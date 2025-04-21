from aiogram import Router, types
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import ReplyKeyboardMarkup, KeyboardButton
from logging import getLogger
from dal.dal import (
    create_patient_user,
    attach_phone_to_user,
    add_role_to_user
)

logger = getLogger(__name__)
router = Router(name="registration_patient")

# ---------- FSM ----------
class RegistPatient(StatesGroup):
    waiting_first_name   = State()
    waiting_last_name    = State()
    waiting_phone_share  = State()
    confirming           = State()

# ---------- Keyboards ----------
def kb_share_contact() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📲 Partilhar nº telemóvel", request_contact=True)],
                  [KeyboardButton(text="⬅️ Cancelar")]],
        resize_keyboard=True
    )

# ---------- Entrypoint ----------
@router.message(Command("regist_patient"))
async def start_patient_reg(msg: types.Message, state: FSMContext) -> None:
    await msg.answer("📝 Qual é o <b>primeiro nome</b> do paciente?", parse_mode="HTML")
    await state.set_state(RegistPatient.waiting_first_name)

# --------- Step 1 ---------
@router.message(RegistPatient.waiting_first_name)
async def get_first_name(msg: types.Message, state: FSMContext) -> None:
    await state.update_data(first_name=msg.text.strip())
    await msg.answer("✅ Recebido. Agora indique o <b>apelido</b>:", parse_mode="HTML")
    await state.set_state(RegistPatient.waiting_last_name)

# --------- Step 2 ---------
@router.message(RegistPatient.waiting_last_name)
async def get_last_name(msg: types.Message, state: FSMContext) -> None:
    await state.update_data(last_name=msg.text.strip())
    await msg.answer(
        "Quase pronto! Partilhe o número de telemóvel para concluir:",
        reply_markup=kb_share_contact()
    )
    await state.set_state(RegistPatient.waiting_phone_share)

# --------- Step 3 (share contact) ---------
@router.message(RegistPatient.waiting_phone_share, content_types=types.ContentType.CONTACT)
async def receive_contact(msg: types.Message, state: FSMContext) -> None:
    phone = msg.contact.phone_number
    data = await state.get_data()
    first = data["first_name"]
    last  = data["last_name"]

    # Criar utilizador + role
    user_id = await create_patient_user(first, last, msg.from_user.id)
    await attach_phone_to_user(user_id, phone, primary=True)
    await add_role_to_user(user_id, role_name="patient")

    logger.info(f"Novo paciente registado #{user_id} ({first} {last})", extra={"telegram_user_id": msg.from_user.id})

    await state.clear()
    await msg.answer(
        "🎉 Registo concluído com sucesso! Já pode usar o menu de paciente.",
        reply_markup=types.ReplyKeyboardRemove()
    )
    # Aqui poderíamos emitir evento para carregar menu de paciente

# ----- Cancel / back -----
@router.message(RegistPatient.waiting_phone_share, Text("⬅️ Cancelar"))
@router.message(RegistPatient.waiting_last_name, Text("⬅️ Cancelar"))
@router.message(RegistPatient.waiting_first_name, Text("⬅️ Cancelar"))
async def cancel_flow(msg: types.Message, state: FSMContext) -> None:
    await state.clear()
    await msg.answer("Operação cancelada.", reply_markup=types.ReplyKeyboardRemove())
