# bot/auth/auth_flow.py
"""
Fluxo de autenticação / onboarding (Aiogram 3).

Estados:
    • WAITING_CONTACT   – bot aguarda que o utilizador partilhe o nº
    • CONFIRMING_LINK   – perfil encontrado; pede confirmação “Sim/Não”
"""
from __future__ import annotations

import logging
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery, Contact,
    ReplyKeyboardMarkup, ReplyKeyboardRemove,
    KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton,
)

from bot.states.auth_states import AuthStates
from bot.database.connection import get_pool
from bot.database import queries as q
from bot.utils.phone import cleanse
from bot.menus import show_menu                    # ⬅️  para enviar o menu

log = logging.getLogger(__name__)

# ───────────────────────── helpers de teclados ──────────────────────────
def contact_keyboard() -> ReplyKeyboardMarkup:
    """Teclado de 1 botão que pede ao utilizador para partilhar o contacto."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Enviar contacto", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    """Inline-keyboard “Sim / Não” para confirmar a ligação ao perfil."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Sim", callback_data="link_yes"),
            InlineKeyboardButton(text="❌ Não", callback_data="link_no"),
        ]]
    )

# ───────────────────────────── handlers FSM ─────────────────────────────
async def start_onboarding(message: Message, state: FSMContext) -> None:
    """Primeiro passo do onboarding quando o utilizador ainda não está ligado."""
    await state.set_state(AuthStates.WAITING_CONTACT)
    await message.answer(
        "Olá! Para continuar, toque no botão abaixo e partilhe o seu número:",
        reply_markup=contact_keyboard(),
    )


async def handle_contact(message: Message, state: FSMContext) -> None:
    """Recebe o contacto, procura o perfil e (se existir) pede confirmação."""
    contact: Contact = message.contact
    phone_digits = cleanse(contact.phone_number)        # normaliza p/ só dígitos

    pool = await get_pool()
    user = await q.get_user_by_phone(pool, phone_digits)

    # remove o teclado de partilha
    await message.answer("👍 Obrigado pelo contacto!", reply_markup=ReplyKeyboardRemove())

    if user:
        # guarda user_id no FSM para a callback
        await state.update_data(db_user_id=str(user["user_id"]))
        await state.set_state(AuthStates.CONFIRMING_LINK)

        await message.answer(
            f"Encontrámos um perfil para *{user['first_name']} {user['last_name']}*.\n"
            "É você?",
            parse_mode="Markdown",
            reply_markup=confirm_keyboard(),
        )
    else:
        await state.clear()
        await message.answer(
            "Não encontramos esse número na nossa base.\n"
            "Assim que o seu registo estiver criado entraremos em contacto. Obrigado! 🙏",
        )
        log.info("Phone %s não encontrado – utilizador não registado", phone_digits)


async def confirm_link(cb: CallbackQuery, state: FSMContext) -> None:
    """Confirmação positiva (“Sim”) – liga telegram_user_id e mostra o menu."""
    data = await state.get_data()
    user_id: str | None = data.get("db_user_id")
    if not user_id:
        await cb.answer("Sessão expirada. Envie /start novamente.", show_alert=True)
        await state.clear()
        return

    pool = await get_pool()
    await q.link_telegram_id(pool, user_id, cb.from_user.id)
    roles = await q.get_user_roles(pool, user_id)

    # limpa qualquer estado pendente e apresenta o menu principal
    await state.clear()
    await cb.message.edit_text("Ligação concluída! 🎉")
    log.info(
        "Telegram %s ligado a user %s com roles %s",
        cb.from_user.id, user_id, roles,
    )

    await show_menu(cb.bot, cb.message.chat.id, state, roles)   # 👈 menu


async def cancel_link(cb: CallbackQuery, state: FSMContext) -> None:
    """Utilizador respondeu “Não” – aborta o processo de ligação."""
    await state.clear()
    await cb.message.edit_text(
        "Operação cancelada. Se precisar, envie novamente /start."
    )
    log.info("Utilizador %s cancelou ligação.", cb.from_user.id)
