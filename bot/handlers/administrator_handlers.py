# bot/handlers/administrator_handlers.py
"""
Handlers do menu de Administrador.

• usa helpers genéricos de menu_guard (is_active_menu / replace_menu)
• timeout de 60 s nos sub-menus
• botão «Voltar» regressa correctamente ao menu principal
"""

from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.filters.role_filter      import RoleFilter
from bot.states.admin_menu_states import AdminMenuStates
from bot.menus.common             import back_button
from bot.menus.administrator_menu import build_menu as _main_menu_kbd
from bot.handlers.menu_guard      import is_active_menu, replace_menu   # 🆕

router = Router(name="administrator")
router.callback_query.filter(RoleFilter("administrator"))

# ───────────────────────── builders ─────────────────────────
def _agenda_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("📆 Geral",               callback_data="agenda:geral")],
            [InlineKeyboardButton("🩺 Escolher Fisioterapeuta",
                                  callback_data="agenda:fisios")],
            [back_button()],
        ]
    )

def _users_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("🔍 Procurar", callback_data="users:search")],
            [InlineKeyboardButton("➕ Adicionar", callback_data="users:add")],
            [back_button()],
        ]
    )

# ───────────────────────── helpers ─────────────────────────
async def _show_main_menu(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminMenuStates.MAIN)
    await replace_menu(cb, state, "💻 *Menu:*", _main_menu_kbd())

# ───────────────────── navegação principal ───────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.MAIN),
    F.data.in_(("admin:agenda", "admin:users")),
)
async def main_nav(cb: CallbackQuery, state: FSMContext):
    if not await is_active_menu(cb, state):
        # menu_guard tomará conta, mas evitamos processamento duplicado
        return

    await cb.answer()

    if cb.data == "admin:agenda":
        await state.set_state(AdminMenuStates.AGENDA)
        await replace_menu(cb, state,
                           "📅 *Agenda* — seleccione:", _agenda_kbd())
    else:
        await state.set_state(AdminMenuStates.USERS)
        await replace_menu(cb, state,
                           "👥 *Utilizadores* — seleccione:", _users_kbd())

# ─────────────────────────── Agenda ──────────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.AGENDA),
    F.data.in_(("agenda:geral", "agenda:fisios")),
)
async def agenda_placeholders(cb: CallbackQuery, state: FSMContext):
    if not await is_active_menu(cb, state):
        return
    await cb.answer("🚧 Placeholder – em desenvolvimento", show_alert=True)
    await cb.message.delete()
    await state.update_data(menu_msg_id=None, menu_chat_id=None)

@router.callback_query(StateFilter(AdminMenuStates.AGENDA), F.data == "back")
async def agenda_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _show_main_menu(cb, state)

# ─────────────────────── Utilizadores ────────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.USERS),
    F.data.in_(("users:search", "users:add")),
)
async def users_placeholders(cb: CallbackQuery, state: FSMContext):
    if not await is_active_menu(cb, state):
        return
    await cb.answer("🚧 Placeholder – em desenvolvimento", show_alert=True)
    await cb.message.delete()
    await state.update_data(menu_msg_id=None, menu_chat_id=None)

@router.callback_query(StateFilter(AdminMenuStates.USERS), F.data == "back")
async def users_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _show_main_menu(cb, state)
