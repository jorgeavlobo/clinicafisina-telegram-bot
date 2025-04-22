# handlers/auth/start_router.py
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from handlers.common.keyboards import share_phone_kb
from dal.dal import fetch_user_by_telegram_id, log_visitor_action

router = Router(name="auth_start")


@router.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    tg_id = message.from_user.id

    user = await fetch_user_by_telegram_id(tg_id)
    if user:
        # Já reconhecido → encaminhar para dispatcher central
        await state.clear()
        await message.answer(
            "Bem‑vindo novamente 👋 Vou carregar o teu menu…",
            reply_markup=ReplyKeyboardRemove()
        )
        await log_visitor_action(telegram_id=tg_id, action="start_known")
        # O dispatch global cuida do menu adequado
        return

    # Desconhecido → pedir contacto
    await state.set_state("awaiting_phone")
    await message.answer(
        "Olá! Para confirmar a tua identidade, partilha o teu número 📱",
        reply_markup=share_phone_kb()
    )
    await log_visitor_action(telegram_id=tg_id, action="start_unknown")
