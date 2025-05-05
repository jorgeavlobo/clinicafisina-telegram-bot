# bot/auth/auth_flow.py
"""
Fluxo de onboarding/autenticação (Aiogram 3).

• /start               → start_onboarding()
• Contacto partilhado  → handle_contact()
• Texto enquanto aguardamos contacto → reject_plain_text()
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
    warn_marker: int            # ← id da mensagem-aviso
    warned_plain_text: bool
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

# ─────────────────── helpers ────────────────────
async def _purge_warning(bot: types.Bot, chat_id: int, data: OnboardingData) -> None:
    """Apaga mensagem-aviso, se existir e ainda não foi removida."""
    warn = data.get("warn_marker")
    if warn:
        await delete_messages(bot, chat_id, warn, soft=False)

async def _ensure_contact_prompt(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
) -> None:
    """
    Garante que existe exactamente **um** prompt «ENVIAR CONTACTO».

    Remove prompt e aviso antigos (se existirem), envia novo prompt,
    actualiza marcador e reinicia timeout.
    """
    data = await state.get_data()

    # limpa aviso antigo
    await _purge_warning(bot, chat_id, data)

    # limpa prompt antigo
    old_prompt = data.get("contact_marker")
    if old_prompt:
        await delete_messages(bot, chat_id, old_prompt, soft=False)

    # novo prompt
    prompt = await bot.send_message(
        chat_id,
        "*Precisamos confirmar o seu número.*\n"
        "Clique no botão abaixo 👇",
        parse_mode="Markdown",
        reply_markup=_contact_kbd(),
    )
    await state.update_data(contact_marker=prompt.message_id)

    # (re)inicia cronómetro
    asyncio.create_task(
        _expire_contact_request(bot, chat_id, prompt.message_id, state)
    )

# ───────── helpers: timeouts ──────────
async def _expire_contact_request(
    bot: types.Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
) -> None:
    """Encerra o prompt se o contacto não for partilhado a tempo."""
    try:
        await asyncio.sleep(MENU_TIMEOUT)
        data: OnboardingData = await state.get_data()
        waiting = await state.get_state() == AuthStates.WAITING_CONTACT.state
        if data.get("contact_marker") != msg_id or not waiting:
            return

        # limpa tudo
        await _purge_warning(bot, chat_id, data)
        await delete_messages(bot, chat_id, msg_id, soft=False)
        await state.clear()

        warn = await bot.send_message(
            chat_id,
            "⚠️ Não obtivemos resposta em 60 s. "
            "Envie /start (ou Menu > Iniciar) para tentar novamente.",
        )
        await asyncio.sleep(MENU_TIMEOUT)
        with suppress(exceptions.TelegramBadRequest):
            await warn.delete()
    except Exception:
        log.exception("Erro no timeout do pedido de contacto")


async def _expire_confirm(
    bot: types.Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
) -> None:
    """Timeout da confirmação “Sim/Não”."""
    try:
        await asyncio.sleep(MENU_TIMEOUT)
        if (await state.get_data()).get("confirm_marker") != msg_id:
            return

        await state.clear()
        await delete_messages(bot, chat_id, msg_id, soft=False)

        warn = await bot.send_message(
            chat_id,
            "⚠️ Tempo expirado. Envie /start para tentar novamente.",
        )
        await asyncio.sleep(MENU_TIMEOUT)
        with suppress(exceptions.TelegramBadRequest):
            await warn.delete()
    except Exception:
        log.exception("Erro no timeout de confirmação")

# ──────────────── Handlers ────────────────
async def start_onboarding(msg: types.Message, state: FSMContext) -> None:
    """Passo 1 – pede o contacto (sempre via _ensure_contact_prompt)."""
    await state.set_state(AuthStates.WAITING_CONTACT)
    await _ensure_contact_prompt(msg.bot, msg.chat.id, state)


async def reject_plain_text(msg: types.Message, state: FSMContext) -> None:
    """
    O utilizador escreveu texto enquanto aguardamos o contacto.
    Apaga a mensagem, mostra aviso **uma vez** e volta a exibir o botão.
    """
    with suppress(exceptions.TelegramBadRequest):
        await msg.delete()

    data: OnboardingData = await state.get_data()
    if not data.get("warned_plain_text"):
        warn = await msg.answer(
            "❗ Por favor, NÃO escreva o número manualmente.\n"
            "Toque no botão *ENVIAR CONTACTO* para continuar.",
            parse_mode="Markdown",
        )
        await state.update_data(
            warned_plain_text=True,
            warn_marker=warn.message_id,
        )

    await _ensure_contact_prompt(msg.bot, msg.chat.id, state)


async def handle_contact(msg: types.Message, state: FSMContext) -> None:
    """Processa o Contacto e procura utilizador na BD."""
    phone_digits = cleanse(msg.contact.phone_number)

    # fecha o teclado
    await msg.answer("👍 Obrigado!", reply_markup=types.ReplyKeyboardRemove())

    data: OnboardingData = await state.get_data()
    # limpa prompt e aviso
    await _purge_warning(msg.bot, msg.chat.id, data)
    prompt = data.get("contact_marker")
    if prompt:
        await delete_messages(msg.bot, msg.chat.id, prompt, soft=False)

    pool = await get_pool()
    user = await q.get_user_by_phone(pool, phone_digits)

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
        f"Encontrámos um perfil para *{user['first_name']} {user['last_name']}*.\n"
        "É você?",
        parse_mode="Markdown",
        reply_markup=_confirm_kbd(),
    )
    await state.update_data(confirm_marker=confirm.message_id)

    asyncio.create_task(
        _expire_confirm(msg.bot, confirm.chat.id, confirm.message_id, state)
    )


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
