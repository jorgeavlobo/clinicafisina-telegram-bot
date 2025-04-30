# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem ≥2 roles.
• Inline-keyboard com timeout de 60 s.
• Regista menu ativo para o ActiveMenuMiddleware.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Iterable, List

from aiogram import Router, F, types, exceptions
from aiogram.fsm.context import FSMContext

from bot.utils.i18n import role_label          # helper opcional para traduzir ‘patient’→‘Paciente’
from bot.menus import show_menu
from bot.states.menu_states import MenuStates

router = Router(name="role_choice")

_TIMEOUT = 60  # s


# ───────────────────────── interface pública ──────────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:
    """
    Mostra inline-keyboard com os roles do utilizador.
    """
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(
                text=role_label(r), callback_data=f"role:{r}"
            ) for r in roles
        ]]
    )

    msg = await bot.send_message(
        chat_id,
        "Escolha o perfil que pretende utilizar:",
        reply_markup=kb,
    )

    # guardar como menu ativo
    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
        role_selector_marker=msg.message_id,
    )

    # timeout
    asyncio.create_task(_expire_selector(bot, msg.chat.id, msg.message_id, state))


# ───────────────────────── timeout helper ──────────────────────────
async def _expire_selector(
    bot: types.Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
) -> None:
    await asyncio.sleep(_TIMEOUT)
    data = await state.get_data()
    if data.get("role_selector_marker") != msg_id:
        return  # já foi tratado

    await state.clear()
    with suppress(exceptions.TelegramBadRequest):
        await bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=None)

    warn = await bot.send_message(
        chat_id,
        "⏳ Tempo expirado. Envie /start para escolher novamente.",
    )
    await asyncio.sleep(_TIMEOUT)
    with suppress(exceptions.TelegramBadRequest):
        await bot.delete_message(chat_id, warn.message_id)


# ───────────────────────── callback handler ──────────────────────────
@router.callback_query(
    F.data.startswith("role:"),
    state=MenuStates.WAIT_ROLE_CHOICE,
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext):
    role = cb.data.split(":", 1)[1]

    # regista perfil ativo e limpa selector
    await state.update_data(active_role=role)
    await state.clear()

    with suppress(exceptions.TelegramBadRequest):
        await cb.message.edit_reply_markup(reply_markup=None)

    await cb.answer(f"Perfil {role_label(role)} selecionado!")

    # mostra o menu desse perfil
    await show_menu(cb.bot, cb.message.chat.id, state, [role])
