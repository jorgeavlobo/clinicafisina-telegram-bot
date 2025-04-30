# bot/handlers/administrator_handlers.py
from __future__ import annotations

from aiogram import Router, F, exceptions
from aiogram.filters import StateFilter
from aiogram.types   import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.filters.role_filter      import RoleFilter
from bot.states.admin_menu_states import AdminMenuStates, AddUserStates
from bot.menus.common             import back_button, start_menu_timeout
from bot.menus.administrator_menu import (
    build_menu as _main_menu_kbd,
    build_user_type_kbd,
)

router = Router(name="administrator")
router.callback_query.filter(RoleFilter("administrator"))

# ───────────────── builders de sub-menus ────────────────
def _agenda_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📆 Geral",         callback_data="agenda:geral")],
            [InlineKeyboardButton(text="🩺 Fisioterapeuta", callback_data="agenda:fisios")],
            [back_button()],
        ]
    )

def _users_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Procurar",   callback_data="users:search")],
            [InlineKeyboardButton(text="➕ Adicionar", callback_data="users:add")],
            [back_button()],
        ]
    )

# ───────────────────── helpers ────────────────────────
async def _replace_menu(
    cb:    CallbackQuery,
    state: FSMContext,
    text:  str,
    kbd:   InlineKeyboardMarkup,
) -> None:
    """Edita (ou envia) a mensagem-menu e reativa o timeout."""
    try:
        await cb.message.edit_text(text, reply_markup=kbd, parse_mode="Markdown")
        msg = cb.message
    except exceptions.TelegramBadRequest:
        await cb.message.delete()
        msg = await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")
        await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)

    start_menu_timeout(cb.bot, msg, state)

async def _show_main_menu(cb: CallbackQuery, state: FSMContext) -> None:
    """Volta ao menu principal do administrador."""
    await state.set_state(AdminMenuStates.MAIN)
    await _replace_menu(cb, state, "💻 *Menu:*", _main_menu_kbd())

async def _show_users_menu(cb: CallbackQuery, state: FSMContext) -> None:
    """Volta ao menu “Utilizadores” (sub-menu do administrador)."""
    # Define estado de Utilizadores e apresenta o menu correspondente
    await state.set_state(AdminMenuStates.USERS)
    await _replace_menu(cb, state, "👥 *Utilizadores* — seleccione:", _users_kbd())

# ─────────────────────────── MAIN nav ───────────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.MAIN),
    F.data.in_(["admin:agenda", "admin:users", "admin:messages"]),
)
async def admin_main_nav(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    if cb.data == "admin:agenda":
        await state.set_state(AdminMenuStates.AGENDA)
        await _replace_menu(cb, state, "📅 *Agenda* — seleccione:", _agenda_kbd())
    elif cb.data == "admin:users":
        await _show_users_menu(cb, state)
    else:  # admin:messages
        await state.set_state(AdminMenuStates.MESSAGES)
        await _replace_menu(
            cb, state,
            "🚧 *Mensagens* – em desenvolvimento",
            InlineKeyboardMarkup(inline_keyboard=[[back_button()]]),
        )

# ─────────────────────────── Agenda ───────────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.AGENDA),
    F.data.in_(["agenda:geral", "agenda:fisios"]),
)
async def agenda_placeholders(cb: CallbackQuery, state: FSMContext):
    await cb.answer("🚧 Placeholder – em desenvolvimento", show_alert=True)
    try:
        await cb.message.delete()
    except exceptions.TelegramBadRequest:
        pass

# ─────────── Voltar (Agenda, Utilizadores, Mensagens) ───────────
@router.callback_query(
    StateFilter((AdminMenuStates.AGENDA, AdminMenuStates.USERS, AdminMenuStates.MESSAGES)),
    F.data == "back",
)
async def admin_submenu_back(cb: CallbackQuery, state: FSMContext):
    """Trata do botão Voltar nos sub-menus principais do administrador."""
    await cb.answer()
    # Regressar ao menu principal do administrador
    await _show_main_menu(cb, state)

# ─────────────────────── Utilizadores ──────────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.USERS),
    F.data.in_(["users:search", "users:add"]),
)
async def users_menu_options(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    if cb.data == "users:search":
        await state.set_state(AdminMenuStates.USERS_SEARCH)
        await _replace_menu(
            cb, state,
            "🚧 *Procurar utilizador* – em desenvolvimento",
            InlineKeyboardMarkup(inline_keyboard=[[back_button()]]),
        )
    else:  # users:add
        # Entrar no fluxo de “Adicionar utilizador” – escolher o tipo
        await state.set_state(AddUserStates.CHOOSING_ROLE)
        await _replace_menu(
            cb, state,
            "👤 *Adicionar utilizador* — escolha o tipo:",
            build_user_type_kbd(),
        )

# ─────── Voltar a partir de QUALQUER sub-estado em Utilizadores ───────
@router.callback_query(
    StateFilter((
        AdminMenuStates.USERS_SEARCH,
        AddUserStates,                # todo o sub-grupo de adicionar utilizador
    )),
    F.data == "back",
)
async def users_suboption_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _show_users_menu(cb, state)

# ─────── Fluxo “Adicionar Utilizador” – passo 1 (placeholder) ───────
@router.callback_query(StateFilter(AddUserStates.CHOOSING_ROLE), F.data.startswith("role:"))
async def adduser_choose_role(cb: CallbackQuery, state: FSMContext):
    role = cb.data.split(":", 1)[1]
    await cb.answer(f"Escolhido: {role}", show_alert=False)

    await cb.message.edit_text(
        f"✅ *{role.title()}* seleccionado!\n"
        "🚧 Passos seguintes por implementar…",
        parse_mode="Markdown",
    )

    # Regressar ao menu de Utilizadores (fim do fluxo Adicionar utilizador)
    await _show_users_menu(cb, state)
