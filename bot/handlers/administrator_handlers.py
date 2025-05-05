# bot/handlers/administrator_handlers.py
"""
Administrator menu handlers (Aiogram 3.x)

• Navegação do menu de administrador
• Fluxo “Adicionar Utilizador” (FSM AddUserFlow)
• Menu rendering através de ui_helpers.refresh_menu
"""

from __future__ import annotations

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from bot.states.admin_menu_states import AdminMenuStates
from bot.states.add_user_flow     import AddUserFlow
from bot.menus.ui_helpers         import (
    back_button,
    cancel_back_kbd,
    refresh_menu,
    close_menu_with_alert,
)
from bot.menus.administrator_menu import (
    build_menu as _main_menu_kbd,
    build_user_type_kbd,
)

router = Router(name="administrator")

# ───────────────────────── sub-keyboards ──────────────────────────
def _agenda_kbd() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="📆 Geral",          callback_data="agenda:geral")],
            [types.InlineKeyboardButton(text="🩺 Fisioterapeuta", callback_data="agenda:fisios")],
            [back_button()],
        ]
    )

def _users_kbd() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🔍 Procurar",  callback_data="users:search")],
            [types.InlineKeyboardButton(text="➕ Adicionar", callback_data="users:add")],
            [back_button()],
        ]
    )

# ─────────────────────────── helper UI ───────────────────────────
async def _swap_menu(
    cb: types.CallbackQuery,
    state: FSMContext,
    text: str,
    kbd: types.InlineKeyboardMarkup,
) -> None:
    """Obter menu_msg_id actual e delegar em refresh_menu()."""
    target_msg_id = (await state.get_data()).get("menu_msg_id")
    await refresh_menu(
        bot       = cb.bot,
        state     = state,
        chat_id   = cb.message.chat.id,
        message_id= target_msg_id,
        text      = text,
        keyboard  = kbd,
    )

# ─────────────────── wrappers de navegação ───────────────────
async def _main(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminMenuStates.MAIN)
    await _swap_menu(cb, state, "👨🏼‍💻 *Menu:*", _main_menu_kbd())

async def _agenda(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminMenuStates.AGENDA)
    await _swap_menu(cb, state, "📅 *Agenda* — seleccione:", _agenda_kbd())

async def _users(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminMenuStates.USERS)
    await _swap_menu(cb, state, "👥 *Utilizadores* — seleccione:", _users_kbd())

async def _add_user(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddUserFlow.CHOOSING_ROLE)
    await _swap_menu(
        cb,
        state,
        "👤 *Adicionar utilizador* — escolha o tipo:",
        build_user_type_kbd(),
    )

# ─────────────────────────── MENU PRINCIPAL ───────────────────────────
@router.callback_query(AdminMenuStates.MAIN, F.data == "admin:agenda")
async def open_agenda(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await _agenda(cb, state)

@router.callback_query(AdminMenuStates.MAIN, F.data == "admin:users")
async def open_users(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await _users(cb, state)

@router.callback_query(AdminMenuStates.MAIN, F.data == "admin:messages")
async def open_messages(cb: types.CallbackQuery, state: FSMContext):
    await close_menu_with_alert(cb, "🚧 Mensagens – em desenvolvimento", state)
    await state.set_state(AdminMenuStates.MAIN)

# ─────────────────────────────── Agenda ───────────────────────────────
@router.callback_query(AdminMenuStates.AGENDA, F.data.in_(["agenda:geral", "agenda:fisios"]))
async def agenda_placeholder(cb: types.CallbackQuery, state: FSMContext):
    destino = "Geral" if cb.data.endswith("geral") else "Fisioterapeuta"
    await close_menu_with_alert(cb, f"📅 *Agenda {destino}* – em desenvolvimento", state)
    await state.set_state(AdminMenuStates.MAIN)

@router.callback_query(AdminMenuStates.AGENDA, F.data == "back")
async def agenda_back(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await _main(cb, state)

# ─────────────────────────── Utilizadores ───────────────────────────
@router.callback_query(AdminMenuStates.USERS, F.data == "users:search")
async def users_search(cb: types.CallbackQuery, state: FSMContext):
    await close_menu_with_alert(cb, "🔍 *Pesquisar utilizador* – em desenvolvimento", state)
    await state.set_state(AdminMenuStates.USERS)

@router.callback_query(AdminMenuStates.USERS, F.data == "users:add")
async def users_add(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await _add_user(cb, state)

@router.callback_query(AdminMenuStates.USERS, F.data == "back")
async def users_back(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await _main(cb, state)

# ───────────── “Escolher tipo de utilizador” (AddUserFlow) ─────────────
@router.callback_query(AddUserFlow.CHOOSING_ROLE, F.data.startswith("role:"))
async def adduser_choose_role(cb: types.CallbackQuery, state: FSMContext):
    role = cb.data.split(":", 1)[1]
    await close_menu_with_alert(cb, f"✅ *{role.title()}* seleccionado! Vamos pedir os dados…", state)
    await state.update_data(role=role)
    await cb.message.answer("Primeiro(s) nome(s):", reply_markup=cancel_back_kbd())
    await state.set_state(AddUserFlow.FIRST_NAME)

@router.callback_query(AddUserFlow.CHOOSING_ROLE, F.data == "back")
async def adduser_choose_role_back(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await _users(cb, state)
