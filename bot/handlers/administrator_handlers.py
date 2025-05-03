# bot/handlers/administrator_handlers.py
"""
Administrator menu handlers (Aiogram 3.20).

– Navegação completa do menu de administrador
– Fluxo “Adicionar Utilizador” incorporado na FSM `AddUserFlow`
– Botões «Voltar» e timeout/fecho de menus totalmente funcionais
"""

from __future__ import annotations

from contextlib import suppress

from aiogram import Router, F, exceptions, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.states.admin_menu_states import AdminMenuStates
from bot.states.add_user_flow     import AddUserFlow      # fluxo de adição
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
# 👉 NÃO há mais RoleFilter; usamos apenas o estado base AdminMenuStates.MAIN
#     (que é configurado assim que o perfil «administrator» é activado)

# ───────────────────────── construtores de sub-menus ─────────────────────────

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

# ─────────────────────────── utilitários UI ────────────────────────────

async def _replace_menu(
    cb: types.CallbackQuery,
    state: FSMContext,
    text: str,
    kbd: types.InlineKeyboardMarkup,
) -> None:
    """Edita (ou cria) a mensagem-menu e reinicia o timeout."""
    # Obtém os dados atuais do estado
    data = await state.get_data()
    menu_msg_id = data.get("menu_msg_id")
    menu_chat_id = data.get("menu_chat_id")

    print(f"Tentando editar mensagem: ID={menu_msg_id}, Chat={menu_chat_id}")

    if menu_msg_id and menu_chat_id:
        try:
            # Tenta editar a mensagem existente
            await cb.bot.edit_message_text(
                chat_id=menu_chat_id,
                message_id=menu_msg_id,
                text=text,
                reply_markup=kbd,
                parse_mode="Markdown"
            )
            print(f"Mensagem {menu_msg_id} editada com sucesso no chat {menu_chat_id}")
            msg = cb.message
        except exceptions.TelegramBadRequest as e:
            print(f"Falha ao editar mensagem {menu_msg_id}: {e}")
            # Deleta a mensagem antiga, se possível
            try:
                await cb.bot.delete_message(chat_id=menu_chat_id, message_id=menu_msg_id)
                print(f"Mensagem {menu_msg_id} deletada")
            except exceptions.TelegramBadRequest:
                print(f"Não foi possível deletar mensagem {menu_msg_id}")
            # Envia uma nova mensagem
            msg = await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")
            await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)
            print(f"Nova mensagem enviada: ID={msg.message_id}, Chat={msg.chat.id}")
    else:
        # Se não houver mensagem anterior, envia uma nova
        msg = await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")
        await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)
        print(f"Menu inicial enviado: ID={msg.message_id}, Chat={msg.chat.id}")

    start_menu_timeout(cb.bot, msg, state)


async def _close_menu(cb: types.CallbackQuery, state: FSMContext, confirmation: str) -> None:
    """Remove o teclado inline e mostra confirmação."""
    with suppress(exceptions.TelegramBadRequest):
        await cb.message.edit_text(confirmation, parse_mode="Markdown", reply_markup=None)
    await state.update_data(menu_msg_id=None, menu_chat_id=None)

# ─────────────────── wrappers de navegação ───────────────────

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

# ────────────────────────────── Agenda ────────────────────────────────

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

# ─── “Escolher tipo de utilizador” (AddUserFlow) ───

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
