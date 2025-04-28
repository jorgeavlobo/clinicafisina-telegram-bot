# bot/handlers/administrator_handlers.py
"""
Handlers do menu de Administrador

Agora utiliza bot.handlers.menu_guard para:
• verificar se o callback pertence ao menu activo
• substituir/actualizar menus e rearmar timeout de 60 s
• encerrar o menu nas opções “terminais”
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

# utilitários genéricos
from bot.handlers.menu_guard import is_active, replace_menu, close_menu

router = Router(name="administrator")
router.callback_query.filter(RoleFilter("administrator"))

# ─────────────────────────── builders ────────────────────────────
def _agenda_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("📆 Geral",               callback_data="agenda:geral")],
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


async def _show_main(cb: CallbackQuery, state: FSMContext) -> None:
    """Volta ao menu principal ‹Agenda / Utilizadores›."""
    await state.set_state(AdminMenuStates.MAIN)
    await replace_menu(cb, state, "💻 *Menu:*", _main_menu_kbd())

# ─────────────────────────── MAIN nav ────────────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.MAIN),
    F.data.in_(("admin:agenda", "admin:users"))
)
async def main_nav(cb: CallbackQuery, state: FSMContext):
    if not await is_active(cb, state):
        await cb.answer("⚠️ Este menu já não está activo.", show_alert=True)
        return
    await cb.answer()

    if cb.data.endswith("agenda"):
        await state.set_state(AdminMenuStates.AGENDA)
        await replace_menu(cb, state, "📅 *Agenda* — seleccione:", _agenda_kbd())
    else:
        await state.set_state(AdminMenuStates.USERS)
        await replace_menu(cb, state, "👥 *Utilizadores* — seleccione:", _users_kbd())

# ─────────────────────────── Agenda ──────────────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.AGENDA),
    F.data.in_(("agenda:geral", "agenda:fisios"))
)
async def agenda_terminal(cb: CallbackQuery, state: FSMContext):
    if not await is_active(cb, state):
        await cb.answer("⚠️ Este menu já não está activo.", show_alert=True)
        return

    await cb.answer("🚧 Placeholder – em desenvolvimento", show_alert=True)
    await close_menu(cb, state)                 # encerra menu após acção


@router.callback_query(StateFilter(AdminMenuStates.AGENDA), F.data == "back")
async def agenda_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _show_main(cb, state)

# ───────────────────────── Utilizadores ──────────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.USERS),
    F.data.in_(("users:search", "users:add"))
)
async def users_terminal(cb: CallbackQuery, state: FSMContext):
    if not await is_active(cb, state):
        await cb.answer("⚠️ Este menu já não está activo.", show_alert=True)
        return

    await cb.answer("🚧 Placeholder – em desenvolvimento", show_alert=True)
    await close_menu(cb, state)


@router.callback_query(StateFilter(AdminMenuStates.USERS), F.data == "back")
async def users_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _show_main(cb, state)

# ─────────────────────── fallback (menus antigos) ──────────────────
@router.callback_query(
    RoleFilter("administrator"),
    F.data.startswith(("admin:", "agenda:", "users:"))
)
async def old_menu(cb: CallbackQuery):
    await cb.answer(
        "⚠️ Este menu já não está activo.\n"
        "Envie /start ou prima *Menu* para abrir um novo.",
        show_alert=True,
    )
