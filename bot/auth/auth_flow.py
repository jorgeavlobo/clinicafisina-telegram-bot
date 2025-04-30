# bot/auth/auth_flow.py
"""
Fluxo de autenticação / onboarding (Aiogram 3).

• Pede ao utilizador que partilhe o contacto.
• Se existir perfil: mostra confirmação “É você? (Sim/Não)” com timeout 60 s.
• Se o contacto tiver vários perfis, apresenta menu de escolha de perfil
  (role) com timeout, via ask_role().
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import List

from aiogram import types, exceptions
from aiogram.fsm.context import FSMContext

from bot.states.auth_states import AuthStates
from bot.database.connection import get_pool
from bot.database import queries as q
from bot.utils.phone import cleanse
from bot.menus import show_menu
from bot.handlers.role_choice_handlers import ask_role   # ← NOVO

log = logging.getLogger(__name__)

CONFIRM_TIMEOUT = 60  # seg

# ───────────────────────── teclados ─────────────────────────
def contact_keyboard() -> types.ReplyKeyboardMarkup:
    return types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="📱 Enviar contacto", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def confirm_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(text="✅ Sim", callback_data="link_yes"),
            types.InlineKeyboardButton(text="❌ Não", callback_data="link_no"),
        ]]
    )

# ─────────────────────── timeout helper ───────────────────────
async def _expire_confirm(
    bot: types.Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
    marker_key: str = "confirm_marker",
) -> None:
    """Remove inline-kbd após 60 s e envia aviso que desaparece 60 s depois."""
    try:
        await asyncio.sleep(CONFIRM_TIMEOUT)
        data = await state.get_data()
        if data.get(marker_key) != msg_id:
            return                              # já houve resposta

        await state.clear()

        with suppress(exceptions.TelegramBadRequest):
            await bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=None)

        warn = await bot.send_message(
            chat_id,
            "⚠️ Tempo expirado. Envie /start para tentar novamente.",
        )
        await asyncio.sleep(CONFIRM_TIMEOUT)
        with suppress(exceptions.TelegramBadRequest):
            await bot.delete_message(chat_id, warn.message_id)
    except Exception:
        log.exception("Erro ao expirar confirmação")


# ───────────────────────── handlers ─────────────────────────
async def start_onboarding(msg: types.Message, state: FSMContext) -> None:
    await state.set_state(AuthStates.WAITING_CONTACT)
    await msg.answer(
        "Olá! Toque no botão abaixo e partilhe o seu número:",
        reply_markup=contact_keyboard(),
    )


async def handle_contact(msg: types.Message, state: FSMContext) -> None:
    contact: types.Contact = msg.contact
    phone_digits = cleanse(contact.phone_number)

    pool = await get_pool()
    user = await q.get_user_by_phone(pool, phone_digits)

    await msg.answer("👍 Obrigado!", reply_markup=types.ReplyKeyboardRemove())

    if not user:
        await state.clear()
        await msg.answer(
            "Número não encontrado. Assim que o seu perfil for criado avisaremos. 🙏"
        )
        return

    await state.update_data(db_user_id=str(user["user_id"]))
    await state.set_state(AuthStates.CONFIRMING_LINK)

    confirm = await msg.answer(
        f"Encontrámos um perfil para *{user['first_name']} {user['last_name']}*.\n"
        "É você?",
        parse_mode="Markdown",
        reply_markup=confirm_keyboard(),
    )
    await state.update_data(
        menu_msg_id=confirm.message_id,
        menu_chat_id=confirm.chat.id,
        confirm_marker=confirm.message_id,
    )

    asyncio.create_task(
        _expire_confirm(msg.bot, confirm.chat.id, confirm.message_id, state)
    )


async def confirm_link(cb: types.CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    user_id: str | None = data.get("db_user_id")
    if not user_id:
        await cb.answer("Sessão expirada. Envie /start novamente.", show_alert=True)
        await state.clear()
        return

    pool = await get_pool()
    await q.link_telegram_id(pool, user_id, cb.from_user.id)
    roles: List[str] = await q.get_user_roles(pool, user_id)

    # fecha mensagem “É você?” e limpa FSM
    await state.clear()
    await cb.message.edit_text("Ligação concluída! 🎉")
    await cb.answer()

    # vários perfis → menu de escolha com timeout
    if len(roles) > 1:
        await ask_role(cb.bot, cb.message.chat.id, state, roles)
        return

    # um único perfil → mostra menu directamente
    await show_menu(cb.bot, cb.message.chat.id, state, roles)


async def cancel_link(cb: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.edit_text(
        "Operação cancelada. Se precisar, envie /start novamente."
    )
    await cb.answer()
