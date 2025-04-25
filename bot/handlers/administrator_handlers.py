# bot/handlers/administrator_handlers.py
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from bot.filters.role_filter import RoleFilter
from bot.states.admin_menu_states import AdminMenuStates
from bot.menus.common import back_button

router = Router(name="administrator")
router.message.filter(RoleFilter("administrator"))      # garante acesso

# ───────────────────────────────────────────────────────
# entrada no menu principal (já vens de show_menu)
# ───────────────────────────────────────────────────────
@router.callback_query(StateFilter(AdminMenuStates.MAIN), F.data == "admin:agenda")
async def nav_admin(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    # muda de estado (sem ttl)
    await state.set_state(AdminMenuStates.AGENDA)
    await cb.message.edit_reply_markup(          # limpa inline anterior
        reply_markup=None
    )
    await cb.message.answer(
        "📅 *Agenda* — seleccione uma opção:",
        reply_markup=await _agenda_kbd(),
        parse_mode="Markdown",
    )

@router.callback_query(StateFilter(AdminMenuStates.MAIN), F.data == "admin:users")
async def nav_users(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(AdminMenuStates.USERS)
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(
        "👥 *Utilizadores* — seleccione uma opção:",
        reply_markup=await _users_kbd(),
        parse_mode="Markdown",
    )

# ───────────────────────────────────────────────────────
# Agenda
# ───────────────────────────────────────────────────────
async def _agenda_kbd():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("📆 Geral", callback_data="agenda:geral")],
            [InlineKeyboardButton("🩺 Escolher Fisioterapeuta", callback_data="agenda:fisios")],
            [back_button()],
        ]
    )

@router.callback_query(StateFilter(AdminMenuStates.AGENDA), F.data == "agenda:geral")
async def agenda_geral(cb: CallbackQuery):
    await cb.answer("Placeholder: Agenda geral (a implementar)", show_alert=True)

@router.callback_query(StateFilter(AdminMenuStates.AGENDA), F.data == "agenda:fisios")
async def agenda_por_fisio(cb: CallbackQuery):
    await cb.answer("Placeholder: lista de fisioterapeutas (a implementar)", show_alert=True)

@router.callback_query(StateFilter(AdminMenuStates.AGENDA), F.data == "back")
async def agenda_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(AdminMenuStates.MAIN)
    from bot.menus.administrator_menu import build_menu
    await cb.message.edit_text(
        "💻 *Menu:*",
        parse_mode="Markdown",
        reply_markup=build_menu(),
    )

# ───────────────────────────────────────────────────────
# Utilizadores (placeholders)
# ───────────────────────────────────────────────────────
async def _users_kbd():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("🔍 Procurar", callback_data="users:search")],
            [InlineKeyboardButton("➕ Adicionar", callback_data="users:add")],
            [back_button()],
        ]
    )

@router.callback_query(StateFilter(AdminMenuStates.USERS), F.data == "users:search")
async def users_search(cb: CallbackQuery):
    await cb.answer("Placeholder: pesquisa de utilizadores (a implementar)", show_alert=True)

@router.callback_query(StateFilter(AdminMenuStates.USERS), F.data == "users:add")
async def users_add(cb: CallbackQuery):
    await cb.answer("Placeholder: adicionar utilizador (a implementar)", show_alert=True)

@router.callback_query(StateFilter(AdminMenuStates.USERS), F.data == "back")
async def users_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(AdminMenuStates.MAIN)
    from bot.menus.administrator_menu import build_menu
    await cb.message.edit_text(
        "💻 *Menu:*",
        parse_mode="Markdown",
        reply_markup=build_menu(),
    )
