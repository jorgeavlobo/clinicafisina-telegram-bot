"""FSM router for caregiver registration flow."""

from aiogram import Router, types
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from handlers.common.keyboards import visitor_main_kb
from logging import getLogger

logger = getLogger(__name__)
router = Router(name="registration_caregiver")

# FSM state definitions
class RegistCaregiver(StatesGroup):
    waiting_first_name = State()
    waiting_last_name = State()
    waiting_email = State()
    waiting_phone_self = State()
    waiting_patient_phone = State()
    confirming = State()

# Reply keyboard generators
def kb_back_cancel() -> types.ReplyKeyboardMarkup:
    """Keyboard with 'Voltar' and 'Cancelar' buttons."""
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="⬅️ Voltar"), types.KeyboardButton(text="❌ Cancelar")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def kb_skip_email() -> types.ReplyKeyboardMarkup:
    """Keyboard with 'Saltar email', 'Voltar' and 'Cancelar' buttons for email step."""
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="⏭️ Saltar email")],
            [types.KeyboardButton(text="⬅️ Voltar"), types.KeyboardButton(text="❌ Cancelar")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def kb_share_phone() -> types.ReplyKeyboardMarkup:
    """Keyboard prompting to share phone contact, with 'Voltar' and 'Cancelar'."""
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📲 Partilhar nº de telemóvel", request_contact=True)],
            [types.KeyboardButton(text="⬅️ Voltar"), types.KeyboardButton(text="❌ Cancelar")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

# Entry point: Start caregiver registration
@router.message(Command("regist_caregiver"))
async def cmd_regist_caregiver(message: types.Message, state: FSMContext) -> None:
    """Starts the caregiver registration FSM flow."""
    await state.clear()
    logger.info(f"Utilizador {message.from_user.id} iniciou registo como cuidador", extra={"telegram_user_id": message.from_user.id})
    # Ask for caregiver's first name
    await message.answer(
        "👥 Qual é o <b>primeiro nome</b> do cuidador?",
        parse_mode="HTML",
        reply_markup=kb_back_cancel()
    )
    await state.set_state(RegistCaregiver.waiting_first_name)

# Step 1: First name
@router.message(RegistCaregiver.waiting_first_name, ~(Text("⬅️ Voltar") | Text("❌ Cancelar") | Text(startswith="⏭️")))
async def caregiver_first_name(message: types.Message, state: FSMContext) -> None:
    """Handles the caregiver's first name input."""
    first = message.text.strip()
    if not first:
        await message.answer("❗ Por favor, indique um nome válido.")
        return
    await state.update_data(first_name=first)
    logger.info(f"Primeiro nome do cuidador: {first}", extra={"telegram_user_id": message.from_user.id})
    # Ask for last name
    await message.answer(
        "✅ Recebido. Agora indique o <b>apelido</b> do cuidador:",
        parse_mode="HTML",
        reply_markup=kb_back_cancel()
    )
    await state.set_state(RegistCaregiver.waiting_last_name)

# Step 2: Last name
@router.message(RegistCaregiver.waiting_last_name, ~(Text("⬅️ Voltar") | Text("❌ Cancelar") | Text(startswith="⏭️")))
async def caregiver_last_name(message: types.Message, state: FSMContext) -> None:
    """Handles the caregiver's last name input."""
    last = message.text.strip()
    if not last:
        await message.answer("❗ Por favor, indique um apelido válido.")
        return
    await state.update_data(last_name=last)
    logger.info(f"Apelido do cuidador: {last}", extra={"telegram_user_id": message.from_user.id})
    # Ask for email (optional)
    await message.answer(
        "✅ Apelido recebido. Qual é o <b>email</b> do cuidador? (Opcional)",
        parse_mode="HTML",
        reply_markup=kb_skip_email()
    )
    await state.set_state(RegistCaregiver.waiting_email)

# Step 3: Email (optional) - skip
@router.message(RegistCaregiver.waiting_email, Text(startswith="⏭️"))
async def caregiver_skip_email(message: types.Message, state: FSMContext) -> None:
    """Handles skipping the email step."""
    await state.update_data(email=None)
    logger.info("Utilizador optou por não fornecer email (cuidador)", extra={"telegram_user_id": message.from_user.id})
    # Ask for caregiver's own phone number
    await message.answer(
        "Por favor, partilhe o <b>seu número de telemóvel</b>:",
        parse_mode="HTML",
        reply_markup=kb_share_phone()
    )
    await state.set_state(RegistCaregiver.waiting_phone_self)

# Step 3: Email (optional) - provided
@router.message(RegistCaregiver.waiting_email, ~(Text("⬅️ Voltar") | Text("❌ Cancelar") | Text(startswith="⏭️")))
async def caregiver_email(message: types.Message, state: FSMContext) -> None:
    """Handles the provided email address."""
    email_text = message.text.strip()
    await state.update_data(email=email_text)
    logger.info(f"Email do cuidador: {email_text}", extra={"telegram_user_id": message.from_user.id})
    # Ask for caregiver's own phone number
    await message.answer(
        "Por favor, partilhe o <b>seu número de telemóvel</b>:",
        parse_mode="HTML",
        reply_markup=kb_share_phone()
    )
    await state.set_state(RegistCaregiver.waiting_phone_self)

# Step 4: Caregiver's phone number
@router.message(RegistCaregiver.waiting_phone_self, types.F.content_type == "contact")
async def caregiver_phone_shared(message: types.Message, state: FSMContext) -> None:
    """Handles sharing the caregiver's own phone contact."""
    caregiver_phone = message.contact.phone_number
    await state.update_data(caregiver_phone=caregiver_phone)
    logger.info(f"Telefone do cuidador recebido: {caregiver_phone}", extra={"telegram_user_id": message.from_user.id})
    # Ask for the patient's phone number to associate
    await message.answer(
        "✔️ Agora partilhe o <b>número de telemóvel do paciente</b> que pretende associar:",
        parse_mode="HTML",
        reply_markup=kb_share_phone()
    )
    await state.set_state(RegistCaregiver.waiting_patient_phone)

# Step 5: Patient's phone number for linking
@router.message(RegistCaregiver.waiting_patient_phone, types.F.content_type == "contact")
async def caregiver_patient_phone(message: types.Message, state: FSMContext) -> None:
    """Handles sharing the patient's phone contact to link caregiver to patient."""
    patient_phone = message.contact.phone_number
    logger.info(f"Telefone do paciente fornecido: {patient_phone}", extra={"telegram_user_id": message.from_user.id})
    # Simulate patient lookup in database
    # (In a real scenario, you'd query the DB for a patient with this phone)
    patient = {"user_id": 0, "first_name": "N/D", "last_name": ""}  # Dummy default
    # TODO: Look up patient in database by phone (e.g., find_patient_by_phone(patient_phone))
    if patient is None or patient.get("user_id") is None or patient.get("user_id") == 0:
        # Patient not found
        logger.warning(f"Nenhum paciente encontrado para o telefone {patient_phone}", extra={"telegram_user_id": message.from_user.id})
        await message.answer("⚠️ Não encontramos nenhum paciente com esse número. Tente novamente ou contacte a clínica.")
        # Remain in the same state to allow retry or cancellation
        return
    # If found, prepare for confirmation
    patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip() or "Paciente encontrado"
    await state.update_data(patient_id=patient.get("user_id"), patient_name=patient_name, patient_phone=patient_phone)
    data = await state.get_data()
    first = data.get("first_name")
    last = data.get("last_name")
    email = data.get("email")
    email_info = email if email else "Não fornecido"
    caregiver_phone = data.get("caregiver_phone")
    # Summarize information for confirmation
    summary = (
        "Por favor, confirme os dados do registo:\n"
        f"👤 Cuidador: {first} {last}\n"
        f"📧 Email: {email_info}\n"
        f"📞 Telemóvel do cuidador: {caregiver_phone}\n"
        f"🤝 Paciente associado: {patient_name}"
    )
    confirm_kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Confirmar", callback_data="confirm_caregiver")],
        [types.InlineKeyboardButton(text="⬅️ Voltar", callback_data="back_caregiver")],
        [types.InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel_caregiver")]
    ])
    sent_msg = await message.answer(summary, reply_markup=types.ReplyKeyboardRemove())
    try:
        await message.bot.edit_message_reply_markup(chat_id=sent_msg.chat.id, message_id=sent_msg.message_id, reply_markup=confirm_kb)
    except Exception as e:
        logger.error(f"Erro ao adicionar teclado de confirmação: {e}", extra={"telegram_user_id": message.from_user.id})
        await message.answer("Por favor confirme os dados acima.", reply_markup=confirm_kb)
    await state.set_state(RegistCaregiver.confirming)

# Confirmation step: user clicked "✅ Confirmar"
@router.callback_query(RegistCaregiver.confirming, Text("confirm_caregiver"))
async def caregiver_confirm(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Finalizes the caregiver registration after confirmation."""
    data = await state.get_data()
    first = data.get("first_name")
    last = data.get("last_name")
    email = data.get("email")
    caregiver_phone = data.get("caregiver_phone")
    patient_id = data.get("patient_id")
    patient_name = data.get("patient_name")
    logger.info(f"Registo de cuidador confirmado: {first} {last} -> paciente {patient_name}", extra={"telegram_user_id": callback.from_user.id})
    # TODO: Save new caregiver into database (e.g., create_caregiver_user with name, Telegram ID, email)
    # TODO: Insert caregiver role into user_roles (e.g., add_role_to_user(user_id, "caregiver"))
    # TODO: Link caregiver to patient in database (e.g., link_caregiver_to_patient(user_id, patient_id))
    # TODO: Update user's telegram_user_id in users table (if not set during creation)
    await state.clear()
    # Notify user of success
    await callback.message.edit_text(
        "🎉 Cuidador registado e associado ao paciente com sucesso! Já pode usar o menu de cuidador.",
        reply_markup=None
    )

# Confirmation step: user clicked "⬅️ Voltar"
@router.callback_query(RegistCaregiver.confirming, Text("back_caregiver"))
async def caregiver_confirm_back(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Allows the user to go back one step from the confirmation stage."""
    try:
        await callback.message.delete()
    except Exception:
        pass
    # Go back to patient phone step
    await state.set_state(RegistCaregiver.waiting_patient_phone)
    await callback.message.answer(
        "Por favor, partilhe o <b>número de telemóvel do paciente</b> que pretende associar:",
        parse_mode="HTML",
        reply_markup=kb_share_phone()
    )

# Confirmation step: user clicked "❌ Cancelar"
@router.callback_query(RegistCaregiver.confirming, Text("cancel_caregiver"))
async def caregiver_confirm_cancel(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Cancels the registration from the confirmation stage."""
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    logger.info("Registo de cuidador cancelado pelo utilizador na confirmação", extra={"telegram_user_id": callback.from_user.id})
    await callback.message.answer("Operação cancelada.", reply_markup=types.ReplyKeyboardRemove())
    await callback.message.answer(
        "Ainda assim, podes ver alguma informação pública 👇",
        reply_markup=visitor_main_kb()
    )

# Handler for text "⬅️ Voltar" during intermediate steps
@router.message(
    RegistCaregiver.waiting_first_name,
    RegistCaregiver.waiting_last_name,
    RegistCaregiver.waiting_email,
    RegistCaregiver.waiting_phone_self,
    RegistCaregiver.waiting_patient_phone,
    Text("⬅️ Voltar")
)
async def caregiver_go_back(message: types.Message, state: FSMContext) -> None:
    """Handles the 'Voltar' action to move one step back in the FSM."""
    current_state = await state.get_state()
    if current_state == RegistCaregiver.waiting_last_name.state:
        # Back to first name
        await state.set_state(RegistCaregiver.waiting_first_name)
        await message.answer(
            "Vamos voltar atrás. Qual é o <b>primeiro nome</b> do cuidador?",
            parse_mode="HTML",
            reply_markup=kb_back_cancel()
        )
    elif current_state == RegistCaregiver.waiting_email.state:
        # Back to last name
        await state.set_state(RegistCaregiver.waiting_last_name)
        await message.answer(
            "Vamos voltar atrás. Indique novamente o <b>apelido</b> do cuidador:",
            parse_mode="HTML",
            reply_markup=kb_back_cancel()
        )
    elif current_state == RegistCaregiver.waiting_phone_self.state:
        # Back to email step
        await state.set_state(RegistCaregiver.waiting_email)
        data = await state.get_data()
        prev_email = data.get("email")
        email_prompt = "Qual é o <b>email</b> do cuidador? (Opcional)"
        if prev_email:
            email_prompt = f"Qual é o <b>email</b> do cuidador? (Atual: {prev_email})"
        await message.answer(
            f"Vamos voltar atrás. {email_prompt}",
            parse_mode="HTML",
            reply_markup=kb_skip_email()
        )
    elif current_state == RegistCaregiver.waiting_patient_phone.state:
        # Back to caregiver's phone step
        await state.set_state(RegistCaregiver.waiting_phone_self)
        await message.answer(
            "Vamos voltar atrás. Por favor, partilhe o <b>seu número de telemóvel</b>:",
            parse_mode="HTML",
            reply_markup=kb_share_phone()
        )
    else:
        # At first name, go back to role selection menu
        await state.clear()
        await message.answer("A regressar à seleção de perfil...", reply_markup=types.ReplyKeyboardRemove())
        await router.emit(
            types.Message(chat=message.chat, from_user=message.from_user, text="/register"),
            message.bot
        )

# Handler for text "❌ Cancelar" during intermediate steps
@router.message(
    RegistCaregiver.waiting_first_name,
    RegistCaregiver.waiting_last_name,
    RegistCaregiver.waiting_email,
    RegistCaregiver.waiting_phone_self,
    RegistCaregiver.waiting_patient_phone,
    Text("❌ Cancelar")
)
async def caregiver_cancel(message: types.Message, state: FSMContext) -> None:
    """Cancels the caregiver registration flow at any intermediate step."""
    await state.clear()
    logger.info("Registo de cuidador cancelado pelo utilizador (fluxo interrompido)", extra={"telegram_user_id": message.from_user.id})
    await message.answer("Operação cancelada.", reply_markup=types.ReplyKeyboardRemove())
    await message.answer(
        "Ainda assim, podes ver alguma informação pública 👇",
        reply_markup=visitor_main_kb()
    )
