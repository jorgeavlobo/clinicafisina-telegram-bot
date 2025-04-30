# bot/handlers/administrator_handlers.py
"""
Administrator menu handlers (Aiogram 3.20).

• Todos os botões **Voltar** mantêm-se operacionais.
• Após a escolha de qualquer opção *placeholder* (Pesquisar utilizador, Agenda → Geral/Fisioterapeuta, Mensagens),
  o menu é imediatamente fechado (keyboard removida) e o utilizador recebe um alerta popup.
• Mantém-se compatível com o ActiveMenuMiddleware, actualizando sempre o menu activo no FSM
  **antes** de editar mensagens.
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

# ─────────────────────── teclados helper ────────────────────────
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

# ───────────────────────── utilitários UI ─────────────────────────
async def _replace_menu(
    cb:    CallbackQuery,
    state: FSMContext,
    text:  str,
    kbd:   InlineKeyboardMarkup,
) -> None:
    """
    Edita (ou cria) a mensagem-menu e reinicia o timeout.

    ⚠️ Regista o menu activo **antes** da edição, prevenindo que o
    ActiveMenuMiddleware descarte callbacks subsequentes.
    """
    await state.update_data(menu_msg_id=cb.message.message_id,
                            menu_chat_id=cb.message.chat.id)

    try:
        await cb.message.edit_text(text, reply_markup=kbd, parse_mode="Markdown")
        msg = cb.message
    except exceptions.TelegramBadRequest:
        await cb.message.delete()
        msg = await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")
        await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)

    start_menu_timeout(cb.bot, msg, state)

async def _close_menu(cb: CallbackQuery, state: FSMContext, confirmation: str) -> None:
    """Remove o teclado inline, mostra confirmação e limpa registo no FSM."""
    try:
        await cb.message.edit_text(confirmation, parse_mode="Markdown", reply_markup=None)
    except exceptions.TelegramBadRequest:
        pass
    await state.update_data(menu_msg_id=None, menu_chat_id=None)

# ─────────────────── wrappers de navegação ────────────────────
async def _main(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminMenuStates.MAIN)
    await _replace_menu(cb, state, "💻 *Menu:*", _main_menu_kbd())

async def _agenda(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminMenuStates.AGENDA)
    await _replace_menu(cb, state, "📅 *Agenda* — seleccione:", _agenda_kbd())

async def _users(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminMenuStates.USERS)
    await _replace_menu(cb, state, "👥 *Utilizadores* — seleccione:", _users_kbd())

async def _add_user(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AddUserStates.CHOOSING_ROLE)
    await _replace_menu(
        cb, state,
        "👤 *Adicionar utilizador* — escolha o tipo:",
        build_user_type_kbd(),
    )

# ──────────────────────── MENU PRINCIPAL ────────────────────────
@router.callback_query(AdminMenuStates.MAIN, F.data == "admin:agenda")
async def open_agenda(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _agenda(cb, state)

@router.callback_query(AdminMenuStates.MAIN, F.data == "admin:users")
async def open_users(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _users(cb, state)

@router.callback_query(AdminMenuStates.MAIN, F.data == "admin:messages")
async def open_messages(cb: CallbackQuery, state: FSMContext):
    await cb.answer("🚧 Mensagens – em desenvolvimento", show_alert=True)
    await _close_menu(cb, state, "💬 *Mensagens* – em desenvolvimento")
    await state.set_state(AdminMenuStates.MAIN)

# ─────────────────────────── Agenda ────────────────────────────
@router.callback_query(AdminMenuStates.AGENDA, F.data.in_(["agenda:geral", "agenda:fisios"]))
async def agenda_placeholder(cb: CallbackQuery, state: FSMContext):
    destino = "Geral" if cb.data.endswith("geral") else "Fisioterapeuta"
    await cb.answer(f"🚧 Agenda {destino} – em desenvolvimento", show_alert=True)
    await _close_menu(cb, state, f"📅 *Agenda {destino}* – em desenvolvimento")
    await state.set_state(AdminMenuStates.MAIN)

@router.callback_query(AdminMenuStates.AGENDA, F.data == "back")
async def agenda_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _main(cb, state)

# ─────────────────────── Utilizadores ────────────────────────
@router.callback_query(AdminMenuStates.USERS, F.data == "users:search")
async def users_search(cb: CallbackQuery, state: FSMContext):
    await cb.answer("🚧 Pesquisar utilizador – em desenvolvimento", show_alert=True)
    await _close_menu(cb, state, "🔍 *Pesquisar utilizador* – em desenvolvimento")
    await state.set_state(AdminMenuStates.USERS)

@router.callback_query(AdminMenuStates.USERS, F.data == "users:add")
async def users_add(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _add_user(cb, state)

@router.callback_query(AdminMenuStates.USERS, F.data == "back")
async def users_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _main(cb, state)

# ─────────────── “Adicionar utilizador” ───────────────
@router.callback_query(AddUserStates.CHOOSING_ROLE, F.data.startswith("role:"))
async def adduser_choose_role(cb: CallbackQuery, state: FSMContext):
    role = cb.data.split(":", 1)[1]
    await cb.answer(f"✅ {role.title()} seleccionado!", show_alert=False)

    # Fecha o menu
    await _close_menu(
        cb, state,
        f"✅ *{role.title()}* seleccionado!\n"
        "🚧 Passos seguintes por implementar…",
    )
    await state.set_state(AdminMenuStates.USERS)

@router.callback_query(AddUserStates.CHOOSING_ROLE, F.data == "back")
async def adduser_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _users(cb, state)
