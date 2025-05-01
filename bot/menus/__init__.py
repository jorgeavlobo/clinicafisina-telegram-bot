# bot/menus/__init__.py
"""
Envia (ou renova) o menu principal apropriado ao perfil activo.
[… comentário igual …]
"""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import List

from aiogram import Bot, exceptions
from aiogram.types import ReplyKeyboardRemove
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

# ───────────────────────── helpers ─────────────────────────
async def _purge_old_menu(bot: Bot, state: FSMContext) -> None:
    data    = await state.get_data()
    msg_id  = data.get("menu_msg_id")
    chat_id = data.get("menu_chat_id")
    if msg_id and chat_id:
        with suppress(exceptions.TelegramBadRequest):
            await bot.delete_message(chat_id, msg_id)

# ───────────────────────── API pública ─────────────────────────
async def show_menu(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    roles: List[str],
    requested: str | None = None,
) -> None:
    # 0) sem papéis válidos
    if not roles:
        await bot.send_message(
            chat_id,
            "⚠️ Ainda não tem permissões atribuídas.\n"
            "Contacte a receção/administrador.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await clear_keep_role(state)
        return

    # 1) determina o papel activo
    data   = await state.get_data()
    active = requested or data.get("active_role")
    if active is None:
        if len(roles) > 1:
            from bot.handlers.role_choice_handlers import ask_role   # evitar ciclo
            await _purge_old_menu(bot, state)
            await ask_role(bot, chat_id, state, roles)
            return
        active = roles[0]

    # 2) guarda escolha
    await state.update_data(active_role=active)

    # 3) builder do menu
    builder = _ROLE_MENU.get(active)
    if builder is None:
        await bot.send_message(
            chat_id, "❗ Menu não definido para este perfil.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # 4) remove menu antigo e envia o novo
    await _purge_old_menu(bot, state)

    title = (
        "💻 *Menu administrador:*"
        if active == "administrator"
        else f"👤 *{active.title()}* – menu principal"
    )
    msg = await bot.send_message(
        chat_id,
        title,
        reply_markup=builder(),
        parse_mode="Markdown",
    )
    await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=chat_id)

    # 5) estado FSM base
    if active == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)   # manter FSM “limpa”

    # 6) (re)inicia timeout automático
    start_menu_timeout(bot, msg, state)
