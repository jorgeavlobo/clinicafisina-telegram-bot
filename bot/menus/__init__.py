# bot/menus/__init__.py
"""
Constrói e gere os menus de cada perfil.

• Se o utilizador tiver vários perfis e ainda não escolheu um,
  delega no selector ask_role().
• Mantém «active_role» mesmo após limpezas de FSM (clear_keep_role).
• Ao abrir um menu novo substitui o menu anterior com `edit_message_text` (sem salto visual);
  em caso de falha, apaga e volta a enviar (fallback).
• Cada envio reinicia o timeout de inactividade (MENU_TIMEOUT em
  bot/config.py).
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
from bot.menus.ui_helpers         import start_menu_timeout

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
async def _purge_all_menus(bot: Bot, state: FSMContext) -> None:
    """
    Apaga **todos** os menus cujo ID esteja registado em `menu_ids`
    (lista guardada no FSM). Essa lista é actualizada no final de
    show_menu() para conter só o menu acabado de abrir.
    """
    data      = await state.get_data()
    chat_id   = data.get("menu_chat_id")        # mesmo chat p/ todos
    menu_ids: List[int] = data.get("menu_ids", [])

    if not chat_id or not menu_ids:
        return

    for mid in menu_ids:
        with suppress(exceptions.TelegramBadRequest):
            await bot.delete_message(chat_id, mid)

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

    # 4) substitui o menu anterior ou envia um novo
    title = (
        "💻 *Menu administrador:*"
        if active == "administrator"
        else f"👤 *{active.title()}* – menu principal"
    )
    prev_msg_id = data.get("menu_msg_id")
    prev_chat_id = data.get("menu_chat_id")
    msg = None
    if prev_msg_id and prev_chat_id:
        # Tenta editar a mensagem anterior
        try:
            msg = await bot.edit_message_text(
                title,
                chat_id=prev_chat_id,
                message_id=prev_msg_id,
                reply_markup=builder(),
                parse_mode="Markdown",
            )
            # Remove outros menus antigos (se existirem)
            menu_ids: List[int] = data.get("menu_ids", [])
            for mid in menu_ids:
                if mid != prev_msg_id:
                    with suppress(exceptions.TelegramBadRequest):
                        await bot.delete_message(prev_chat_id, mid)
        except exceptions.TelegramBadRequest:
            # Falhou editar, faz envio normal (fallback)
            await _purge_all_menus(bot, state)
            msg = await bot.send_message(
                chat_id,
                title,
                reply_markup=builder(),
                parse_mode="Markdown",
            )
    else:
        msg = await bot.send_message(
            chat_id,
            title,
            reply_markup=builder(),
            parse_mode="Markdown",
        )

    # 5) regista **só** o menu actual
    await state.update_data(
        menu_msg_id = msg.message_id,
        menu_chat_id = chat_id,
        menu_ids     = [msg.message_id],        # lista reiniciada
    )

    # 6) estado FSM base
    if active == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)   # manter FSM “limpa”

    # 7) (re)inicia timeout automático
    start_menu_timeout(bot, msg, state)
