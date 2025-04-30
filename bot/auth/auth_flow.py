# bot/auth/auth_flow.py
"""
Fluxo de onboarding/autenticação (aiogram-3).

• /start chama start_onboarding() quando o utilizador ainda não está
  ligado ao perfil da base de dados.
• O utilizador partilha o contacto → handle_contact()
    – Se não existir, informa-o e termina.
    – Se existir, pergunta “É você? (Sim/Não)” e coloca timeout de 60 s.
• “✅ Sim” → confirm_link():
    – Associa telegram_user_id.
    – Se houver vários perfis chama ask_role() para escolher.
    – Caso contrário grava «active_role» e mostra imediatamente o menu.
• “❌ Não” → cancel_link()
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import List

from aiogram import types, exceptions
from aiogram.fsm.context import FSMContext

from bot.states.auth_states    import AuthStates
from bot.database.connection   import get_pool
from bot.database              import queries as q
from bot.utils.phone           import cleanse
from bot.menus                 import show_menu
from bot.handlers.role_choice_handlers import ask_role   # selector de perfis

log = logging.getLogger(__name__)

_CONFIRM_TTL = 60   # segundos

# ─────────────────────────── Keyboards ────────────────────────────
def _contact_kbd() -> types.ReplyKeyboardMarkup:
    return types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="📱 Enviar contacto",
                                        request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _confirm_kbd() -> types.InlineKeyboardMarkup:            # ← nome livre, como quiser
    return types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(text="✅ Sim", callback_data="link_yes"),
            types.InlineKeyboardButton(text="❌ Não", callback_data="link_no"),
        ]]
    )

# ───────────────────── helper: timeout confirm ────────────────────
async def _expire_confirm(
    bot: types.Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
) -> None:
    """Remove o teclado ‘Sim/Não’ após _CONFIRM_TTL s e avisa o utilizador."""
    try:
        await asyncio.sleep(_CONFIRM_TTL)

        data = await state.get_data()
        if data.get("confirm_marker") != msg_id:        # já validou / cancelou
            return

        await state.clear()
        with suppress(exceptions.TelegramBadRequest):
            await bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=None)

        warn = await bot.send_message(
            chat_id,
            "⚠️ Tempo expirado. Envie /start para tentar novamente.",
        )
        await asyncio.sleep(_CONFIRM_TTL)
        with suppress(exceptions.TelegramBadRequest):
            await warn.delete()
    except Exception:
        log.exception("Erro no timeout de confirmação")


# ─────────────────────────── Handlers ─────────────────────────────
async def start_onboarding(msg: types.Message, state: FSMContext) -> None:
    """Primeiro passo – pedir o número de telefone."""
    await state.set_state(AuthStates.WAITING_CONTACT)
    await msg.answer(
        "Olá! Toque no botão abaixo para partilhar o seu número:",
        reply_markup=_contact_kbd(),
    )


async def handle_contact(msg: types.Message, state: FSMContext) -> None:
    """Recebe Contact e procura utilizador pelo número limpo."""
    phone_digits = cleanse(msg.contact.phone_number)

    pool = await get_pool()
    user = await q.get_user_by_phone(pool, phone_digits)

    await msg.answer("👍 Obrigado!", reply_markup=types.ReplyKeyboardRemove())

    if not user:
        await state.clear()
        await msg.answer(
            "Número não encontrado. Assim que o seu perfil for criado avisaremos 🙏"
        )
        return

    # guarda user_id na FSM para o passo seguinte
    await state.update_data(db_user_id=str(user["user_id"]))
    await state.set_state(AuthStates.CONFIRMING_LINK)

    confirm = await msg.answer(
        f"Encontrámos um perfil para *{user['first_name']} {user['last_name']}*.\n"
        "É você?",
        parse_mode="Markdown",
        reply_markup=_confirm_kbd(),
    )
    await state.update_data(
        confirm_marker=confirm.message_id,
        menu_msg_id=confirm.message_id,
        menu_chat_id=confirm.chat.id,
    )

    asyncio.create_task(
        _expire_confirm(msg.bot, confirm.chat.id, confirm.message_id, state)
    )


async def confirm_link(cb: types.CallbackQuery, state: FSMContext) -> None:
    """Handler do botão ✅ Sim – associa Telegram-ID e abre o menu."""
    data = await state.get_data()
    user_id: str | None = data.get("db_user_id")
    if not user_id:
        await cb.answer("Sessão expirada. Envie /start de novo.", show_alert=True)
        await state.clear()
        return

    pool = await get_pool()
    await q.link_telegram_id(pool, user_id, cb.from_user.id)
    roles: List[str] = await q.get_user_roles(pool, user_id)

    # fecha a msg “É você?” e limpa estado transitório
    await state.clear()
    await cb.message.edit_text("Ligação concluída! 🎉")
    await cb.answer()

    # vários perfis → selector de perfil
    if len(roles) > 1:
        await ask_role(cb.bot, cb.message.chat.id, state, roles)
        return

    # um único perfil → entra directo
    if roles:
        await state.update_data(active_role=roles[0])
    await show_menu(cb.bot, cb.message.chat.id, state, roles)


async def cancel_link(cb: types.CallbackQuery, state: FSMContext) -> None:
    """Handler do botão ❌ Não – aborta o processo."""
    await state.clear()
    await cb.message.edit_text(
        "Operação cancelada. Se precisar, envie /start novamente."
    )
    await cb.answer()
