# bot/handlers/auth_handlers.py
from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.auth import auth_flow as flow
from bot.states.auth_states import AuthStates
from bot.database.connection import get_pool
from bot.database import queries as q
from bot.menus import show_menu            # utilitário de menus

router = Router(name="auth")

# ───────────────────────────── /start ─────────────────────────────
@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    pool = await get_pool()
    user = await q.get_user_by_telegram_id(pool, message.from_user.id)

    if user:
        # já existe ligação → mostrar menu adequado
        roles = await q.get_user_roles(pool, user["user_id"])
        await state.clear()                                # reset FSM
        await show_menu(message.bot, message.chat.id, state, roles)
    else:
        # não encontrado → iniciar onboarding
        await flow.start_onboarding(message, state)

# ─────────────────────────── onboarding FSM ───────────────────────────
@router.message(StateFilter(AuthStates.WAITING_CONTACT), F.contact)
async def contact_handler(message: Message, state: FSMContext):
    await flow.handle_contact(message, state)

@router.callback_query(StateFilter(AuthStates.CONFIRMING_LINK), F.data == "link_yes")
async def cb_confirm_yes(cb: CallbackQuery, state: FSMContext):
    await flow.confirm_link(cb, state)

@router.callback_query(StateFilter(AuthStates.CONFIRMING_LINK), F.data == "link_no")
async def cb_confirm_no(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("Operação cancelada.")
