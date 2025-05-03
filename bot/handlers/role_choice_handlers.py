# bot/handlers/role_choice_handlers.py
"""
Handle the 'choose profile' inline-menu.

• ask_role()     – sends selector with buttons
• choose_role()  – processes click, hides selector, switches role
"""

from __future__ import annotations
from typing import Iterable
import logging

from aiogram import Router, types, exceptions          # ← exceptions ADDED
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus                     import show_menu
from bot.menus.common              import start_menu_timeout
from bot.config                    import MESSAGE_TIMEOUT
from bot.states.menu_states        import MenuStates
from bot.states.admin_menu_states  import AdminMenuStates

router = Router(name="role_choice")
log = logging.getLogger(__name__)                      # temporary debug

_LABELS_PT: dict[str, str] = {
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
    """Send the inline selector “🔰 Escolha o perfil:”."""
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


# ─────────────────── callback “role:…” ───────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    lambda c: c.data and c.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    """Hide selector and load the menu of the chosen profile."""
    await cb.answer()                                 # stop Telegram spinner

    role  = cb.data.split(":", 1)[1].lower()
    data  = await state.get_data()
    roles = data.get("roles", [])

    if role not in roles:
        await cb.answer("Perfil inválido.", show_alert=True)
        return

    # 1️⃣ hide selector message immediately
    try:
        log.debug("Trying delete_message id=%s", cb.message.message_id)
        await cb.message.delete()
        log.debug("delete_message OK")
    except exceptions.TelegramBadRequest as e:
        log.warning("delete_message failed: %s", e)
        try:
            await cb.message.edit_reply_markup(reply_markup=None)
            await cb.message.edit_text("\u200B", parse_mode=None)
            log.debug("Selector blanked via edit_text")
        except exceptions.TelegramBadRequest as e2:
            log.error("edit_text failed: %s", e2)

    # 2️⃣ switch FSM / role --------------------------------
    await state.clear()
    await state.update_data(active_role=role, roles=roles)

    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)

    await cb.answer(f"Perfil {_label(role)} seleccionado!")
    await show_menu(cb.bot, cb.message.chat.id, state, [role])
