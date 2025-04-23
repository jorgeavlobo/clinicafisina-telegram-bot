from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery
from bot.auth import auth_flow as flow
from bot.states.auth_states import AuthStates
from bot.database.connection import get_pool
from bot.database import queries as q

router = Router(name="auth")

@router.message(CommandStart())
async def start(message: Message, state):
    pool = await get_pool()
    user = await q.get_user_by_telegram_id(pool, message.from_user.id)

    if user:
        # já temos ligação → saltar FSM, mostrar menu base
        roles = await q.get_user_roles(pool, user["user_id"])
        await state.clear()
        await message.answer(
            f"👋 Olá, {user['first_name']}! O que pretende fazer hoje?")
        # TODO: show_menu(roles[0], message.chat.id)
    else:
        # não encontrado → prossegue onboarding normal
        await flow.start_onboarding(message, state)

@router.message(StateFilter(AuthStates.WAITING_CONTACT), F.contact)
async def contact_handler(message: Message, state):
    await flow.handle_contact(message, state)

@router.callback_query(StateFilter(AuthStates.CONFIRMING_LINK), F.data == "link_yes")
async def cb_confirm_yes(cb: CallbackQuery, state):
    await flow.confirm_link(cb, state)

@router.callback_query(StateFilter(AuthStates.CONFIRMING_LINK), F.data == "link_no")
async def cb_confirm_no(cb: CallbackQuery, state):
    await state.clear()
    await cb.message.edit_text("Operação cancelada.")
