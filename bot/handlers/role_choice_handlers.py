# bot/handlers/role_choice_handlers.py
"""
Profile selector shown when the user owns two or more roles.

• Sends an inline-keyboard selector (generic timeout in bot/menus/common.py)
• Keeps track of all selector-message IDs so time-outs can hide them
• After the user chooses a role the SAME message is **edited** (no jump)
"""

from __future__ import annotations

from typing import Iterable, List

from aiogram import Router, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus import show_menu
from bot.menus.common import (
    start_menu_timeout,
    replace_or_create_menu,      # ← new helper: smooth menu transition
)
from bot.states.menu_states import MenuStates
from bot.states.admin_menu_states import AdminMenuStates

router = Router(name="role_choice")

# ──────────────────────────── UI helpers ────────────────────────────
_LABELS_PT = {
    "patient":         "🧑🏼‍🦯 Paciente",
    "caregiver":       "🤝🏼 Cuidador",
    "physiotherapist": "👩🏼‍⚕️ Fisioterapeuta",
    "accountant":      "📊 Contabilista",
    "administrator":   "👨🏼‍💼 Administrador",
}
def _label(role: str) -> str:
    return _LABELS_PT.get(role.lower(), role.capitalize())

# ────────────────────────── ask_role (entry) ─────────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:
    """
    Show the profile selector and record EVERY message-ID created so that
    the background timeout task can later hide them if they become stale.
    """
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

    data = await state.get_data()
    menu_ids: List[int] = data.get("menu_ids", [])  # accumulate
    menu_ids.append(msg.message_id)

    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        roles=[r.lower() for r in roles],
        menu_ids=menu_ids,
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
    )

    start_menu_timeout(bot, msg, state)

# ─────────────────────── callback «role:…» ──────────────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    F.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    role = cb.data.split(":", 1)[1].lower()
    data = await state.get_data()
    if role not in data.get("roles", []):
        # Unknown role – ignore
        await cb.answer("Perfil inválido.", show_alert=True)
        return

    # ─── update the FSM with the new active role ────────────────────
    await state.clear()                       # wipe *but* we re-insert below
    await state.update_data(active_role=role)

    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)

    # ─── build first menu for the chosen role ───────────────────────
    # Assumes `show_menu.build(role)` → (keyboard, text).  Adapt if needed.
    kbd, text = await show_menu.build(role)

    # Edit the selector itself or create a fresh one if editing fails
    new_msg = await replace_or_create_menu(
        cb.bot,
        state,
        chat_id=cb.message.chat.id,
        message=cb.message,      # try to reuse the same bubble → no “jump”
        text=text,
        kbd=kbd,
    )

    # Restart inactivity timer for the (possibly new) menu message
    start_menu_timeout(cb.bot, new_msg, state)

    await cb.answer(f"Perfil {_label(role)} seleccionado!")
