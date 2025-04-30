# bot/handlers/administrator_handlers.py
"""
Handlers do menu de Administrador.

• Corrige todos os fluxos de “Voltar” (back) que não regressavam ao menu correcto.
• Mantém o utilizador no submenu “Adicionar utilizador” depois de escolher o
  tipo (Paciente, Cuidador, …), em vez de saltar para “Utilizadores – seleccione”.
• Garante que o ID da mensagem-menu activa é sempre actualizado no FSM, evitando
  que o ActiveMenuMiddleware rejeite callbacks legítimas.
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
    """Teclado inline do submenu Agenda."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📆 Geral",         callback_data="agenda:geral")],
            [InlineKeyboardButton(text="🩺 Fisioterapeuta", callback_data="agenda:fisios")],
            [back_button()],
        ]
    )

def _users_kbd() -> InlineKeyboardMarkup:
    """Teclado inline do submenu Utilizadores."""
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
    guardado no FSM para que o `ActiveMenuMiddleware` valide futuras callbacks.
    """
    try:
        # Tenta editar a mensagem existente
        await cb.message.edit_text(text, reply_markup=kbd, parse_mode="Markdown")
        msg = cb.message
    except exceptions.TelegramBadRequest:
        # Caso falhe (p.ex. mensagem demasiado antiga), apaga-a e cria nova
        await cb.message.delete()
        msg = await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")

    # ✱ GARANTE que o middleware reconhece este menu como o activo
    await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)

    # (Re)inicia o timeout de inactividade
    start_menu_timeout(cb.bot, msg, state)

async def _show_main_menu(cb: CallbackQuery, state: FSMContext) -> None:
    """Mostra o menu principal de Administrador."""
    await state.set_state(AdminMenuStates.MAIN)
    await _replace_menu(cb, state, "💻 *Menu:*", _main_menu_kbd())

async def _show_users_menu(cb: CallbackQuery, state: FSMContext) -> None:
    """Mostra o submenu ‘Utilizadores’."""
    await state.set_state(AdminMenuStates.USERS)
    await _replace_menu(cb, state, "👥 *Utilizadores* — seleccione:", _users_kbd())

async def _show_adduser_menu(cb: CallbackQuery, state: FSMContext) -> None:
    """Mostra o fluxo ‘Adicionar utilizador — escolha o tipo’."""
    await state.set_state(AddUserStates.CHOOSING_ROLE)
    await _replace_menu(
        cb, state,
        "👤 *Adicionar utilizador* — escolha o tipo:",
        build_user_type_kbd(),
    )

# ─────────────────────── Navegação principal ───────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.MAIN),
    F.data.in_(["admin:agenda", "admin:users", "admin:messages"]),
)
async def admin_main_nav(cb: CallbackQuery, state: FSMContext):
    """Entrada nos três sub-menus principais do Administrador."""
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
    """Placeholders para opções de Agenda ainda não implementadas."""
    await cb.answer("🚧 Placeholder – em desenvolvimento", show_alert=True)
    try:
        await cb.message.delete()
    except exceptions.TelegramBadRequest:
        pass

# ────────────── Botão VOLTAR nos sub-menus principais ──────────────
@router.callback_query(
    StateFilter((AdminMenuStates.AGENDA, AdminMenuStates.USERS, AdminMenuStates.MESSAGES)),
    F.data == "back",
)
async def admin_submenu_back(cb: CallbackQuery, state: FSMContext):
    """Regressa do submenu actual para o menu principal do Administrador."""
    await cb.answer()
    await _show_main_menu(cb, state)

# ─────────────────────── Utilizadores ───────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.USERS),
    F.data.in_(["users:search", "users:add"]),
)
async def users_menu_options(cb: CallbackQuery, state: FSMContext):
    """Trata das duas opções do submenu Utilizadores: Procurar / Adicionar."""
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

# ─────────────── Botão VOLTAR em ‘Procurar’ ou ‘Adicionar’ ───────────────
@router.callback_query(
    StateFilter((
        AdminMenuStates.USERS_SEARCH,
        AddUserStates,  # qualquer estado dentro do fluxo “Adicionar utilizador”
    )),
    F.data == "back",
)
async def users_suboption_back(cb: CallbackQuery, state: FSMContext):
    """Regressa de ‘Procurar’ ou ‘Adicionar’ ao submenu Utilizadores."""
    await cb.answer()
    await _show_users_menu(cb, state)

# ───────── Fluxo “Adicionar utilizador” – escolha do tipo ─────────
@router.callback_query(StateFilter(AddUserStates.CHOOSING_ROLE), F.data.startswith("role:"))
async def adduser_choose_role(cb: CallbackQuery, state: FSMContext):
    """
    Placeholder para criação de utilizador.

    Após escolher o tipo (Paciente, Cuidador, …) o utilizador mantém-se no
    submenu ‘Adicionar utilizador’, permitindo outra escolha ou sair com Voltar.
    """
    role = cb.data.split(":", 1)[1]
    await cb.answer(f"✅ {role.title()} seleccionado!", show_alert=False)

    await _replace_menu(
        cb, state,
        f"✅ *{role.title()}* seleccionado!\n"
        "🚧 Passos seguintes por implementar…\n\n"
        "*Escolha outro tipo ou volte:*",
        build_user_type_kbd(),
    )
    # Mantém-se em AddUserStates.CHOOSING_ROLE
