"""FSM router for patient registration flow."""

from aiogram import Router, types
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from handlers.common.keyboards import visitor_main_kb
from logging import getLogger

logger = getLogger(__name__)
router = Router(name="registration_patient")

# FSM state definitions
class RegistPatient(StatesGroup):
    waiting_first_name = State()
    waiting_last_name = State()
    waiting_email = State()
    waiting_phone = State()
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

# Entry point: Start patient registration
@router.message(Command("regist_patient"))
async def cmd_regist_patient(message: types.Message, state: FSMContext) -> None:
    """Starts the patient registration FSM flow."""
    await state.clear()  # reset any existing state
    logger.info(f"Utilizador {message.from_user.id} iniciou registo como paciente", extra={"telegram_user_id": message.from_user.id})
    # Ask for first name
    await message.answer(
        "📝 Qual é o <b>primeiro nome</b> do paciente?",
        parse_mode="HTML",
        reply_markup=kb_back_cancel()
    )
    await state.set_state(RegistPatient.waiting_first_name)

# Step 1: First name
@router.message(RegistPatient.waiting_first_name, ~(Text("⬅️ Voltar") | Text("❌ Cancelar") | Text(startswith="⏭️")))
async def patient_first_name(message: types.Message, state: FSMContext) -> None:
    """Handles the first name input."""
    first = message.text.strip()
    if not first:
        await message.answer("❗ Por favor, indique um nome válido.")
        return
    await state.update_data(first_name=first)
    logger.info(f"Primeiro nome recebido: {first}", extra={"telegram_user_id": message.from_user.id})
    # Ask for last name
    await message.answer(
        "✅ Recebido. Agora indique o <b>apelido</b>:",
        parse_mode="HTML",
        reply_markup=kb_back_cancel()
    )
    await state.set_state(RegistPatient.waiting_last_name)

# Step 2: Last name
@router.message(RegistPatient.waiting_last_name, ~(Text("⬅️ Voltar") | Text("❌ Cancelar") | Text(startswith="⏭️")))
async def patient_last_name(message: types.Message, state: FSMContext) -> None:
    """Handles the last name input."""
    last = message.text.strip()
    if not last:
        await message.answer("❗ Por favor, indique um apelido válido.")
        return
    await state.update_data(last_name=last)
    logger.info(f"Apelido recebido: {last}", extra={"telegram_user_id": message.from_user.id})
    # Ask for email (optional)
    await message.answer(
        "✅ Apelido recebido. Qual é o <b>email</b>? (Opcional)",
        parse_mode="HTML",
        reply_markup=kb_skip_email()
    )
    await state.set_state(RegistPatient.waiting_email)

# Step 3: Email (optional) - skip
@router.message(RegistPatient.waiting_email, Text(startswith="⏭️"))
async def patient_skip_email(message: types.Message, state: FSMContext) -> None:
    """Handles skipping the email step."""
    await state.update_data(email=None)
    logger.info("Utilizador optou por não fornecer email", extra={"telegram_user_id": message.from_user.id})
    # Proceed to phone number collection
    await message.answer(
        "Quase pronto! Por favor, partilhe o <b>número de telemóvel</b> para concluir o registo:",
        parse_mode="HTML",
        reply_markup=kb_share_phone()
    )
    await state.set_state(RegistPatient.waiting_phone)

# Step 3: Email (optional) - provided
@router.message(RegistPatient.waiting_email, ~(Text("⬅️ Voltar") | Text("❌ Cancelar") | Text(startswith="⏭️")))
async def patient_email(message: types.Message, state: FSMContext) -> None:
    """Handles the provided email address."""
    email_text = message.text.strip()
    await state.update_data(email=email_text)
    logger.info(f"Email recebido: {email_text}", extra={"telegram_user_id": message.from_user.id})
    # Proceed to phone number collection
    await message.answer(
        "Quase pronto! Por favor, partilhe o <b>número de telemóvel</b> para concluir o registo:",
        parse_mode="HTML",
        reply_markup=kb_share_phone()
    )
    await state.set_state(RegistPatient.waiting_phone)

# Step 4: Phone number (contact share)
@router.message(RegistPatient.waiting_phone, types.F.content_type == "contact")
async def patient_phone_shared(message: types.Message, state: FSMContext) -> None:
    """Handles the shared phone contact."""
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    data = await state.get_data()
    first = data.get("first_name")
    last = data.get("last_name")
    email = data.get("email")
    email_info = email if email else "Não fornecido"
    # Prepare confirmation summary
    summary = (
        "Por favor, confirme os seus dados:\n"
        f"👤 Nome: {first} {last}\n"
        f"📧 Email: {email_info}\n"
        f"📞 Telemóvel: {phone}"
    )
    # Inline keyboard for confirmation
    confirm_kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Confirmar", callback_data="confirm_patient")],
        [types.InlineKeyboardButton(text="⬅️ Voltar", callback_data="back_patient")],
        [types.InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel_patient")]
    ])
    # Send confirmation prompt (remove reply keyboard by editing markup)
    sent_msg = await message.answer(summary, reply_markup=types.ReplyKeyboardRemove())
    try:
        await message.bot.edit_message_reply_markup(chat_id=sent_msg.chat.id, message_id=sent_msg.message_id, reply_markup=confirm_kb)
    except Exception as e:
        # In case editing fails, send separate message with inline keyboard
        logger.error(f"Erro ao adicionar teclado de confirmação: {e}", extra={"telegram_user_id": message.from_user.id})
        await message.answer("Por favor confirme os dados acima.", reply_markup=confirm_kb)
    await state.set_state(RegistPatient.confirming)
    # (State remains `confirming` until user presses Confirm/Voltar/Cancelar)

