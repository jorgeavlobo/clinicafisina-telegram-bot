# bot/handlers/administrator_handlers.py
"""
Handlers do menu de Administrador.

Principais correcções nesta versão
──────────────────────────────────
1. **Botões “Voltar”** – agora funcionam em todos os sub-menus:
   • Agenda, Utilizadores, Procurar, Adicionar e dentro de “Adicionar utilizador”.
2. **Fluxo “Adicionar utilizador”** – ao escolher Paciente/Cuidador/…:
   • O menu fecha-se (inline-keyboard removida) em vez de regressar
     a “Utilizadores – seleccione”.
3. **Gestão de menu activo** – quando o menu é destruído ou fechado,
   as chaves `menu_msg_id` e `menu_chat_id` são limpas no contexto FSM,
   evitando bloqueios no `ActiveMenuMiddleware`.
4. Código reorganizado para clareza e modularidade, mantendo compatibilidade
   com Aiogram 3.20.
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

# ────────────────────────── builders de sub-menus ─────────────────────────
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
            [InlineKeyboardButton(text="🔍 Procurar",  callback_data="users:search")],
            [InlineKeyboardButton(text="➕ Adicionar", callback_data="users:add")],
            [back_button()],
        ]
    )

# ───────────────────────────── helpers ─────────────────────────────
async def _replace_menu(
    cb:    CallbackQuery,
    state: FSMContext,
    text:  str,
    kbd:   InlineKeyboardMarkup,
) -> None:
    """
    Edita (ou cria) a mensagem-menu e reinicia o timeout.

    Sempre que o menu é actualizado, o par (menu_chat_id, menu_msg_id) é
    guardado no FSM para validação futura pelo ActiveMenuMiddleware.
    """
    try:
        await cb.message.edit_text(text, reply_markup=kbd, parse_mode="Markdown")
        msg = cb.message
    except exceptions.TelegramBadRequest:
        # Se a mensagem já expirou para edição, cria nova
        await cb.message.delete()
        msg = await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")

    await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)
    start_menu_timeout(cb.bot, msg, state)

async def _clear_active_menu(state: FSMContext) -> None:
    """Remove do FSM a referência ao menu activo (para o middleware)."""
    await state.update_data(menu_msg_id=None, menu_chat_id=None)

async def _show_main_menu(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminMenuStates.MAIN)
    await _replace_menu(cb, state, "💻 *Menu:*", _main_menu_kbd())

async def _show_users_menu(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminMenuStates.USERS)
    await _replace_menu(cb, state, "👥 *Utilizadores* — seleccione:", _users_kbd())

async def _show_adduser_menu(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddUserStates.CHOOSING_ROLE)
    await _replace_menu(
        cb, state,
        "👤 *Adicionar utilizador* — escolha o tipo:",
        build_user_type_kbd(),
    )

# ─────────────────────────── entrada principal ───────────────────────────
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

# ──────────────────────────── Agenda ────────────────────────────
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
    await _clear_active_menu(state)

# ─────────────── botão VOLTAR (Agenda / Utilizadores / Mensagens) ───────────────
@router.callback_query(
    StateFilter((AdminMenuStates.AGENDA, AdminMenuStates.USERS, AdminMenuStates.MESSAGES)),
    F.data == "back",
)
async def admin_submenu_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _show_main_menu(cb, state)

# ─────────────────────── Utilizadores ───────────────────────
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
        await _show_adduser_menu(cb, state)

# ─────────────── botão VOLTAR em ‘Procurar’ ou ‘Adicionar’ ───────────────
@router.callback_query(
    StateFilter((
        AdminMenuStates.USERS_SEARCH,
        AddUserStates,  # qualquer estado dentro de “Adicionar utilizador”
    )),
    F.data == "back",
)
async def users_suboption_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _show_users_menu(cb, state)

# ───────── Fluxo “Adicionar utilizador” – escolha do tipo ─────────
@router.callback_query(StateFilter(AddUserStates.CHOOSING_ROLE), F.data.startswith("role:"))
async def adduser_choose_role(cb: CallbackQuery, state: FSMContext):
    """
    Placeholder para criação de utilizador.

    Depois de escolher o tipo, o menu é fechado (keyboard removida).
    """
    role = cb.data.split(":", 1)[1]
    await cb.answer(f"✅ {role.title()} seleccionado!", show_alert=False)

    # Fecha o menu: remove o teclado inline
    await cb.message.edit_text(
        f"✅ *{role.title()}* seleccionado!\n"
        "🚧 Passos seguintes por implementar…",
        parse_mode="Markdown",
        reply_markup=None,
    )
    await _clear_active_menu(state)

    # Mantém o utilizador em AdminMenuStates.USERS para futuras acções
    await state.set_state(AdminMenuStates.USERS)
