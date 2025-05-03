# bot/handlers/role_choice_handlers.py
"""
Selector de perfil:
• ask_role  – envia o menu “🔰 Escolha o perfil:”
• choose_role – trata o clique, apaga o selector e mostra o menu do perfil
"""

from __future__ import annotations
from typing import Iterable
import logging

from aiogram import Router, types, exceptions
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus import show_menu
from bot.menus.common import start_menu_timeout        # _hide_menu_after NUNCA!
from bot.config import MESSAGE_TIMEOUT
from bot.states.menu_states import MenuStates
from bot.states.admin_menu_states import AdminMenuStates

router = Router(name="role_choice")
log = logging.getLogger(__name__)

# —— labels ——————————————————————————
_LABELS_PT: dict[str, str] = {
    "patient":         "🧑🏼‍🦯 Paciente",
    "caregiver":       "🤝🏼 Cuidador",
    "physiotherapist": "👩🏼‍⚕️ Fisioterapeuta",
    "accountant":      "📊 Contabilista",
    "administrator":   "👨🏼‍💼 Administrador",
}
def _label(role: str) -> str:
    return _LABELS_PT.get(role.lower(), role.capitalize())

# —— ask_role —————————————————————————
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:
    """Envia o selector inline com os perfis permitidos."""
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(
                text=_label(r),
                callback_data=f"role:{r.lower()}",
            )
        ] for r in roles]
    )
    msg = await bot.send_message(
        chat_id,
        "🔰 *Escolha o perfil:*",
        reply_markup=kbd,
        parse_mode="Markdown",
    )

    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        roles=[r.lower() for r in roles],
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
    )
    start_menu_timeout(bot, msg, state)

# —— choose_role ——————————————————————
@router.callback_query(
    lambda c: c.data and c.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    """Apaga o selector e abre o menu do perfil escolhido."""
    await cb.answer()                           # pára o spinner

    role  = cb.data.split(":", 1)[1].lower()
    data  = await state.get_data()
    roles = data.get("roles", [])

    if role not in roles:
        await cb.answer("Perfil inválido.", show_alert=True)
        return

    # — 1. apagar a mensagem-selector —
    try:
        log.debug("delete_message id=%s", cb.message.message_id)
        await cb.message.delete()
    except exceptions.TelegramBadRequest as e:
        log.warning("delete falhou: %s – tentar blank", e)
        try:
            await cb.message.edit_reply_markup(reply_markup=None)
            await cb.message.edit_text("\u200B", parse_mode=None)
            log.debug("selector blanked via edit")
        except exceptions.TelegramBadRequest as e2:
            log.error("edit_text falhou: %s", e2)

    # — 2. actualizar FSM / role —
    await state.clear()
    await state.update_data(active_role=role, roles=roles)

    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)

    await cb.answer(f"Perfil {_label(role)} seleccionado!")
    await show_menu(cb.bot, cb.message.chat.id, state, [role])
