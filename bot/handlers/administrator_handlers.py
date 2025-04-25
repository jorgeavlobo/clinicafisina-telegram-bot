# bot/handlers/administrator_handlers.py
"""
Handlers do menu de Administrador.

• Garante que só o *menu actualmente activo* responde aos cliques.
• Depois de uma opção-placeholder, remove o menu para evitar clutter.
"""

from aiogram import Router, F, exceptions
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.filters.role_filter import RoleFilter
from bot.states.admin_menu_states import AdminMenuStates
from bot.menus.common import back_button

router = Router(name="administrator")
router.callback_query.filter(RoleFilter("administrator"))   # acesso restrito a admins


# ───────────────────────── helpers de teclados ─────────────────────────
def _agenda_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📆 Geral", callback_data="agenda:geral")],
            [
                InlineKeyboardButton(
                    text="🩺 Escolher Fisioterapeuta",
                    callback_data="agenda:fisios",
                )
            ],
            [back_button()],
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


# ───────────────────── utilidades: menu activo & fechar ─────────────────────
async def _ensure_active_menu(cb: CallbackQuery, state: FSMContext) -> bool:
    """
    Devolve True se o menu onde o clique ocorreu é o último menu
    mostrado pela bot; caso contrário mostra alerta e ignora.
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


async def _close_menu(cb: CallbackQuery, state: FSMContext) -> None:
    """Apaga a mensagem-menu actual e limpa as chaves menu_* do FSM."""
    try:
        await cb.message.delete()
    except exceptions.TelegramBadRequest:
        pass
    await state.update_data(menu_msg_id=None, menu_chat_id=None)


# ─────────────────────── MENU PRINCIPAL (Agenda / Utilizadores) ──────────────
@router.callback_query(
    StateFilter(AdminMenuStates.MAIN),
    F.data.in_(["admin:agenda", "admin:users"]),
)
async def admin_main_nav(cb: CallbackQuery, state: FSMContext):
    if not await _ensure_active_menu(cb, state):
        return

    await cb.answer()

    if cb.data == "admin:agenda":
        await state.set_state(AdminMenuStates.AGENDA)
        await cb.message.edit_text(
            "📅 *Agenda* — seleccione uma opção:",
            reply_markup=_agenda_kbd(),
            parse_mode="Markdown",
        )
    else:  # admin:users
        await state.set_state(AdminMenuStates.USERS)
        await cb.message.edit_text(
            "👥 *Utilizadores* — seleccione uma opção:",
            reply_markup=_users_kbd(),
            parse_mode="Markdown",
        )


# ──────────────────────────── AGENDA ─────────────────────────────────────────
@router.callback_query(StateFilter(AdminMenuStates.AGENDA))
async def agenda_router(cb: CallbackQuery, state: FSMContext):
    if not await _ensure_active_menu(cb, state):
        return

    action = cb.data

    if action == "back":
        from bot.menus.administrator_menu import build_menu

        await state.set_state(AdminMenuStates.MAIN)
        await cb.message.edit_text(
            "💻 *Menu:*", reply_markup=build_menu(), parse_mode="Markdown"
        )
        await cb.answer()
        return

    # Placeholders ------------------------------------------------------------
    if action == "agenda:geral":
        await cb.answer("🚧 (placeholder) Agenda geral", show_alert=True)
    elif action == "agenda:fisios":
        await cb.answer("🚧 (placeholder) Lista de fisioterapeutas", show_alert=True)
    else:
        await cb.answer("❗ Opção não reconhecida", show_alert=True)
        return

    # Após placeholder, fecha-se o menu
    await _close_menu(cb, state)


# ─────────────────────────── UTILIZADORES ────────────────────────────────────
@router.callback_query(StateFilter(AdminMenuStates.USERS))
async def users_router(cb: CallbackQuery, state: FSMContext):
    if not await _ensure_active_menu(cb, state):
        return

    action = cb.data

    if action == "back":
        from bot.menus.administrator_menu import build_menu

        await state.set_state(AdminMenuStates.MAIN)
        await cb.message.edit_text(
            "💻 *Menu:*", reply_markup=build_menu(), parse_mode="Markdown"
        )
        await cb.answer()
        return

    # Placeholders ------------------------------------------------------------
    if action == "users:search":
        await cb.answer("🚧 (placeholder) Pesquisa de utilizadores", show_alert=True)
    elif action == "users:add":
        await cb.answer("🚧 (placeholder) Adicionar utilizador", show_alert=True)
    else:
        await cb.answer("❗ Opção não reconhecida", show_alert=True)
        return

    # Após placeholder, fecha-se o menu
    await _close_menu(cb, state)
