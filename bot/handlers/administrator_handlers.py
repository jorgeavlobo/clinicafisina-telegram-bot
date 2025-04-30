# bot/handlers/administrator_handlers.py
"""
Administrator menu handlers (Aiogram 3.20).

— Garante navegação completa do menu de administrador.
— Fluxo “Adicionar Utilizador” incorporado na FSM `AddUserFlow`.
— Botões "Voltar" e fecho de menus totalmente funcionais.
"""

from __future__ import annotations

from aiogram import Router, F, exceptions, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.filters.role_filter      import RoleFilter
from bot.states.admin_menu_states import AdminMenuStates
from bot.states.add_user_flow     import AddUserFlow  # Fluxo completo de adição
from bot.menus.common             import (
    back_button,
    start_menu_timeout,
    cancel_back_kbd,
)
from bot.menus.administrator_menu import (
    build_menu as _main_menu_kbd,
    build_user_type_kbd,
)

router = Router(name="administrator")
router.callback_query.filter(RoleFilter("administrator"))

# ────────────────────────── construtores de sub‑menus ─────────────────────────

def _agenda_kbd() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="📆 Geral",         callback_data="agenda:geral")],
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

# ───────────────────────────── utilitários UI ──────────────────────────────

async def _replace_menu(
    cb: types.CallbackQuery,
    state: FSMContext,
    text: str,
    kbd: types.InlineKeyboardMarkup,
) -> None:
    """Edita (ou cria) a mensagem‑menu e reinicia o timeout."""

    # Regista a mensagem (antes da edição) como menu activo
    await state.update_data(menu_msg_id=cb.message.message_id,
                            menu_chat_id=cb.message.chat.id)
    try:
        await cb.message.edit_text(text, reply_markup=kbd, parse_mode="Markdown")
        msg = cb.message
    except exceptions.TelegramBadRequest:
        # Se a mensagem já não pode ser editada, cria nova
        await cb.message.delete()
        msg = await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")
        await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)

    await start_menu_timeout(cb.bot, msg, state)


async def _close_menu(cb: types.CallbackQuery, state: FSMContext, confirmation: str) -> None:
    """Remove o teclado inline, mostra confirmação e limpa registo no FSM."""
    try:
        await cb.message.edit_text(confirmation, parse_mode="Markdown", reply_markup=None)
    except exceptions.TelegramBadRequest:
        pass
    await state.update_data(menu_msg_id=None, menu_chat_id=None)


# ───────────────────── wrappers de navegação ─────────────────────

async def _main(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminMenuStates.MAIN)
    await _replace_menu(cb, state, "💻 *Menu:*", _main_menu_kbd())


async def _agenda(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminMenuStates.AGENDA)
    await _replace_menu(cb, state, "📅 *Agenda* — seleccione:", _agenda_kbd())


async def _users(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminMenuStates.USERS)
    await _replace_menu(cb, state, "👥 *Utilizadores* — seleccione:", _users_kbd())


async def _add_user(cb: types.CallbackQuery, state: FSMContext):
    """Entra no fluxo ‘Adicionar utilizador’ — passo CHOOSING_ROLE."""

    await state.set_state(AddUserFlow.CHOOSING_ROLE)
    await _replace_menu(
        cb,
        state,
        "👤 *Adicionar utilizador* — escolha o tipo:",
        build_user_type_kbd(),
    )


# ─────────────────────────── MENU PRINCIPAL ────────────────────────────

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
    await cb.answer("🚧 Mensagens – em desenvolvimento", show_alert=True)
    await _close_menu(cb, state, "💬 *Mensagens* – em desenvolvimento")
    await state.set_state(AdminMenuStates.MAIN)


# ────────────────────────────── Agenda ───────────────────────────────

@router.callback_query(AdminMenuStates.AGENDA, F.data.in_(["agenda:geral", "agenda:fisios"]))
async def agenda_placeholder(cb: types.CallbackQuery, state: FSMContext):
    destino = "Geral" if cb.data.endswith("geral") else "Fisioterapeuta"
    await cb.answer(f"🚧 Agenda {destino} – em desenvolvimento", show_alert=True)
    await _close_menu(cb, state, f"📅 *Agenda {destino}* – em desenvolvimento")
    await state.set_state(AdminMenuStates.MAIN)


@router.callback_query(AdminMenuStates.AGENDA, F.data == "back")
async def agenda_back(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await _main(cb, state)


# ─────────────────────────── Utilizadores ────────────────────────────

@router.callback_query(AdminMenuStates.USERS, F.data == "users:search")
async def users_search(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer("🚧 Pesquisar utilizador – em desenvolvimento", show_alert=True)
    await _close_menu(cb, state, "🔍 *Pesquisar utilizador* – em desenvolvimento")
    await state.set_state(AdminMenuStates.USERS)


@router.callback_query(AdminMenuStates.USERS, F.data == "users:add")
async def users_add(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await _add_user(cb, state)


@router.callback_query(AdminMenuStates.USERS, F.data == "back")
async def users_back(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await _main(cb, state)


# ─────────── “Escolher tipo de utilizador” (AddUserFlow) ────────────

@router.callback_query(AddUserFlow.CHOOSING_ROLE, F.data.startswith("role:"))
async def adduser_choose_role(cb: types.CallbackQuery, state: FSMContext):
    role = cb.data.split(":", 1)[1]
    await cb.answer(f"✅ {role.title()} seleccionado!", show_alert=False)
    await _close_menu(cb, state, f"✅ *{role.title()}* seleccionado! Vamos pedir os dados…")
    await state.update_data(role=role)
    await cb.message.answer("Primeiro(s) nome(s):", reply_markup=cancel_back_kbd())
    await state.set_state(AddUserFlow.FIRST_NAME)


@router.callback_query(AddUserFlow.CHOOSING_ROLE, F.data == "back")
async def adduser_choose_role_back(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await _users(cb, state)
