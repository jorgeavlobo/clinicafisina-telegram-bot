# bot/handlers/role_choice_handlers.py
from __future__ import annotations
from contextlib import suppress
from typing import Iterable

from aiogram import Router, types, exceptions
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus                     import show_menu
from bot.menus.common              import start_menu_timeout, hide_menu_now
from bot.config                    import MESSAGE_TIMEOUT
from bot.states.menu_states        import MenuStates
from bot.states.admin_menu_states  import AdminMenuStates

router = Router(name="role_choice")

_LABELS_PT: dict[str, str] = {
    "patient":         "🧑🏼‍🦯 Paciente",
    "caregiver":       "🤝🏼 Cuidador",
    "physiotherapist": "👩🏼‍⚕️ Fisioterapeuta",
    "accountant":      "📊 Contabilista",
    "administrator":   "👨🏼‍💼 Administrador",
}
def _label(role: str) -> str:
    """Return localised label for role; fallback to capitalised name."""
    return _LABELS_PT.get(role.lower(), role.capitalize())


# ───────────────────────── ask_role ─────────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:
    """Send the profile-selector menu and set FSM into waiting state."""
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=_label(r),
                                        callback_data=f"role:{r.lower()}")]
            for r in roles
        ]
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
        menu_msg_id=msg.message_id,      # selector message ID
        menu_chat_id=msg.chat.id,
    )
    start_menu_timeout(bot, msg, state)


# ─────────────────── callback “role:…” ───────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    lambda c: c.data and c.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    """Handle the user picking a role from the selector menu."""
    role  = cb.data.split(":", 1)[1].lower()
    data  = await state.get_data()
    roles = data.get("roles", [])

    if role not in roles:
        await cb.answer("Perfil inválido.", show_alert=True)
        return

    # 0️⃣  immediate feedback – stop the Telegram loading spinner
    await cb.answer()

    selector_id   = data.get("menu_msg_id")
    selector_chat = data.get("menu_chat_id")

    # ─── 1. try to DELETE the selector message ───
    deleted = False
    if selector_id and selector_chat:
        try:
            await cb.bot.delete_message(selector_chat, selector_id)
            deleted = True
        except exceptions.TelegramBadRequest:
            deleted = False

        # ─── 2. fallback: blank the message instantly ───
        if not deleted:
            hide_menu_now(cb.bot, selector_chat, selector_id, state)

    # ─── 3. proceed with role switch ───
    await state.clear()
    await state.update_data(active_role=role, roles=roles)

    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        # regular users have no global FSM state
        await state.set_state(None)

    # brief confirmation toast (non-blocking)
    await cb.answer(f"Perfil {_label(role)} seleccionado!")

    # finally, show the main menu for the selected role
    await show_menu(cb.bot, cb.message.chat.id, state, [role])
