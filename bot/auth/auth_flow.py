# bot/auth/auth_flow.py
"""
Fluxo de onboarding/autenticação (Aiogram 3).

• /start               → start_onboarding()
• Contacto partilhado  → handle_contact()
• Confirmação “Sim/Não” com timeout MENU_TIMEOUT
• “✅ Sim”  → confirm_link()   – associa Telegram-ID e abre menu
• “❌ Não”  → cancel_link()    – aborta o processo
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import List, TypedDict

from aiogram import exceptions, types
from aiogram.fsm.context import FSMContext

from bot.config                   import MENU_TIMEOUT
from bot.database                 import queries as q
from bot.database.connection      import get_pool
from bot.handlers.role_choice_handlers import ask_role
from bot.menus                    import show_menu
from bot.menus.ui_helpers         import delete_messages, close_menu_with_alert
from bot.states.auth_states       import AuthStates
from bot.utils.phone              import cleanse

log = logging.getLogger(__name__)

# ──────────────── FSM typing ────────────────
class OnboardingData(TypedDict, total=False):
    db_user_id: str
    first_name: str
    last_name: str
    roles: List[str]
    confirm_marker: int
    contact_marker: int
    active_role: str

# ──────────────── Keyboards ────────────────
def _contact_kbd() -> types.ReplyKeyboardMarkup:
    return types.ReplyKeyboardMarkup(
        keyboard=[[
            types.KeyboardButton(
                text="👉🏼📱  ENVIAR CONTACTO  📱👈🏼",
                request_contact=True,
            )
        ]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _confirm_kbd() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(text="✅ Sim", callback_data="link_yes"),
            types.InlineKeyboardButton(text="❌ Não", callback_data="link_no"),
        ]]
    )

# ───────── helpers: timeouts ──────────
async def _expire_contact_request(bot: types.Bot, chat_id: int, msg_id: int, state: FSMContext) -> None:
    try:
        await asyncio.sleep(MENU_TIMEOUT)

        data: OnboardingData = await state.get_data()
        waiting = await state.get_state() == AuthStates.WAITING_CONTACT.state
        if data.get("contact_marker") != msg_id or not waiting:
            return

        await state.clear()
        await delete_messages(bot, chat_id, msg_id, soft=False)

        warn = await bot.send_message(chat_id,
            "⚠️ Não obtivemos resposta em 60 s. Envie /start (ou Menu > Iniciar) para tentar novamente.")
        await asyncio.sleep(MENU_TIMEOUT)
        with suppress(exceptions.TelegramBadRequest):
            await warn.delete()
    except Exception:
        log.exception("Erro no timeout do pedido de contacto")


async def _expire_confirm(bot: types.Bot, chat_id: int, msg_id: int, state: FSMContext) -> None:
    try:
        await asyncio.sleep(MENU_TIMEOUT)
        if (await state.get_data()).get("confirm_marker") != msg_id:
            return

        await state.clear()
        await delete_messages(bot, chat_id, msg_id, soft=False)

        warn = await bot.send_message(chat_id,
            "⚠️ Tempo expirado. Envie /start para tentar novamente.")
        await asyncio.sleep(MENU_TIMEOUT)
        with suppress(exceptions.TelegramBadRequest):
            await warn.delete()
    except Exception:
        log.exception("Erro no timeout de confirmação")

# ──────────────── Handlers ────────────────
async def start_onboarding(msg: types.Message, state: FSMContext) -> None:
    """
    Passo 1 – pedir o número de telefone.
    Se já existir um prompt pendente, tenta EDITAR a mensagem; caso falhe, apaga
    e envia uma nova. Em ambas as situações reinicia o timeout.
    """
    await state.set_state(AuthStates.WAITING_CONTACT)
    data        = await state.get_data()
    old_marker  = data.get("contact_marker")
    prompt_msg  = None

    if old_marker:
        try:
            prompt_msg = await msg.bot.edit_message_text(
                "*Precisamos confirmar o seu número.*\nClique no botão abaixo 👇",
                chat_id=msg.chat.id,
                message_id=old_marker,
                reply_markup=_contact_kbd(),
                parse_mode="Markdown",
            )
        except exceptions.TelegramBadRequest:
            # falhou a edição → apaga e envia nova
            await delete_messages(msg.bot, msg.chat.id, old_marker, soft=False)

    if prompt_msg is None:  # não havia antiga ou edição falhou
        prompt_msg = await msg.answer(
            "*Precisamos confirmar o seu número.*\nClique no botão abaixo 👇",
            parse_mode="Markdown",
            reply_markup=_contact_kbd(),
        )

    await state.update_data(contact_marker=prompt_msg.message_id)

    asyncio.create_task(
        _expire_contact_request(msg.bot, prompt_msg.chat.id, prompt_msg.message_id, state)
    )


async def handle_contact(msg: types.Message, state: FSMContext) -> None:
    """Processa o Contacto e procura utilizador na BD."""
    phone_digits = cleanse(msg.contact.phone_number)

    pool = await get_pool()
    user = await q.get_user_by_phone(pool, phone_digits)

    await msg.answer("👍 Obrigado!", reply_markup=types.ReplyKeyboardRemove())

    # remove prompt de contacto
    marker = (await state.get_data()).get("contact_marker")
    if marker:
        await delete_messages(msg.bot, msg.chat.id, marker, soft=False)

    if not user:
        await state.clear()
        await msg.answer("Número não encontrado. Assim que o seu perfil for criado avisaremos 🙏")
        return

    await state.update_data(
        db_user_id=str(user["user_id"]),
        first_name=user["first_name"],
        last_name=user["last_name"],
    )
    await state.set_state(AuthStates.CONFIRMING_LINK)

    confirm = await msg.answer(
        f"Encontrámos um perfil para *{user['first_name']} {user['last_name']}*.\nÉ você?",
        parse_mode="Markdown",
        reply_markup=_confirm_kbd(),
    )
    await state.update_data(confirm_marker=confirm.message_id)

    asyncio.create_task(_expire_confirm(msg.bot, confirm.chat.id, confirm.message_id, state))


async def confirm_link(cb: types.CallbackQuery, state: FSMContext) -> None:
    """Botão ✅ Sim – associa Telegram-ID e abre o menu adequado."""
    data: OnboardingData = await state.get_data()
    user_id = data.get("db_user_id")
    if not user_id:
        await cb.answer("Sessão expirada. Envie /start novamente.", show_alert=True)
        await state.clear()
        return

    pool = await get_pool()
    await q.link_telegram_id(pool, user_id, cb.from_user.id)
    roles = await q.get_user_roles(pool, user_id)

    first, last = data.get("first_name", ""), data.get("last_name", "")
    await state.clear()

    await cb.message.edit_text(
        f"✅ O utilizador *{first} {last}* foi associado ao seu Telegram 💬",
        parse_mode="Markdown",
    )
    await cb.answer()

    if len(roles) > 1:
        await ask_role(cb.bot, cb.message.chat.id, state, roles)
    else:
        if roles:
            await state.update_data(active_role=roles[0])
        await show_menu(cb.bot, cb.message.chat.id, state, roles)


async def cancel_link(cb: types.CallbackQuery, state: FSMContext) -> None:
    """Botão ❌ Não – aborta o processo."""
    await state.clear()
    await close_menu_with_alert(cb, "Operação cancelada. Se precisar, envie /start novamente.")
