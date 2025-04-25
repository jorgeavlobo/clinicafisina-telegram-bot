# bot/handlers/administrator_handlers.py
"""
Handlers do menu de Administrador

• Garante que só o *menu actualmente activo* responde aos cliques.
• Fecha o menu anterior sempre que um novo é aberto (evita clutter).
• Depois de uma opção-placeholder, remove o menu.
"""

from __future__ import annotations

from aiogram import Router, F, exceptions
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.filters.role_filter import RoleFilter
from bot.states.admin_menu_states import AdminMenuStates
from bot.menus.common import back_button

router = Router(name="administrator")
router.callback_query.filter(RoleFilter("administrator"))   # acesso reservado


# ────────────────────────── construtores de teclados ─────────────────────────
def _agenda_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("📆 Geral",               callback_data="agenda:geral")],
            [InlineKeyboardButton("🩺 Escolher Fisioterapeuta", callback_data="agenda:fisios")],
            [back_button()],
        ]
    )


def _users_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("🔍 Procurar", callback_data="users:search")],
            [InlineKeyboardButton("➕ Adicionar", callback_data="users:add")],
            [back_button()],
        ]
    )


# ───────────────────────── helpers  (menu activo / fechar) ───────────────────
async def _purge_last_menu(bot_msg_chat_id: tuple[int, int] | None) -> None:
    """
    Recebe (chat_id, msg_id) e tenta apagar a mensagem-menu anterior.
    Ignora erros se a mensagem já não existir.
    """
    if not bot_msg_chat_id:
        return
    chat_id, msg_id = bot_msg_chat_id
    from bot.main import bot  # evita ciclo
    try:
        await bot.delete_message(chat_id, msg_id)
    except exceptions.TelegramBadRequest:
        pass


async def _ensure_active_menu(cb: CallbackQuery, state: FSMContext) -> bool:
    """
    True  → o clique veio do menu activo
    False → menu antigo (mostra alert e ignora)
    """
    data = await state.get_data()
    if cb.message.message_id != data.get("menu_msg_id"):
        try:
            await cb.answer(
                "⚠️ Este menu já não está activo. Use /start para abrir um novo.",
                show_alert=True,
            )
        except exceptions.TelegramBadRequest:
            pass
        return False
    return True


async def _switch_submenu(
    cb: CallbackQuery,
    state: FSMContext,
    new_state: AdminMenuStates,
    text: str,
    kbd: InlineKeyboardMarkup,
) -> None:
    """
    Remove o submenu anterior (se existir) e envia o novo.
    Guarda o novo menu_msg_id para validações futuras.
    """
    data = await state.get_data()
    last_chat_msg: tuple[int, int] | None = None
    if "menu_chat_id" in data and "menu_msg_id" in data:
        last_chat_msg = (data["menu_chat_id"], data["menu_msg_id"])

    # apaga mensagem onde o botão foi clicado (se ainda existir),
    # bem como o submenu anterior guardado em FSM
    try:
        await cb.message.delete()
    except exceptions.TelegramBadRequest:
        pass
    await _purge_last_menu(last_chat_msg)

    # envia o novo submenu
    msg = await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")
    await state.set_state(new_state)
    await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)
    await cb.answer()


async def _close_menu(cb: CallbackQuery, state: FSMContext) -> None:
    """Apaga o menu actual e limpa as chaves menu_* do FSM."""
    try:
        await cb.message.delete()
    except exceptions.TelegramBadRequest:
        pass
    await state.update_data(menu_msg_id=None, menu_chat_id=None)


# ─────────────────────────── MENU PRINCIPAL ────────────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.MAIN),
    F.data.in_(["admin:agenda", "admin:users"]),
)
async def admin_main_nav(cb: CallbackQuery, state: FSMContext):
    if not await _ensure_active_menu(cb, state):
        return

    if cb.data == "admin:agenda":
        await _switch_submenu(
            cb,
            state,
            AdminMenuStates.AGENDA,
            "📅 *Agenda* — seleccione uma opção:",
            _agenda_kbd(),
        )
    else:  # admin:users
        await _switch_submenu(
            cb,
            state,
            AdminMenuStates.USERS,
            "👥 *Utilizadores* — seleccione uma opção:",
            _users_kbd(),
        )


# ───────────────────────────── AGENDA ──────────────────────────────────
@router.callback_query(StateFilter(AdminMenuStates.AGENDA) & F.data == "back")
async def agenda_back(cb: CallbackQuery, state: FSMContext):
    # volta ao menu principal de administrador
    from bot.menus.administrator_menu import build_menu
    await cb.message.edit_text("💻 *Menu:*", reply_markup=build_menu(), parse_mode="Markdown")
    await state.set_state(AdminMenuStates.MAIN)
    await cb.answer()


@router.callback_query(
    StateFilter(AdminMenuStates.AGENDA),
    F.data.in_(["agenda:geral", "agenda:fisios"]),
)
async def agenda_placeholders(cb: CallbackQuery, state: FSMContext):
    if not await _ensure_active_menu(cb, state):
        return

    if cb.data == "agenda:geral":
        await cb.answer("🚧 (placeholder) Agenda geral", show_alert=True)
    else:
        await cb.answer("🚧 (placeholder) Lista de fisioterapeutas", show_alert=True)

    await _close_menu(cb, state)


# ─────────────────────────── UTILIZADORES ──────────────────────────────
@router.callback_query(StateFilter(AdminMenuStates.USERS) & F.data == "back")
async def users_back(cb: CallbackQuery, state: FSMContext):
    from bot.menus.administrator_menu import build_menu
    await cb.message.edit_text("💻 *Menu:*", reply_markup=build_menu(), parse_mode="Markdown")
    await state.set_state(AdminMenuStates.MAIN)
    await cb.answer()


@router.callback_query(
    StateFilter(AdminMenuStates.USERS),
    F.data.in_(["users:search", "users:add"]),
)
async def users_placeholders(cb: CallbackQuery, state: FSMContext):
    if not await _ensure_active_menu(cb, state):
        return

    if cb.data == "users:search":
        await cb.answer("🚧 (placeholder) Pesquisa de utilizadores", show_alert=True)
    else:
        await cb.answer("🚧 (placeholder) Adicionar utilizador", show_alert=True)

    await _close_menu(cb, state)
