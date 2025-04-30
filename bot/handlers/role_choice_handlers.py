# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem vários roles.

• Inline-keyboard com timeout de 60 s
• Após a escolha grava «active_role» no FSM
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Iterable

from aiogram import Router, F, types, exceptions
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from bot.menus import show_menu
from bot.states.menu_states import MenuStates

router = Router(name="role_choice")

_TIMEOUT = 60  # seg.

# ───────────── labels PT ─────────────
_LABELS_PT = {
    "patient":         "Paciente",
    "caregiver":       "Cuidador",
    "physiotherapist": "Fisioterapeuta",
    "accountant":      "Contabilista",
    "administrator":   "Administrador",
}


def role_label(role: str) -> str:
    return _LABELS_PT.get(role, role.capitalize())


# ───────────── API pública ─────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(role_label(r), callback_data=f"role:{r}")
            for r in roles
        ]]
    )

    msg = await bot.send_message(
        chat_id,
        "🔰 Escolha o perfil que pretende utilizar:",
        reply_markup=keyboard,
    )

    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
        role_selector_marker=msg.message_id,
    )

    asyncio.create_task(
        _expire_selector(bot, msg.chat.id, msg.message_id, state)
    )


# ───────────── timeout ─────────────
async def _expire_selector(
    bot: types.Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
) -> None:
    await asyncio.sleep(_TIMEOUT)
    data = await state.get_data()
    if data.get("role_selector_marker") != msg_id:
        return  # utilizador já escolheu

    await state.clear()
    with suppress(exceptions.TelegramBadRequest):
        await bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=None)

    warn = await bot.send_message(
        chat_id,
        "⏳ Tempo expirado. Envie /start para escolher de novo.",
    )
    await asyncio.sleep(_TIMEOUT)
    with suppress(exceptions.TelegramBadRequest):
        await bot.delete_message(chat_id, warn.message_id)


# ───────────── callback de escolha ─────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    F.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    role = cb.data.split(":", 1)[1]  # ex.: administrator

    # 1) limpar qualquer estado intermédio
    await state.clear()

    # 2) guardar o papel activo (agora NÃO é apagado)
    await state.update_data(active_role=role)

    # 3) remover o teclado do selector
    with suppress(exceptions.TelegramBadRequest):
        await cb.message.edit_reply_markup(reply_markup=None)

    await cb.answer(f"Perfil {role_label(role)} seleccionado!")

    # 4) abrir o menu respectivo
    await show_menu(cb.bot, cb.message.chat.id, state, [role])
