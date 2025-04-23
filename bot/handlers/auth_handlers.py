from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery, Contact
from bot.auth import auth_flow as flow
from bot.states.auth_states import AuthStates

router = Router(name="auth")

@router.message(CommandStart())
async def start(message: Message, state):
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
