# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem >1 role.
Grava «active_role» e mantém-no vivo em toda a sessão.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Iterable, List

from aiogram import Router, F, types, exceptions
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus import show_menu
from bot.states.menu_states import MenuStates
from bot.states.admin_menu_states import AdminMenuStates
from bot.utils.fsm_helpers import clear_keep_role          # ← NOVO

__all__: List[str] = ["ask_role", "router"]

router = Router(name="role_choice")

_TIMEOUT = 60  # s

_LABELS_PT = {
    "patient":         "Paciente",
    "caregiver":       "Cuidador",
    "physiotherapist": "Fisioterapeuta",
    "accountant":      "Contabilista",
    "administrator":   "Administrador",
}
def _label(role: str) -> str:
    return _LABELS_PT.get(role, role.capitalize())

# ───────────── API pública ─────────────
async def ask_role(bot: types.Bot, chat_id: int, state: FSMContext,
                   roles: Iterable[str]) -> None:
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(_label(r), callback_data=f"role:{r}")
        ] for r in roles]
    )
    msg = await bot.send_message(chat_id,
                                 "🔰 Selecione o perfil que pretende utilizar:",
                                 reply_markup=kbd)

    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        roles=[r.lower() for r in roles],
        role_selector_marker=msg.message_id,
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
    )
    asyncio.create_task(_expire_selector(bot, msg.chat.id, msg.message_id, state))

# ───────────── timeout ─────────────
async def _expire_selector(bot: types.Bot, chat: int, msg: int,
                           state: FSMContext) -> None:
    await asyncio.sleep(_TIMEOUT)
    if await state.get_state() != MenuStates.WAIT_ROLE_CHOICE.state:
        return
    data = await state.get_data()
    if data.get("role_selector_marker") != msg:
        return

    await state.clear()
    with suppress(exceptions.TelegramBadRequest):
        await bot.edit_message_reply_markup(chat, msg, reply_markup=None)

    warn = await bot.send_message(chat,
                                  "⏳ Tempo expirado. Envie /start para escolher de novo.")
    await asyncio.sleep(_TIMEOUT)
    with suppress(exceptions.TelegramBadRequest):
        await warn.delete()

# ───────────── callback ─────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    lambda c: c.data and c.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    role = cb.data.split(":", 1)[1].lower()
    data = await state.get_data()
    if role not in data.get("roles", []):
        await cb.answer("Perfil inválido.", show_alert=True)
        return

    with suppress(exceptions.TelegramBadRequest):
        await cb.message.delete()

    await state.clear()
    await state.update_data(active_role=role)

    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)

    await cb.answer(f"Perfil {_label(role)} selecionado!")
    await show_menu(cb.bot, cb.message.chat.id, state, [role])
