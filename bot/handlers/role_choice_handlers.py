# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem ≥ 2 papéis.

• Mostra inline-keyboard (timeout generico em bot/menus/common.py)
• Edita a mensagem existente para transições suaves
• Mantém apenas uma mensagem de menu ativa
"""

from __future__ import annotations

from contextlib import suppress
from typing import Iterable

from aiogram import Router, types, exceptions, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus                     import show_menu
from bot.menus.common              import start_menu_timeout
from bot.states.menu_states        import MenuStates
from bot.states.admin_menu_states  import AdminMenuStates

router = Router(name="role_choice")

_LABELS_PT = {
    "patient":         "🧑🏼‍🦯 Paciente",
    "caregiver":       "🤝🏼 Cuidador",
    "physiotherapist": "👩🏼‍⚕️ Fisioterapeuta",
    "accountant":      "📊 Contabilista",
    "administrator":   "👨🏼‍💼 Administrador",
}
def _label(role: str) -> str:
    return _LABELS_PT.get(role.lower(), role.capitalize())

# ───────────────────────── ask_role ─────────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:
    """Envia ou edita o selector de perfis, mantendo apenas uma mensagem ativa."""
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(text=_label(r), callback_data=f"role:{r.lower()}")
        ] for r in roles]
    )
    text = "🔰 *Escolha o perfil:*"

    data = await state.get_data()
    menu_msg_id = data.get("menu_msg_id")
    menu_chat_id = data.get("menu_chat_id")

    if menu_msg_id and menu_chat_id:
        try:
            await bot.edit_message_text(
                chat_id=menu_chat_id,
                message_id=menu_msg_id,
                text=text,
                reply_markup=kbd,
                parse_mode="Markdown",
            )
        except exceptions.TelegramBadRequest:
            # Fallback to sending a new message if editing fails
            msg = await bot.send_message(
                chat_id,
                text,
                reply_markup=kbd,
                parse_mode="Markdown",
            )
            await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)
    else:
        msg = await bot.send_message(
            chat_id,
            text,
            reply_markup=kbd,
            parse_mode="Markdown",
        )
        await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)

    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(roles=[r.lower() for r in roles])
    start_menu_timeout(bot, msg, state)

# ─────────────────── callback «role:…» ────────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    F.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    role = cb.data.split(":", 1)[1].lower()
    data = await state.get_data()
    roles = data.get("roles", [])

    if role not in roles:
        await cb.answer("Perfil inválido.", show_alert=True)
        return

    await state.update_data(active_role=role)

    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)

    # Edit the existing message with the role-specific menu
    await show_menu(
        cb.bot,
        cb.from_user.id,
        state,
        [role],
        edit_message_id=cb.message.message_id,
        edit_chat_id=cb.message.chat.id,
    )

    await cb.answer(f"Perfil {_label(role)} seleccionado!")
