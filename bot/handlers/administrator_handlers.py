# bot/handlers/administrator_handlers.py
"""
Administrator menu handlers.
- Ensures only the active menu responds (via global middleware).
- 60 s timeout for menu inactivity.
- "Voltar" (Back) button works correctly.
"""
from __future__ import annotations

from aiogram import Router, F, exceptions
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.filters.role_filter      import RoleFilter
from bot.states.admin_menu_states import AdminMenuStates
from bot.menus.common             import back_button, start_menu_timeout
from bot.menus.administrator_menu import build_menu as _main_menu_kbd

router = Router(name="administrator")
router.callback_query.filter(RoleFilter("administrator"))

# ───────────────────────────── builders ──────────────────────────────
def _agenda_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📆 Geral", callback_data="agenda:geral")],
            [InlineKeyboardButton(text="🩺 Escolher Fisioterapeuta", callback_data="agenda:fisios")],
            [back_button()],
        ]
    )

def _users_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Procurar", callback_data="users:search")],
            [InlineKeyboardButton(text="➕ Adicionar", callback_data="users:add")],
            [back_button()],
        ]
    )

# ───────────────────────── helpers ──────────────────────────────────
async def _replace_menu(
    cb: CallbackQuery,
    state: FSMContext,
    text: str,
    kbd: InlineKeyboardMarkup,
) -> None:
    """
    Edit the current menu message to update its content, or send a new message if editing fails (e.g., message is too old).
    Updates the FSM state data with the new menu message ID and restarts the inactivity timeout.
    """
    try:
        await cb.message.edit_text(text, reply_markup=kbd, parse_mode="Markdown")
        msg = cb.message
    except exceptions.TelegramBadRequest:
        # If edit fails (message might be obsolete), delete it and send a new one
        await cb.message.delete()
        msg = await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")
        # Update FSM context with the new active menu message details
        await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)

    # Start (or reset) the 60-second inactivity timeout for this menu
    start_menu_timeout(cb.bot, msg, state)

async def _show_main_menu(cb: CallbackQuery, state: FSMContext) -> None:
    """
    Return to the main Administrator menu.
    """
    await state.set_state(AdminMenuStates.MAIN)
    await _replace_menu(cb, state, "💻 *Menu:*", _main_menu_kbd())

# ─────────────────────────── MAIN nav ───────────────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.MAIN),
    F.data.in_(["admin:agenda", "admin:users"])
)
async def admin_main_nav(cb: CallbackQuery, state: FSMContext):
    # Navigate from the main menu to the "Agenda" or "Utilizadores" submenu
    await cb.answer()  # acknowledge the interaction promptly

    if cb.data == "admin:agenda":
        await state.set_state(AdminMenuStates.AGENDA)
        await _replace_menu(cb, state, "📅 *Agenda* — seleccione:", _agenda_kbd())
    else:
        await state.set_state(AdminMenuStates.USERS)
        await _replace_menu(cb, state, "👥 *Utilizadores* — seleccione:", _users_kbd())

# ─────────────────────────── Agenda ────────────────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.AGENDA),
    F.data.in_(["agenda:geral", "agenda:fisios"])
)
async def agenda_placeholders(cb: CallbackQuery, state: FSMContext):
    # Placeholder interaction (not implemented yet) for Agenda options
    await cb.answer("🚧 Placeholder – em desenvolvimento", show_alert=True)
    await cb.message.delete()
    await state.update_data(menu_msg_id=None, menu_chat_id=None)

@router.callback_query(StateFilter(AdminMenuStates.AGENDA), F.data == "back")
async def agenda_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _show_main_menu(cb, state)

# ──────────────────────── Utilizadores ─────────────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.USERS),
    F.data.in_(["users:search", "users:add"])
)
async def users_placeholders(cb: CallbackQuery, state: FSMContext):
    # Placeholder interaction (not implemented yet) for Users options
    await cb.answer("🚧 Placeholder – em desenvolvimento", show_alert=True)
    await cb.message.delete()
    await state.update_data(menu_msg_id=None, menu_chat_id=None)

@router.callback_query(StateFilter(AdminMenuStates.USERS), F.data == "back")
async def users_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _show_main_menu(cb, state)
