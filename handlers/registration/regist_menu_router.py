from aiogram import Router, types
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import ReplyKeyboardMarkup, KeyboardButton
from logging import getLogger

logger = getLogger(__name__)
router = Router(name="registration_menu")

# ---------- Keyboard helpers ----------
def kb_registration_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Registar‑me como Paciente")],
            [KeyboardButton(text="👥 Registar‑me como Cuidador")],
            [KeyboardButton(text="⬅️ Voltar")]
        ],
        resize_keyboard=True
    )

# ---------- FSM ----------
class RegistMenu(StatesGroup):
    waiting_choice = State()

# ---------- Handlers ----------
@router.message(Command("register"))
async def cmd_register(msg: types.Message, state: FSMContext) -> None:
    """
    Entrada principal para /register (ou quando menu unregistered_user conduz aqui).
    """
    # Apaga eventual menu anterior associado à sessão
    old_msg_id = (await state.get_data()).get("last_menu_id")
    if old_msg_id:
        await msg.bot.delete_message(chat_id=msg.chat.id, message_id=old_msg_id)

    sent = await msg.answer(
        "Como pretende registar‑se? Escolha uma das opções:",
        reply_markup=kb_registration_menu()
    )

    # Guardar id do menu para poder apagar quando reentrar
    await state.update_data(last_menu_id=sent.message_id)
    await state.set_state(RegistMenu.waiting_choice)

@router.message(RegistMenu.waiting_choice, Text("⬅️ Voltar"))
async def back_to_start(msg: types.Message, state: FSMContext) -> None:
    """
    Regressa ao fluxo de identificação original (router visitor ou auth).
    """
    await state.clear()
    await msg.answer(
        "Ok, voltámos atrás. Utilize /start para recomeçar.",
        reply_markup=types.ReplyKeyboardRemove()
    )

@router.message(RegistMenu.waiting_choice, Text("📝 Registar‑me como Paciente"))
async def select_patient(msg: types.Message, state: FSMContext) -> None:
    await state.clear()
    # Passamos a outro router → enviamos comando virtual
    await router.emit(types.Message(
        chat=msg.chat,
        from_user=msg.from_user,
        message_id=msg.message_id,
        date=msg.date,
        text="/regist_patient"
    ), msg.bot)

@router.message(RegistMenu.waiting_choice, Text("👥 Registar‑me como Cuidador"))
async def select_caregiver(msg: types.Message, state: FSMContext) -> None:
    await state.clear()
    await router.emit(types.Message(
        chat=msg.chat,
        from_user=msg.from_user,
        message_id=msg.message_id,
        date=msg.date,
        text="/regist_caregiver"
    ), msg.bot)
