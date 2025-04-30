# bot/handlers/administrator_handlers.py
"""
Menu de administrador.
• Protegido por RoleFilter("administrator")
• Timeout de 60 s para inactividade (start_menu_timeout)
• Botões 🔙 Voltar totalmente funcionais
"""
from __future__ import annotations

from aiogram import Router, F, exceptions
from aiogram.filters import StateFilter
from aiogram.types   import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.filters.role_filter      import RoleFilter
from bot.states.admin_menu_states import AdminMenuStates, AddUserStates
from bot.menus.common             import back_button, start_menu_timeout
from bot.menus.administrator_menu import (
    build_menu            as _main_menu_kbd,
    build_user_type_kbd,
)

router = Router(name="administrator")
router.callback_query.filter(RoleFilter("administrator"))

# ─────────────── builders de sub-menus ────────────────
def _agenda_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📆 Geral",            callback_data="agenda:geral")],
            [InlineKeyboardButton(text="🩺 Fisioterapeuta",   callback_data="agenda:fisios")],
            [back_button()],
        ]
    )

def _users_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔎 Procurar",  callback_data="users:search")],
            [InlineKeyboardButton(text="➕ Adicionar", callback_data="users:add")],
            [back_button()],
        ]
    )

def _messages_kbd() -> InlineKeyboardMarkup:
    # (ainda não há sub-opções – só botão Voltar)
    return InlineKeyboardMarkup(inline_keyboard=[[back_button()]])

# ─────────────────── helpers ────────────────────
async def _replace_menu(
    cb:    CallbackQuery,
    state: FSMContext,
    text:  str,
    kbd:   InlineKeyboardMarkup,
) -> None:
    """
    Actualiza (edit) a mensagem-menu ou, se falhar, envia nova.
    Reinicia o timeout e actualiza menu_msg_id/menu_chat_id no FSM.
    """
    try:
        await cb.message.edit_text(text, reply_markup=kbd, parse_mode="Markdown")
        msg = cb.message
    except exceptions.TelegramBadRequest:
        await cb.message.delete()
        msg = await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")
        await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)

    start_menu_timeout(cb.bot, msg, state)

async def _show_main_menu(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminMenuStates.MAIN)
    await _replace_menu(cb, state, "💻 *Menu:*", _main_menu_kbd())

# ─────────────────────────── MAIN nav ────────────────────────────
@router.callback_query(StateFilter(AdminMenuStates.MAIN))
async def admin_main_nav(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    routes = {
        "admin:agenda":   ("📅 *Agenda* — seleccione:",       _agenda_kbd,  AdminMenuStates.AGENDA),
        "admin:users":    ("👥 *Utilizadores* — seleccione:", _users_kbd,   AdminMenuStates.USERS),
        "admin:messages": ("💬 *Mensagens* — seleccione:",    _messages_kbd,AdminMenuStates.MESSAGES),
    }
    if cb.data in routes:
        text, builder, new_state = routes[cb.data]
        await state.set_state(new_state)
        await _replace_menu(cb, state, text, builder())

# ─────────────────────────── Agenda ───────────────────────────────
@router.callback_query(StateFilter(AdminMenuStates.AGENDA),
                       F.data.in_(["agenda:geral", "agenda:fisios"]))
async def agenda_placeholders(cb: CallbackQuery, state: FSMContext):
    # mostra pop-up e fecha o menu
    await cb.answer("🚧 Placeholder – em desenvolvimento", show_alert=True)
    try:
        await cb.message.delete()
    except exceptions.TelegramBadRequest:
        pass
    await state.update_data(menu_msg_id=None, menu_chat_id=None)

@router.callback_query(StateFilter(AdminMenuStates.AGENDA), F.data == "back")
async def agenda_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _show_main_menu(cb, state)

# ─────────────────────── Utilizadores ─────────────────────────────
@router.callback_query(StateFilter(AdminMenuStates.USERS),
                       F.data.in_(["users:search", "users:add"]))
async def users_menu_options(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    if cb.data == "users:search":
        await state.set_state(AdminMenuStates.USERS_SEARCH)
        text  = "🚧 *Procurar utilizador* – em desenvolvimento"
        kbd   = InlineKeyboardMarkup(inline_keyboard=[[back_button()]])
    else:
        # → fluxo “Adicionar”: mostrar escolha de tipo
        await state.set_state(AdminMenuStates.USERS_ADD)
        await state.set_state(AddUserStates.CHOOSING_ROLE)
        text  = "👤 *Adicionar utilizador* — escolha o tipo:"
        kbd   = build_user_type_kbd()

    await _replace_menu(cb, state, text, kbd)

@router.callback_query(StateFilter(AdminMenuStates.USERS), F.data == "back")
async def users_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _show_main_menu(cb, state)

# ───── “Voltar” a partir de USERS_SEARCH / USERS_ADD ─────
@router.callback_query(
    StateFilter((AdminMenuStates.USERS_SEARCH, AdminMenuStates.USERS_ADD)),
    F.data == "back")
async def users_suboption_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(AdminMenuStates.USERS)
    await _replace_menu(cb, state, "👥 *Utilizadores* — seleccione:", _users_kbd())

# ────────── Step 1: escolha do tipo de utilizador ──────────
@router.callback_query(StateFilter(AddUserStates.CHOOSING_ROLE),
                       F.data.startswith("role:"))
async def adduser_choose_role(cb: CallbackQuery, state: FSMContext):
    role = cb.data.split(":", 1)[1]
    await cb.answer(f"Escolhido: {role}", show_alert=False)

    # placeholder das etapas seguintes
    await cb.message.edit_text(
        f"✅ *{role.title()}* seleccionado!\n"
        "🚧 Passos seguintes por implementar…",
        parse_mode="Markdown"
    )
    # termina o mini-fluxo
    await state.set_state(AdminMenuStates.USERS)

# ─────────────────────── Mensagens (placeholder) ───────────────────
@router.callback_query(StateFilter(AdminMenuStates.MESSAGES))
async def messages_placeholder(cb: CallbackQuery, state: FSMContext):
    if cb.data == "back":
        await cb.answer()
        await _show_main_menu(cb, state)
        return
    await cb.answer("🚧 Funcionalidade *Mensagens* ainda não disponível",
                    show_alert=True)
