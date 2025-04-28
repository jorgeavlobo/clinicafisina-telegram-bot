# bot/handlers/administrator_handlers.py
"""
Handlers do menu de Administrador.
Mantém:
• verificação de menu activo
• fecho automático após placeholders
• timeout de 60 s em TODOS os sub-menus
"""

from __future__ import annotations

from aiogram import Router, F, exceptions
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.filters.role_filter import RoleFilter
from bot.menus.common import back_button, start_menu_timeout      # 🆕
from bot.states.admin_menu_states import AdminMenuStates

router = Router(name="administrator")
router.callback_query.filter(RoleFilter("administrator"))

# ──────────────── builders ────────────────
def _agenda_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("📆 Geral", callback_data="agenda:geral")],
            [InlineKeyboardButton("🩺 Escolher Fisioterapeuta", callback_data="agenda:fisios")],
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

# ─────────── utilidades (menu activo + fecho) ───────────
async def _ensure_active(cb: CallbackQuery, state: FSMContext) -> bool:
    data = await state.get_data()
    return cb.message.message_id == data.get("menu_msg_id")

async def _close_menu(cb: CallbackQuery, state: FSMContext) -> None:
    try:
        await cb.message.delete()
    except exceptions.TelegramBadRequest:
        pass
    await state.update_data(menu_msg_id=None, menu_chat_id=None)

# ─────────── helper envio + timeout ───────────
async def _update_admin_submenu(
    cb: CallbackQuery,
    state: FSMContext,
    text: str,
    kbd: InlineKeyboardMarkup,
    new_state: AdminMenuStates,
) -> None:
    await cb.answer()
    if not await _ensure_active(cb, state):
        await cb.answer("Este menu já não está activo.", show_alert=True)
        return

    await cb.message.edit_text(text, reply_markup=kbd, parse_mode="Markdown")
    await state.set_state(new_state)
    start_menu_timeout(cb.bot, cb.message)          # ▶️ timeout (reinicia)

# ─────────── MAIN (Agenda / Utilizadores) ───────────
@router.callback_query(StateFilter(AdminMenuStates.MAIN) & F.data.in_({"admin:agenda", "admin:users"}))
async def admin_main_nav(cb: CallbackQuery, state: FSMContext) -> None:
    if cb.data.endswith("agenda"):
        await _update_admin_submenu(cb, state, "📅 *Agenda* — seleccione uma opção:", _agenda_kbd(), AdminMenuStates.AGENDA)
    else:
        await _update_admin_submenu(cb, state, "👥 *Utilizadores* — seleccione uma opção:", _users_kbd(), AdminMenuStates.USERS)

# ─────────── AGENDA placeholders ───────────
@router.callback_query(StateFilter(AdminMenuStates.AGENDA) & F.data.in_({"agenda:geral", "agenda:fisios"}))
async def agenda_placeholders(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_active(cb, state):
        await cb.answer("Este menu já não está activo.", show_alert=True)
        return
    await cb.answer("🚧 Placeholder – em desenvolvimento", show_alert=True)
    await _close_menu(cb, state)

@router.callback_query(StateFilter(AdminMenuStates.AGENDA) & F.data == "back")
async def agenda_back(cb: CallbackQuery, state: FSMContext) -> None:
    await admin_main_nav(cb.copy(update={"data": "admin:agenda"}), state)

# ─────────── USERS placeholders ───────────
@router.callback_query(StateFilter(AdminMenuStates.USERS) & F.data.in_({"users:search", "users:add"}))
async def users_placeholders(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_active(cb, state):
        await cb.answer("Este menu já não está activo.", show_alert=True)
        return
    await cb.answer("🚧 Placeholder – em desenvolvimento", show_alert=True)
    await _close_menu(cb, state)

@router.callback_query(StateFilter(AdminMenuStates.USERS) & F.data == "back")
async def users_back(cb: CallbackQuery, state: FSMContext) -> None:
    await admin_main_nav(cb.copy(update={"data": "admin:users"}), state)
