# bot/auth/auth_flow.py
"""
Fluxo de autenticação / onboarding.

Novidade:
    • a pergunta “É você? (Sim/Não)” expira ao fim de 60 s.
      – se não houver resposta: remove inline-kbd, avisa e apaga aviso
        após mais 60 s, mantendo o chat limpo.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery, Contact,
    ReplyKeyboardMarkup, ReplyKeyboardRemove,
    KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram import exceptions

from bot.states.auth_states import AuthStates
from bot.database.connection import get_pool
from bot.database import queries as q
from bot.utils.phone import cleanse
from bot.menus import show_menu                    # apresenta o menu inicial

log = logging.getLogger(__name__)

CONFIRM_TIMEOUT = 60        # segundos

# ────────────────────── teclados ────────────────────────
def contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Enviar contacto", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Sim", callback_data="link_yes"),
            InlineKeyboardButton(text="❌ Não", callback_data="link_no"),
        ]]
    )

# ─────────────────── helpers de tempo limite ───────────────────
async def _expire_confirm(bot, chat_id: int, msg_id: int,
                          state: FSMContext, data_key: str) -> None:
    """Espera CONFIRM_TIMEOUT; se ainda estamos em CONFIRMING_LINK remove kbd."""
    try:
        await asyncio.sleep(CONFIRM_TIMEOUT)
        data = await state.get_data()
        if data.get(data_key) != msg_id:     # já respondido / outro ciclo
            return
        await state.clear()
        # remove inline-kbd
        with asyncio.TaskGroup() as tg:      # python 3.11; usa try/await se 3.10
            tg.create_task(
                bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=None)
            )
            # envia aviso e apaga-o após 60 s
            async def _warn_then_delete():
                warn = await bot.send_message(
                    chat_id,
                    "⚠️ Tempo expirado. Volte a enviar /start se quiser tentar de novo.",
                )
                await asyncio.sleep(CONFIRM_TIMEOUT)
                with asyncio.SuppressExceptions(exceptions.TelegramBadRequest):
                    await bot.delete_message(chat_id, warn.message_id)
            tg.create_task(_warn_then_delete())
    except Exception as e:                   # log sem falhar a app
        log.exception("Erro a expirar confirmação: %s", e)

# ────────────────────── handlers FSM ──────────────────────
async def start_onboarding(message: Message, state: FSMContext) -> None:
    await state.set_state(AuthStates.WAITING_CONTACT)
    await message.answer(
        "Olá! Toque no botão abaixo e partilhe o seu número:",
        reply_markup=contact_keyboard(),
    )


async def handle_contact(message: Message, state: FSMContext) -> None:
    contact: Contact = message.contact
    phone_digits = cleanse(contact.phone_number)

    pool = await get_pool()
    user = await q.get_user_by_phone(pool, phone_digits)

    await message.answer("👍 Obrigado!", reply_markup=ReplyKeyboardRemove())

    if user:
        await state.update_data(db_user_id=str(user["user_id"]))
        await state.set_state(AuthStates.CONFIRMING_LINK)

        confirm = await message.answer(
            f"Encontrámos um perfil para *{user['first_name']} {user['last_name']}*.\n"
            "É você?",
            parse_mode="Markdown",
            reply_markup=confirm_keyboard(),
        )

        # regista menu activo
        await state.update_data(
            menu_msg_id=confirm.message_id,
            menu_chat_id=confirm.chat.id,
            confirm_marker=confirm.message_id,   # usado para timeout
        )

        # inicia tarefa de expiração
        asyncio.create_task(
            _expire_confirm(message.bot, confirm.chat.id,
                            confirm.message_id, state, "confirm_marker")
        )
    else:
        await state.clear()
        await message.answer(
            "Número não encontrado. Quando o seu perfil estiver criado entraremos em contacto. Obrigado! 🙏"
        )


async def confirm_link(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    user_id: str | None = data.get("db_user_id")
    if not user_id:
        await cb.answer("Sessão expirada. Envie /start novamente.", show_alert=True)
        await state.clear()
        return

    pool = await get_pool()
    await q.link_telegram_id(pool, user_id, cb.from_user.id)
    roles = await q.get_user_roles(pool, user_id)

    await state.clear()
    await cb.message.edit_text("Ligação concluída! 🎉")
    await show_menu(cb.bot, cb.message.chat.id, state, roles)


async def cancel_link(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.edit_text(
        "Operação cancelada. Se precisar, envie novamente /start."
    )
