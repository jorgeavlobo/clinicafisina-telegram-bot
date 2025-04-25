from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.filters.role_filter import RoleFilter
from bot.states.admin_menu_states import AdminMenuStates
from bot.menus.common import back_button
from bot.menus.administrator_menu import build_menu

router = Router(name="administrator")
router.callback_query.filter(RoleFilter("administrator"))

# ───────────────────────── menu principal ─────────────────────────
@router.callback_query(StateFilter(AdminMenuStates.MAIN), F.data == "admin:agenda")
async def admin_to_agenda(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(AdminMenuStates.AGENDA)
    await cb.message.edit_text(
        "📅 *Agenda* — seleccione uma opção:",
        parse_mode="Markdown",
        reply_markup=_agenda_kbd(),
    )

@router.callback_query(StateFilter(AdminMenuStates.MAIN), F.data == "admin:users")
async def admin_to_users(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(AdminMenuStates.USERS)
    await cb.message.edit_text(
        "👥 *Utilizadores* — seleccione uma opção:",
        parse_mode="Markdown",
        reply_markup=_users_kbd(),
    )

# ───────────────────────── sub-menus ─────────────────────────
def _agenda_kbd():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("📆 Geral",   callback_data="agenda:geral")],
        [InlineKeyboardButton("🩺 Por Fisioterapeuta", callback_data="agenda:fisios")],
        [back_button()],
    ])

@router.callback_query(StateFilter(AdminMenuStates.AGENDA), F.data.startswith("agenda:"))
async def agenda_actions(cb: CallbackQuery, state: FSMContext):
    await cb.answer("🚧 Placeholder – lógica por implementar", show_alert=True)
    # fecha o menu depois de acção final
    await state.set_state(AdminMenuStates.MAIN)
    await cb.message.delete()

def _users_kbd():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🔍 Procurar", callback_data="users:search")],
        [InlineKeyboardButton("➕ Adicionar", callback_data="users:add")],
        [back_button()],
    ])

@router.callback_query(StateFilter(AdminMenuStates.USERS), F.data.startswith("users:"))
async def users_actions(cb: CallbackQuery, state: FSMContext):
    await cb.answer("🚧 Placeholder – lógica por implementar", show_alert=True)
    await state.set_state(AdminMenuStates.MAIN)
    await cb.message.delete()

# ───────────────────────── voltar (back) ─────────────────────────
@router.callback_query(F.data == "back")
async def go_back(cb: CallbackQuery, state: FSMContext):
    """
    Qualquer submenu que envie 'back' regressa ao menu principal.
    O teclado é reposto (edit_text) em vez de criar nova mensagem.
    """
    await cb.answer()
    await state.set_state(AdminMenuStates.MAIN)
    await cb.message.edit_text("💻 *Menu:*", parse_mode="Markdown",
                               reply_markup=build_menu())
