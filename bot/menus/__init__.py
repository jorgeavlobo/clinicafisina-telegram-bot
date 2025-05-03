# bot/menus/__init__.py
"""
Builds and manages the menus for each user role.

• If the user has several roles and hasn’t chosen one yet, delegates to
  ask_role() in bot/handlers/role_choice_handlers.py.
• Keeps «active_role» even after clean-ups (clear_keep_role).
• When a brand-new menu is required, purges *all* previous menu messages
  still stored in menu_ids.
• Each visible menu restarts the inactivity timer (MENU_TIMEOUT in
  bot/config.py).

NEW (2025-05-03)
────────────────
• Added async build(role) which **only constructs** (keyboard, text) – it
  never sends or edits messages.  Handlers that want a perfectly smooth
  transition should call this helper and then use
  replace_or_create_menu() to edit the current bubble.
  Existing show_menu() keeps its old API for /start and similar commands.
"""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import List, Tuple

from aiogram import Bot, exceptions
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from bot.states.admin_menu_states import AdminMenuStates
from bot.utils.fsm_helpers        import clear_keep_role
from bot.menus.common             import start_menu_timeout

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

# ────────────────────────── PUBLIC: purely build UI ──────────────────────────
async def build(role: str) -> Tuple[InlineKeyboardMarkup, str]:
    """
    Return **(keyboard, text)** for the first menu of *role*.

    • Nothing is sent/edited here – handlers decide what to do with the UI.
    • Raises ValueError if role is unknown.
    """
    builder = _ROLE_MENU.get(role)
    if builder is None:
        raise ValueError(f"No menu defined for role '{role}'")

    title = (
        "💻 *Menu administrador:*"
        if role == "administrator"
        else f"👤 *{role.title()}* – menu principal"
    )
    return builder(), title

# ─────────────────────── internal helper – purge old menus ───────────────────
async def _purge_all_menus(bot: Bot, state: FSMContext) -> None:
    """Delete every message whose ID is listed in FSM «menu_ids»."""
    data      = await state.get_data()
    chat_id   = data.get("menu_chat_id")
    menu_ids: List[int] = data.get("menu_ids", [])

    if not chat_id or not menu_ids:
        return

    for mid in menu_ids:
        with suppress(exceptions.TelegramBadRequest):
            await bot.delete_message(chat_id, mid)

# ────────────────────────── PUBLIC: legacy API (sends) ───────────────────────
async def show_menu(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    roles: List[str],
    requested: str | None = None,
) -> None:
    """
    “Classic” helper that **sends** a new menu after wiping the old ones.
    Used by /start or flows where a clean chat history is preferred.

    New code that requires *seamless* transitions should favour
    build(role) + replace_or_create_menu() instead.
    """
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
            from bot.handlers.role_choice_handlers import ask_role   # avoid cycle
            await _purge_all_menus(bot, state)
            await ask_role(bot, chat_id, state, roles)
            return
        active = roles[0]

    # 2) persist choice
    await state.update_data(active_role=active)

    # 3) build UI for that role
    try:
        kbd, title = await build(active)
    except ValueError:
        await bot.send_message(
            chat_id, "❗ Menu não definido para este perfil.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # 4) wipe every previous menu, then send a fresh one
    await _purge_all_menus(bot, state)

    msg = await bot.send_message(
        chat_id,
        title,
        reply_markup=kbd,
        parse_mode="Markdown",
    )

    # 5) track ONLY the newly created menu
    await state.update_data(
        menu_msg_id = msg.message_id,
        menu_chat_id = chat_id,
        menu_ids     = [msg.message_id],
    )

    # 6) base FSM state
    if active == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)

    # 7) kick timer
    start_menu_timeout(bot, msg, state)
