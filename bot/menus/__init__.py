# bot/menus/__init__.py
"""
Constrói e gere os menus de cada perfil.

• Se o utilizador tiver vários perfis e ainda não escolheu um,
  delega no selector ask_role().
• Mantém «active_role» mesmo após limpezas de FSM (clear_keep_role).
• Ao abrir um menu novo *apaga todos* os menus anteriores que ainda
  possam estar no histórico (lista menu_ids).
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
async def _purge_all_menus(bot: Bot, state: FSMContext) -> None:
    """
    Apaga **todos** os menus cujo ID esteja registado em `menu_ids`
    (lista guardada no FSM). Essa lista é actualizada no final de
    show_menu() para conter só o menu acabado de abrir.
    """
    data      = await state.get_data()
    chat_id   = data.get("menu_chat_id")
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
    edit_message_id: int = None,
    edit_chat_id: int = None,
) -> None:
    # Determina o papel ativo
    data = await state.get_data()
    active_role = requested or data.get("active_role")
    
    if active_role is None:
        if len(roles) == 1:
            active_role = roles[0]
        else:
            # Se houver múltiplos papéis e nenhum ativo, pede ao usuário para escolher
            await bot.send_message(chat_id, "Por favor, selecione um papel.")
            return

    # Obtém a função de construção de menu para o papel ativo
    builder = _ROLE_MENU.get(active_role)
    if builder is None:
        await bot.send_message(chat_id, f"Menu para o papel '{active_role}' não está disponível.")
        return

    # Constrói o menu
    reply_markup = builder()

    # Define o título do menu com base no papel
    title = f"Menu de {active_role.capitalize()}"

    # Tenta editar a mensagem existente ou envia uma nova
    if edit_message_id and edit_chat_id:
        try:
            await bot.edit_message_text(
                chat_id=edit_chat_id,
                message_id=edit_message_id,
                text=title,
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )
            msg_id = edit_message_id
            chat_id = edit_chat_id
        except exceptions.TelegramBadRequest:
            # Se falhar (ex.: mensagem não existe), envia nova mensagem
            msg = await bot.send_message(
                chat_id,
                title,
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )
            msg_id = msg.message_id
            chat_id = msg.chat.id
    else:
        # Caso não haja IDs para edição, envia nova mensagem
        msg = await bot.send_message(
            chat_id,
            title,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
        msg_id = msg.message_id
        chat_id = msg.chat.id

    # Atualiza o estado com os IDs da mensagem
    await state.update_data(menu_msg_id=msg_id, menu_chat_id=chat_id)
