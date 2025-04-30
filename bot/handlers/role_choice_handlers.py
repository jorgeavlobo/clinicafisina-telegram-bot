# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem ≥ 2 roles.

• Mostra um inline-keyboard com timeout de 60 s
• Depois da escolha guarda «active_role» no FSM
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Iterable, List

from aiogram import Router, types, exceptions
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus import show_menu
from bot.states.menu_states import MenuStates
from bot.states.admin_menu_states import AdminMenuStates

router = Router(name="role_choice")

_TIMEOUT = 60  # segundos

_LABELS_PT = {
    "patient":         "Paciente",
    "caregiver":       "Cuidador",
    "physiotherapist": "Fisioterapeuta",
    "accountant":      "Contabilista",
    "administrator":   "Administrador",
}


def _label(role: str) -> str:
    """Devolve rótulo PT ou capitaliza por defeito."""
    return _LABELS_PT.get(role.lower(), role.capitalize())


# ─────────────────── API pública ────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:
    """
    Envia o selector de perfis e coloca o estado
    MenuStates.WAIT_ROLE_CHOICE.
    """
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=_label(r),
                    callback_data=f"role:{r.lower()}",
                )
            ]
            for r in roles
        ]
    )

    msg = await bot.send_message(
        chat_id,
        "🔰 Escolha o perfil que pretende utilizar:",
        reply_markup=kbd,
    )

    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        roles=[r.lower() for r in roles],
        role_selector_marker=msg.message_id,
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
    )

    # timeout p/ remover teclado se não escolher
    asyncio.create_task(
        _expire_selector(bot, msg.chat.id, msg.message_id, state)
    )


# ─────────────────── timeout ────────────────────
async def _expire_selector(
    bot: types.Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
) -> None:
    await asyncio.sleep(_TIMEOUT)

    if await state.get_state() != MenuStates.WAIT_ROLE_CHOICE.state:
        return
    if (await state.get_data()).get("role_selector_marker") != msg_id:
        return

    await state.clear()          # descarta selector
    with suppress(exceptions.TelegramBadRequest):
        await bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=None)

    warn = await bot.send_message(
        chat_id,
        "⏳ Tempo expirado. Envie /start para escolher de novo.",
    )
    await asyncio.sleep(_TIMEOUT)
    with suppress(exceptions.TelegramBadRequest):
        await warn.delete()


# ─────────────────── callback “role:…” ────────────────────
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

    # remove a mensagem do selector
    with suppress(exceptions.TelegramBadRequest):
        await cb.message.delete()

    # limpa estado temporário mas mantém roles
    await state.clear()
    await state.update_data(active_role=role, roles=data["roles"])

    # estado base (só é necessário para administrador)
    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)          # ← ALTERADO

    await cb.answer(f"Perfil {_label(role)} selecionado!")
    await show_menu(cb.bot, cb.message.chat.id, state, [role])
