"""
Selector de perfil quando o utilizador tem mais do que um role.

• Teclado inline com timeout de 60 s
• Depois da escolha guarda «active_role» no FSM e mostra o menu
"""
from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Iterable, List

from aiogram import Router, types, exceptions
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus.common          import start_menu_timeout   # só p/ timeout extra
from bot.states.menu_states    import MenuStates
from bot.states.admin_menu_states import AdminMenuStates
from bot.utils.fsm_helpers     import clear_keep_role

__all__: List[str] = ["ask_role", "router"]

router = Router(name="role_choice")

_TIMEOUT = 60  # s

_LABELS = {
    "patient":         "Paciente",
    "caregiver":       "Cuidador",
    "physiotherapist": "Fisioterapeuta",
    "accountant":      "Contabilista",
    "administrator":   "Administrador",
}


def _label(role: str) -> str:
    return _LABELS.get(role, role.capitalize())


# ───────────────────── API pública ─────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(_label(r), callback_data=f"role:{r}")
            for r in roles
        ]]
    )

    msg = await bot.send_message(
        chat_id,
        "🔰 Selecione o perfil que pretende utilizar:",
        reply_markup=kb,
    )

    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        roles=list(roles),
        role_selector_marker=msg.message_id,
        menu_msg_id=msg.message_id,
        menu_chat_id=chat_id,
    )

    # timeout para esconder selector
    asyncio.create_task(_expire_selector(bot, chat_id, msg.message_id, state))


# ───────────────────── timeout ─────────────────────
async def _expire_selector(bot: types.Bot, chat_id: int, msg_id: int, state: FSMContext):
    await asyncio.sleep(_TIMEOUT)
    data = await state.get_data()
    if data.get("role_selector_marker") != msg_id:
        return                                    # já respondeu

    await clear_keep_role(state)                  # limpa FSM mas preserva active_role
    with suppress(exceptions.TelegramBadRequest):
        await bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=None)

    warn = await bot.send_message(
        chat_id,
        "⏳ Tempo expirado. Envie /start para tentar de novo.",
    )
    await asyncio.sleep(_TIMEOUT)
    with suppress(exceptions.TelegramBadRequest):
        await warn.delete()


# ───────────────────── callback ─────────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    lambda c: c.data and c.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext):
    role = cb.data.split(":", 1)[1]

    # remove selector
    with suppress(exceptions.TelegramBadRequest):
        await cb.message.delete()

    # limpa markers mas mantém role activo
    await clear_keep_role(state)
    await state.update_data(active_role=role)

    # estado base para menus que precisam (admin)
    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)

    await cb.answer(f"Perfil {_label(role)} seleccionado!")

    # import atrasado para evitar ciclo
    from bot.menus import show_menu
    await show_menu(cb.bot, cb.message.chat.id, state, [role])

    # reinicia timeout do menu
    start_menu_timeout(cb.bot, cb.message, state)
