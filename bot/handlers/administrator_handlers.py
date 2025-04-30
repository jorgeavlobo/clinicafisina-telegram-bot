# bot/handlers/administrator_handlers.py
"""
Menu de administrador
• Protegido por RoleFilter("administrator")
• Timeout de 60 s para inactividade (start_menu_timeout)
• Botão 🔵 Voltar totalmente funcional
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
    build_menu as _main_menu_kbd,
    build_user_type_kbd,
)

router = Router(name="administrator")
router.callback_query.filter(RoleFilter("administrator"))

# ─────────────── builders de sub-menus ────────────────
def _agenda_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📆 Geral",          callback_data="agenda:geral")],
            [InlineKeyboardButton(text="🩺 Fisioterapeuta", callback_data="agenda:fisios")],
            [back_button()],  # linha própria
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

# ─────────────────── helpers ────────────────────
async def _replace_menu(
    cb:    CallbackQuery,
    state: FSMContext,
    text:  str,
    kbd:   InlineKeyboardMarkup,
) -> None:
    """Edita a mensagem-menu ou, se falhar, envia nova. Reinicia timeout."""
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

# ─────────────────────── MAIN nav ───────────────────────
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
        await state.set_state(AdminMenuStates.USERS)
        await _replace_menu(cb, state, "👥 *Utilizadores* — seleccione:", _users_kbd())
    else:                                   # admin:messages (placeholder)
        await state.set_state(AdminMenuStates.MESSAGES)
        await _replace_menu(
            cb, state,
            "🚧 *Mensagens* — funcionalidade em desenvolvimento",
            InlineKeyboardMarkup(inline_keyboard=[[back_button()]])
        )

# ───────────────────────── Agenda ─────────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.AGENDA),
    F.data.in_(["agenda:geral", "agenda:fisios"]),
)
async def agenda_placeholders(cb: CallbackQuery, state: FSMContext):
    """Mostra popup e remove o menu para não ficar aberto."""
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

# ───────────────────── Utilizadores ──────────────────────
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
            InlineKeyboardMarkup(inline_keyboard=[[back_button()]])
        )
    else:  # users:add
        await state.set_state(AdminMenuStates.USERS_ADD)
        await state.set_state(AddUserStates.CHOOSING_ROLE)          # 1.º passo
        await _replace_menu(
            cb, state,
            "👤 *Adicionar utilizador* — escolha o tipo:",
            build_user_type_kbd()
        )

@router.callback_query(StateFilter(AdminMenuStates.USERS), F.data == "back")
async def users_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _show_main_menu(cb, state)

# ─── “Voltar” a partir de qualquer passo interno de Utilizadores ───
@router.callback_query(
    StateFilter(
        AdminMenuStates.USERS_SEARCH,
        AdminMenuStates.USERS_ADD,
        AddUserStates,               # qualquer sub-estado do fluxo “Adicionar”
    ),
    F.data == "back",
)
async def users_suboption_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(AdminMenuStates.USERS)
    await _replace_menu(cb, state, "👥 *Utilizadores* — seleccione:", _users_kbd())

# ─── Passo “escolher tipo de utilizador” (placeholder) ───
@router.callback_query(
    StateFilter(AddUserStates.CHOOSING_ROLE),
    F.data.startswith("role:"),
)
async def adduser_choose_role(cb: CallbackQuery, state: FSMContext):
    role = cb.data.split(":", 1)[1]
    await cb.answer(f"Escolhido: {role}", show_alert=False)

    await cb.message.edit_text(
        f"✅ *{role.title()}* seleccionado!\n"
        "🚧 Passos seguintes por implementar…",
        parse_mode="Markdown",
    )

    # regressa ao sub-menu Utilizadores
    await state.set_state(AdminMenuStates.USERS)
    await _replace_menu(cb, state, "👥 *Utilizadores* — seleccione:", _users_kbd())
