from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters.callback_data import CallbackData
from shared.dal import DAL

router = Router(name="regist_patient")

class RegistPatient(StatesGroup):
    waiting_name = State()
    waiting_surname = State()
    done = State()

@router.callback_query(F.data == "regist_patient")
async def cb_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("Qual é o teu primeiro nome?")
    await state.set_state(RegistPatient.waiting_name)

@router.message(RegistPatient.waiting_name)
async def get_name(msg: types.Message, state: FSMContext):
    await state.update_data(first_name=msg.text.strip())
    await msg.answer("E o teu apelido?")
    await state.set_state(RegistPatient.waiting_surname)

@router.message(RegistPatient.waiting_surname)
async def get_surname(msg: types.Message, state: FSMContext):
    data = await state.update_data(last_name=msg.text.strip())
    # Placeholder DB insert
    await msg.answer(f"🎉 {data['first_name']} {data['last_name']}, registo concluído! (demo)")
    await state.clear()
