# bot/handlers/role_choice_handlers.py
"""
Profile selector shown when the user owns two or more roles.

• Shows an inline-keyboard selector (generic timeout in bot/menus/common.py)
• After the user chooses a role, the SAME message is edited –
  identical logic to administrator_handlers._replace_menu().
"""

from __future__ import annotations

from contextlib import suppress
from typing import Iterable, List, Dict, Callable

from aiogram import Router, types, F, exceptions
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus.common import start_menu_timeout         # timeout helper
from bot.states.menu_states import MenuStates
from bot.states.admin_menu_states import AdminMenuStates

# import builders used by bot/menus/__init__.py
from bot.menus.patient_menu         import build_menu as _patient
from bot.menus.caregiver_menu       import build_menu as _caregiver
from bot.menus.physiotherapist_menu import build_menu as _physio
from bot.menus.accountant_menu      import build_menu as _accountant
from bot.menus.administrator_menu   import build_menu as _admin

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

# builders por papel (mesma fonte que bot/menus)
_ROLE_MENU: Dict[str, Callable[[], types.InlineKeyboardMarkup]] = {
    "patient":         _patient,
    "caregiver":       _caregiver,
    "physiotherapist": _physio,
    "accountant":      _accountant,
    "administrator":   _admin,
}

# ────────────────────────── ask_role (entry) ─────────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:
    """Send the profile selector and register its message‑ID."""
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
        menu_ids=[msg.message_id],          # list with ONE selector msg
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
    )
    start_menu_timeout(bot, msg, state)

# ─────────────────── helper: edit or recreate menu ──────────────────
async def _replace_menu(
    cb: types.CallbackQuery,
    state: FSMContext,
    text: str,
    kbd: types.InlineKeyboardMarkup,
) -> None:
    """
    Edit the current selector bubble into the first role menu.
    Mirrors administrator_handlers._replace_menu().
    """
    await state.update_data(menu_msg_id=cb.message.message_id,
                            menu_chat_id=cb.message.chat.id)
    try:
        await cb.message.edit_text(text, reply_markup=kbd, parse_mode="Markdown")
        msg = cb.message
    except exceptions.TelegramBadRequest:
        # Fallback: delete + send
        with suppress(exceptions.TelegramBadRequest):
            await cb.message.delete()
        msg = await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")
        await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)

    start_menu_timeout(cb.bot, msg, state)

# ─────────────────────── callback «role:…» ──────────────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    F.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    role = cb.data.split(":", 1)[1].lower()
    data = await state.get_data()
    if role not in data.get("roles", []):
        await cb.answer("Perfil inválido.", show_alert=True)
        return

    # ─── update FSM ────────────────────────────────────────────────
    await state.clear()
    await state.update_data(active_role=role,
                            menu_ids=[cb.message.message_id])  # track the bubble

    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)

    # ─── build first menu for the chosen role ──────────────────────
    builder = _ROLE_MENU.get(role)
    if not builder:                                            # safety
        return await cb.answer("Menu não definido.", show_alert=True)

    title = (
        "💻 *Menu administrador:*"
        if role == "administrator"
        else f"👤 *{role.title()}* – menu principal"
    )
    kbd = builder()

    # edit (or recreate) the selector message → perfectly smooth
    await _replace_menu(cb, state, title, kbd)

    await cb.answer(f"Perfil {_label(role)} seleccionado!")
