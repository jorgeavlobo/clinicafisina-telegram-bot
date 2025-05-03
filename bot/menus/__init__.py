# bot/menus/__init__.py
"""
Constrói e gere os menus de cada perfil.

• Se o utilizador tiver vários perfis e ainda não escolheu um,
  delega no selector ask_role().
• Mantém «active_role» mesmo após limpezas de FSM (clear_keep_role).
• A renderização/actualização do menu é feita via ui_helpers.edit_menu()
  (sem repetição de lógica de fallback).
• Cada envio reinicia o timeout de inactividade (MENU_TIMEOUT).
"""

from __future__ import annotations

import logging
from typing import List

from aiogram import Bot
from aiogram.types import ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from bot.states.admin_menu_states import AdminMenuStates
from bot.utils.fsm_helpers        import clear_keep_role
from bot.menus.ui_helpers         import (
    start_menu_timeout,
    edit_menu,
    delete_messages,
)

# builders de cada perfil
from .patient_menu         import build_menu as _patient
from .caregiver_menu       import build_menu as _caregiver
from .physiotherapist_menu import build_menu as _physio
from .accountant_menu      import build_menu as _accountant
from .administrator_menu   import build_menu as _admin

log = logging.getLogger(__name__)

_ROLE_MENU = {
    "patient":         _patient,
    "caregiver":       _caregiver,
    "physiotherapist": _physio,
    "accountant":      _accountant,
    "administrator":   _admin,
}

# ───────────────────────── API pública ─────────────────────────
async def show_menu(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    roles: List[str],
    requested: str | None = None,
) -> None:
    """Create or update the main menu for the active profile."""
    # 0) no valid roles
    if not roles:
        await bot.send_message(
            chat_id,
            "⚠️ Ainda não tem permissões atribuídas.\n"
            "Contacte a receção/administrador.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await clear_keep_role(state)
        return

    # 1) determine active role
    data   = await state.get_data()
    active = requested or data.get("active_role")
    if active is None:
        if len(roles) > 1:
            from bot.handlers.role_choice_handlers import ask_role
            await ask_role(bot, chat_id, state, roles)
            return
        active = roles[0]

    # 2) persist active_role
    await state.update_data(active_role=active)

    # 3) get menu builder
    builder = _ROLE_MENU.get(active)
    if builder is None:
        await bot.send_message(
            chat_id, "❗ Menu não definido para este perfil.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # 4) title & previous message-id
    title = (
        "💻 *Menu administrador:*"
        if active == "administrator"
        else f"👤 *{active.title()}* – menu principal"
    )
    prev_msg_id  = data.get("menu_msg_id")
    prev_chat_id = data.get("menu_chat_id")
    menu_ids: List[int] = data.get("menu_ids", [])

    # 4.a) choose target message for editing (same chat only)
    target_msg_id = prev_msg_id if prev_chat_id == chat_id else None

    # 4.b) render (edit ↦ delete ↦ ZW ↦ new) using ui_helpers.edit_menu()
    msg = await edit_menu(
        bot=bot,
        chat_id=chat_id,
        message_id=target_msg_id,
        text=title,
        keyboard=builder(),
    )

    # 4.c) purge obsolete menus (IDs ≠ actual menu)
    obsolete = [mid for mid in menu_ids if mid != msg.message_id]
    if obsolete:
        await delete_messages(bot, chat_id, obsolete, soft=False)

    # 5) register current menu ID
    await state.update_data(
        menu_msg_id = msg.message_id,
        menu_chat_id = chat_id,
        menu_ids     = [msg.message_id],
    )

    # 6) set base FSM state
    if active == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)

    # 7) (re)start inactivity timeout
    start_menu_timeout(bot, msg, state)
