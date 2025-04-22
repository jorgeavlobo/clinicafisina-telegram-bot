from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

router = Router(name="regist_caregiver")

class RegistCaregiver(StatesGroup):
    waiting_name = State()

@router.callback_query(F.data == "regist_caregiver")
async def cb_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("Como te chamas? (Cuidador)")
    await state.set_state(RegistCaregiver.waiting_name)

@router.message(RegistCaregiver.waiting_name)
async def done(msg: types.Message, state: FSMContext):
    await msg.answer(f"Obrigado {msg.text}! Registo de cuidador (demo).")
    await state.clear()
