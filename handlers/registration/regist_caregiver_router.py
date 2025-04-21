from aiogram import Router, types
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import ReplyKeyboardMarkup, KeyboardButton
from logging import getLogger
from dal.dal import (
    create_caregiver_user,
    attach_phone_to_user,
    add_role_to_user,
    find_patient_by_phone,
    link_caregiver_to_patient
)

logger = getLogger(__name__)
router = Router(name="registration_caregiver")

# ---------- FSM ----------
class RegistCaregiver(StatesGroup):
    ask_first_name   = State()
    ask_last_name    = State()
    ask_phone_self   = State()
    ask_patient_phone= State()

# ---------- Keyboards ----------
def kb_share_contact(cancel_label="⬅️ Cancelar") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📲 Partilhar nº telemóvel", request_contact=True)],
                  [KeyboardButton(text=cancel_label)]],
        resize_keyboard=True
    )

# ---------- Entrypoint ----------
@router.message(Command("regist_caregiver"))
async def start_caregiver_reg(msg: types.Message, state: FSMContext) -> None:
    await msg.answer("👥 Qual é o <b>primeiro nome</b> do cuidador?", parse_mode="HTML")
    await state.set_state(RegistCaregiver.ask_first_name)

# --- Nome próprio ---
@router.message(RegistCaregiver.ask_first_name)
async def caregiver_first(msg: types.Message, state: FSMContext):
    await state.update_data(first_name=msg.text.strip())
    await msg.answer("✅ Agora o <b>apelido</b>:", parse_mode="HTML")
    await state.set_state(RegistCaregiver.ask_last_name)

# --- Apelido ---
@router.message(RegistCaregiver.ask_last_name)
async def caregiver_last(msg: types.Message, state: FSMContext):
    await state.update_data(last_name=msg.text.strip())
    await msg.answer(
        "Partilhe <b>o seu</b> número de telemóvel:",
        parse_mode="HTML",
        reply_markup=kb_share_contact()
    )
    await state.set_state(RegistCaregiver.ask_phone_self)

# --- Telefone do cuidador ---
@router.message(RegistCaregiver.ask_phone_self, content_types=types.ContentType.CONTACT)
async def caregiver_phone(msg: types.Message, state: FSMContext):
    await state.update_data(caregiver_phone=msg.contact.phone_number)
    await msg.answer(
        "✔️ Agora partilhe o <b>número do paciente</b> que pretende associar:",
        parse_mode="HTML",
        reply_markup=kb_share_contact(cancel_label="❌ Cancelar")
    )
    await state.set_state(RegistCaregiver.ask_patient_phone)

# --- Telefone do paciente ---
@router.message(RegistCaregiver.ask_patient_phone, content_types=types.ContentType.CONTACT)
async def patient_phone(msg: types.Message, state: FSMContext):
    patient_phone = msg.contact.phone_number
    patient = await find_patient_by_phone(patient_phone)

    if not patient:
        await msg.answer("⚠️ Não encontramos paciente com esse número. Tente novamente ou contacte a clínica.")
        return

    data = await state.get_data()
    user_id = await create_caregiver_user(
        first_name=data["first_name"],
        last_name=data["last_name"],
        telegram_user_id=msg.from_user.id
    )
    await attach_phone_to_user(user_id, data["caregiver_phone"], primary=True)
    await add_role_to_user(user_id, "caregiver")
    await link_caregiver_to_patient(user_id, patient["user_id"])

    await state.clear()
    await msg.answer(
        "🎉 Cuidador registado e ligado ao paciente com sucesso!",
        reply_markup=types.ReplyKeyboardRemove()
    )

# --- Cancelar ---
@router.message(
    RegistCaregiver.ask_patient_phone,
    RegistCaregiver.ask_phone_self,
    RegistCaregiver.ask_last_name,
    RegistCaregiver.ask_first_name,
    Text(startswith="⬅️") | Text(startswith="❌")
)
async def cancel_reg(msg: types.Message, state: FSMContext):
    await state.clear()
    await msg.answer("Operação cancelada.", reply_markup=types.ReplyKeyboardRemove())