# Confirmation step: user clicked "✅ Confirmar"
@router.callback_query(RegistPatient.confirming, Text("confirm_patient"))
async def patient_confirm(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Finalizes the patient registration after confirmation."""
    data = await state.get_data()
    first = data.get("first_name")
    last = data.get("last_name")
    email = data.get("email")
    phone = data.get("phone")
    logger.info(f"Registo de paciente confirmado: {first} {last}", extra={"telegram_user_id": callback.from_user.id})
    # TODO: Save new patient into database (e.g., create_patient_user with name, Telegram ID, email)
    # TODO: Insert patient role into user_roles table (e.g., add_role_to_user(user_id, "patient"))
    # TODO: Update user's telegram_user_id in users table (if not set during creation)
    await state.clear()
    # Notify user of success
    await callback.message.edit_text(
        "🎉 Registo concluído com sucesso! Já pode usar o menu de paciente.",
        reply_markup=None
    )
    # Optionally, could automatically open the patient menu:
    # await router.emit(types.Message(chat=callback.message.chat, from_user=callback.from_user, text="/menu_patient"), callback.bot)

# Confirmation step: user clicked "⬅️ Voltar" (to edit previous input)
@router.callback_query(RegistPatient.confirming, Text("back_patient"))
async def patient_confirm_back(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Allows the user to go back one step from the confirmation stage."""
    # Remove the confirmation message
    try:
        await callback.message.delete()
    except Exception:
        pass
    # Go back to phone number step
    await state.set_state(RegistPatient.waiting_phone)
    await callback.message.answer(
        "Por favor, partilhe o <b>número de telemóvel</b> para concluir o registo:",
        parse_mode="HTML",
        reply_markup=kb_share_phone()
    )

# Confirmation step: user clicked "❌ Cancelar"
@router.callback_query(RegistPatient.confirming, Text("cancel_patient"))
async def patient_confirm_cancel(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Cancels the registration from the confirmation stage."""
    await state.clear()
    # Remove the confirmation message
    try:
        await callback.message.delete()
    except Exception:
        pass
    logger.info("Registo de paciente cancelado pelo utilizador na confirmação", extra={"telegram_user_id": callback.from_user.id})
    # Inform user and show visitor menu
    await callback.message.answer("Operação cancelada.", reply_markup=types.ReplyKeyboardRemove())
    await callback.message.answer(
        "Ainda assim, podes ver alguma informação pública 👇",
        reply_markup=visitor_main_kb()
    )

# Handler for text "⬅️ Voltar" during intermediate steps (go back to previous step)
@router.message(
    RegistPatient.waiting_first_name,
    RegistPatient.waiting_last_name,
    RegistPatient.waiting_email,
    RegistPatient.waiting_phone,
    Text("⬅️ Voltar")
)
async def patient_go_back(message: types.Message, state: FSMContext) -> None:
    """Handles the 'Voltar' action to move one step back in the FSM."""
    current_state = await state.get_state()
    if current_state == RegistPatient.waiting_last_name.state:
        # Go back from last name to first name
        await state.set_state(RegistPatient.waiting_first_name)
        await message.answer(
            "Vamos voltar atrás. Qual é o <b>primeiro nome</b> do paciente?",
            parse_mode="HTML",
            reply_markup=kb_back_cancel()
        )
    elif current_state == RegistPatient.waiting_email.state:
        # Go back from email to last name
        await state.set_state(RegistPatient.waiting_last_name)
        await message.answer(
            "Vamos voltar atrás. Indique novamente o <b>apelido</b>:",
            parse_mode="HTML",
            reply_markup=kb_back_cancel()
        )
    elif current_state == RegistPatient.waiting_phone.state:
        # Go back from phone to email step
        await state.set_state(RegistPatient.waiting_email)
        # If an email was previously provided, include it in the prompt
        data = await state.get_data()
        prev_email = data.get("email")
        email_prompt = "Qual é o <b>email</b>? (Opcional)"
        if prev_email:
            email_prompt = f"Qual é o <b>email</b>? (Atual: {prev_email})"
        await message.answer(
            f"Vamos voltar atrás. {email_prompt}",
            parse_mode="HTML",
            reply_markup=kb_skip_email()
        )
    else:
        # At first name step, 'Voltar' goes back to role selection menu
        await state.clear()
        await message.answer("A regressar à seleção de perfil...", reply_markup=types.ReplyKeyboardRemove())
        # Re-open the registration role menu
        await router.emit(
            types.Message(chat=message.chat, from_user=message.from_user, text="/register"),
            message.bot
        )

# Handler for text "❌ Cancelar" during intermediate steps (cancel the registration flow)
@router.message(
    RegistPatient.waiting_first_name,
    RegistPatient.waiting_last_name,
    RegistPatient.waiting_email,
    RegistPatient.waiting_phone,
    Text("❌ Cancelar")
)
async def patient_cancel(message: types.Message, state: FSMContext) -> None:
    """Cancels the patient registration flow at any intermediate step."""
    await state.clear()
    logger.info("Registo de paciente cancelado pelo utilizador (fluxo interrompido)", extra={"telegram_user_id": message.from_user.id})
    await message.answer("Operação cancelada.", reply_markup=types.ReplyKeyboardRemove())
    await message.answer(
        "Ainda assim, podes ver alguma informação pública 👇",
        reply_markup=visitor_main_kb()
    )
