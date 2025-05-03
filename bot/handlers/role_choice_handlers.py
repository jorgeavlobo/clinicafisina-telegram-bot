# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem ≥ 2 papéis.

• Mostra inline-keyboard com timeout comum (common.py)
• Cancela a task de timeout assim que o utilizador escolhe
• Remove teclado, tenta apagar a mensagem e só depois abre o novo menu
"""

from __future__ import annotations
import asyncio
from contextlib import suppress
from typing import Iterable

import logging
from aiogram import Router, types, exceptions
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus                    import show_menu
from bot.menus.common             import start_menu_timeout, _hide_menu_after
from bot.config                   import MENU_TIMEOUT, MESSAGE_TIMEOUT
from bot.states.menu_states       import MenuStates
from bot.states.admin_menu_states import AdminMenuStates

router = Router(name="role_choice")

_LABELS_PT = {
    "patient":         "🧑🏼‍🦯 Paciente",
    "caregiver":       "🤝🏼 Cuidador",
    "physiotherapist": "👩🏼‍⚕️ Fisioterapeuta",
    "accountant":      "📊 Contabilista",
    "administrator":   "👨🏼‍💼 Administrador",
}
def _label(r: str) -> str: return _LABELS_PT.get(r.lower(), r.capitalize())


# ───────────────────── ask_role ─────────────────────
async def ask_role(bot: types.Bot, chat_id: int, state: FSMContext, roles: Iterable[str]) -> None:
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=_label(r), callback_data=f"role:{r.lower()}")]
            for r in roles
        ]
    )
    msg = await bot.send_message(chat_id, "🔰 *Escolha o perfil:*", reply_markup=kbd, parse_mode="Markdown")

    # guarda tudo o que precisamos para limpeza posterior
    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        roles=[r.lower() for r in roles],
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
    )

    # timeout: cria task e guarda handle para podermos cancelar
    task = asyncio.create_task(_hide_menu_after(
        bot             = bot,
        chat_id         = msg.chat.id,
        msg_id          = msg.message_id,
        state           = state,
        menu_timeout    = MENU_TIMEOUT,
        message_timeout = MESSAGE_TIMEOUT,
    ))
    await state.update_data(timeout_task=task)


# ───────────────── callback «role:…» ─────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    lambda c: c.data and c.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    role = cb.data.split(":", 1)[1].lower()
    data = await state.get_data()
    roles = data.get("roles", [])

    if role not in roles:
        await cb.answer("Perfil inválido.", show_alert=True)
        return

    selector_id = data.get("menu_msg_id")
    selector_chat = data.get("menu_chat_id")

    # Passo 1: Tentar editar a mensagem para torná-la invisível
    try:
        await cb.bot.edit_message_text(
            chat_id=selector_chat,
            message_id=selector_id,
            text="\u200B",  # Espaço de largura zero
            reply_markup=None  # Remove os botões
        )
        logging.info(f"Mensagem {selector_id} editada para ficar invisível.")
    except exceptions.TelegramBadRequest as e:
        logging.error(f"Erro ao editar a mensagem {selector_id}: {e}")

    # Passo 2: Tentar apagar a mensagem
    try:
        await cb.bot.delete_message(chat_id=selector_chat, message_id=selector_id)
        logging.info(f"Mensagem {selector_id} apagada com sucesso.")
    except exceptions.TelegramBadRequest as e:
        logging.warning(f"Não foi possível apagar a mensagem {selector_id}: {e}")

    # Prosseguir com a troca de perfil
    await state.clear()
    await state.update_data(active_role=role, roles=roles)

    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)

    await cb.answer(f"Perfil {role} seleccionado!")
    await show_menu(cb.bot, cb.message.chat.id, state, [role])
