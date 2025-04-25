# bot/handlers/administrator_handlers.py
"""
Handlers do menu de Administrador.

• Garante que só o *menu actualmente activo* responde aos cliques.
• Depois de um placeholder, remove o menu para evitar clutter.
• Se o utilizador abrir um novo submenu, o anterior é apagado,
  mantendo-se apenas o mais recente.
"""
from __future__ import annotations

from aiogram import Router, F, exceptions
from aiogram.filters import StateFilter
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext

from bot.filters.role_filter import RoleFilter
from bot.states.admin_menu_states import AdminMenuStates
from bot.menus.common import back_button

router = Router(name="administrator")
router.callback_query.filter(RoleFilter("administrator"))

# ────────────────────────────── builders ──────────────────────────────
def _agenda_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📆 Geral",               callback_data="agenda:geral")],
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

# ─────────────────── helpers: menu activo & limpeza ───────────────────
async def _ensure_active_main(cb: CallbackQuery, state: FSMContext) -> bool:
    """True se o clique ocorreu no *menu principal* mais recente."""
    data = await state.get_data()
    return cb.message.message_id == data.get("menu_msg_id")

async def _ensure_active_sub(cb: CallbackQuery, state: FSMContext) -> bool:
    """True se o clique ocorreu no *submenu* (Agenda/Users) mais recente."""
    data = await state.get_data()
    return cb.message.message_id == data.get("admin_msg_id")

async def _purge_prev_submenu(cb: CallbackQuery, state: FSMContext) -> None:
    """Apaga o último submenu caso exista (id guardado em admin_msg_id)."""
    data = await state.get_data()
    old_id: int | None = data.get("admin_msg_id")
    if old_id:
        try:
            await cb.bot.delete_message(cb.message.chat.id, old_id)
        except exceptions.TelegramBadRequest:
            pass                    # já não existe ou demasiado antiga

async def _send_submenu(
    cb: CallbackQuery,
    state: FSMContext,
    text: str,
    kbd: InlineKeyboardMarkup,
) -> None:
    """Remove submenu anterior, apaga a msg do botão clicado e envia novo submenu."""
    await _purge_prev_submenu(cb, state)
    try:
        await cb.message.delete()          # apaga a msg do menu principal
    except exceptions.TelegramBadRequest:
        pass
    msg = await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")
    await state.update_data(admin_msg_id=msg.message_id)

async def _close_submenu(cb: CallbackQuery, state: FSMContext) -> None:
    """Apaga o submenu actual após placeholder."""
    try:
        await cb.message.delete()
    except exceptions.TelegramBadRequest:
        pass
    await state.update_data(admin_msg_id=None)

# ─────────────────────── MENU PRINCIPAL ───────────────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.MAIN),
    F.data.in_({"admin:agenda", "admin:users"}),
)
async def admin_main_nav(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_active_main(cb, state):
        # menu principal antigo → avisa
        await cb.answer(
            "⚠️ Este menu já não está activo. Use /start para abrir um novo.",
            show_alert=True,
        )
        return

    await cb.answer()
    if cb.data == "admin:agenda":
        await state.set_state(AdminMenuStates.AGENDA)
        await _send_submenu(cb, state, "📅 *Agenda* — seleccione uma opção:", _agenda_kbd())
    else:
        await state.set_state(AdminMenuStates.USERS)
        await _send_submenu(cb, state, "👥 *Utilizadores* — seleccione uma opção:", _users_kbd())

# ────────────────────────────── AGENDA ────────────────────────────────
@router.callback_query(StateFilter(AdminMenuStates.AGENDA) & F.data == "back")
async def agenda_back(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_active_sub(cb, state):
        await cb.answer("⚠️ Este menu já expirou.", show_alert=True)
        return
    await cb.answer()
    # regressa ao menu principal (Agenda)
    from bot.menus.administrator_menu import build_menu
    await state.set_state(AdminMenuStates.MAIN)
    await _close_submenu(cb, state)          # remove submenu
    await cb.message.answer("💻 *Menu:*", reply_markup=build_menu(), parse_mode="Markdown")

@router.callback_query(StateFilter(AdminMenuStates.AGENDA) & F.data.in_({"agenda:geral", "agenda:fisios"}))
async def agenda_placeholders(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_active_sub(cb, state):
        await cb.answer("⚠️ Este menu já expirou.", show_alert=True)
        return
    await cb.answer("🚧 Placeholder – em desenvolvimento", show_alert=True)
    await _close_submenu(cb, state)

# ─────────────────────────── UTILIZADORES ─────────────────────────────
@router.callback_query(StateFilter(AdminMenuStates.USERS) & F.data == "back")
async def users_back(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_active_sub(cb, state):
        await cb.answer("⚠️ Este menu já expirou.", show_alert=True)
        return
    await cb.answer()
    from bot.menus.administrator_menu import build_menu
    await state.set_state(AdminMenuStates.MAIN)
    await _close_submenu(cb, state)
    await cb.message.answer("💻 *Menu:*", reply_markup=build_menu(), parse_mode="Markdown")

@router.callback_query(StateFilter(AdminMenuStates.USERS) & F.data.in_({"users:search", "users:add"}))
async def users_placeholders(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_active_sub(cb, state):
        await cb.answer("⚠️ Este menu já expirou.", show_alert=True)
        return
    await cb.answer("🚧 Placeholder – em desenvolvimento", show_alert=True)
    await _close_submenu(cb, state)
