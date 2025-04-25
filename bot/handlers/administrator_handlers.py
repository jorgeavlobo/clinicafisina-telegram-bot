# bot/handlers/administrator_handlers.py
from aiogram import Router, F, exceptions
from aiogram.filters import StateFilter
from aiogram.types import (
    CallbackQuery, Message,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext

from bot.filters.role_filter import RoleFilter
from bot.states.admin_menu_states import AdminMenuStates
from bot.menus.common import back_button

router = Router(name="administrator")
router.message.filter(RoleFilter("administrator"))
router.callback_query.filter(RoleFilter("administrator"))

# ───────────────────────────── helpers ──────────────────────────────
def _agenda_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📆 Geral",               callback_data="agenda:geral")],
        [InlineKeyboardButton(text="🩺 Escolher Fisioterapeuta", callback_data="agenda:fisios")],
        [back_button()],
    ])

def _users_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Procurar", callback_data="users:search")],
        [InlineKeyboardButton(text="➕ Adicionar", callback_data="users:add")],
        [back_button()],
    ])

async def _delete_prev(bot, state: FSMContext) -> None:
    """Apaga, se ainda existir, a última mensagem-menu guardada no FSM."""
    data = await state.get_data()
    msg_id  = data.get("menu_msg_id")
    chat_id = data.get("menu_chat_id")
    if msg_id and chat_id:
        try:
            await bot.delete_message(chat_id, msg_id)
        except exceptions.TelegramBadRequest:
            pass  # já não existe ou demasiado antiga

async def _register_menu(state: FSMContext, msg: Message) -> None:
    """Guarda o id da nova mensagem-menu para poder limpá-la depois."""
    await state.update_data(menu_msg_id=msg.message_id,
                            menu_chat_id=msg.chat.id)

# ─────────────────────────── MENU PRINCIPAL ─────────────────────────
@router.callback_query(StateFilter(AdminMenuStates.MAIN), F.data == "admin:agenda")
async def admin_to_agenda(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    await _delete_prev(cb.bot, state)
    await state.set_state(AdminMenuStates.AGENDA)

    new_msg = await cb.message.answer(
        "📅 *Agenda* — seleccione uma opção:",
        reply_markup=_agenda_kbd(),
        parse_mode="Markdown",
    )
    await _register_menu(state, new_msg)

@router.callback_query(StateFilter(AdminMenuStates.MAIN), F.data == "admin:users")
async def admin_to_users(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    await _delete_prev(cb.bot, state)
    await state.set_state(AdminMenuStates.USERS)

    new_msg = await cb.message.answer(
        "👥 *Utilizadores* — seleccione uma opção:",
        reply_markup=_users_kbd(),
        parse_mode="Markdown",
    )
    await _register_menu(state, new_msg)

# ─────────────────────────────── A G E N D A ────────────────────────
@router.callback_query(StateFilter(AdminMenuStates.AGENDA), F.data == "agenda:geral")
async def agenda_geral(cb: CallbackQuery):
    await cb.answer("🚧 Placeholder: Agenda geral (a implementar)", show_alert=True)
    await cb.message.delete()

@router.callback_query(StateFilter(AdminMenuStates.AGENDA), F.data == "agenda:fisios")
async def agenda_fisio(cb: CallbackQuery):
    await cb.answer("🚧 Placeholder: lista de fisioterapeutas (a implementar)", show_alert=True)
    await cb.message.delete()

@router.callback_query(StateFilter(AdminMenuStates.AGENDA), F.data == "back")
async def agenda_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await cb.message.delete()
    await state.set_state(AdminMenuStates.MAIN)

    from bot.menus.administrator_menu import build_menu
    new = await cb.message.answer(
        "💻 *Menu:*",
        parse_mode="Markdown",
        reply_markup=build_menu(),
    )
    await _register_menu(state, new)

# ────────────────────────── U T I L I Z A D O R E S ──────────────────
@router.callback_query(StateFilter(AdminMenuStates.USERS), F.data == "users:search")
async def users_search(cb: CallbackQuery):
    await cb.answer("🚧 Placeholder: pesquisa de utilizadores", show_alert=True)
    await cb.message.delete()

@router.callback_query(StateFilter(AdminMenuStates.USERS), F.data == "users:add")
async def users_add(cb: CallbackQuery):
    await cb.answer("🚧 Placeholder: adicionar utilizador", show_alert=True)
    await cb.message.delete()

@router.callback_query(StateFilter(AdminMenuStates.USERS), F.data == "back")
async def users_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await cb.message.delete()
    await state.set_state(AdminMenuStates.MAIN)

    from bot.menus.administrator_menu import build_menu
    new = await cb.message.answer(
        "💻 *Menu:*",
        parse_mode="Markdown",
        reply_markup=build_menu(),
    )
    await _register_menu(state, new)
