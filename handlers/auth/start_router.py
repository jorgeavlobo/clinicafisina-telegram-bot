from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from shared.dal import DAL
from handlers.common.keyboards import share_phone_kb, visitor_main_kb

router = Router(name="auth_start")

@router.message(F.text == "/start")
async def cmd_start(msg: types.Message, state: FSMContext):
    user = await DAL.get_user_by_telegram_id(msg.from_user.id)
    if user:
        await msg.answer("🌟 Bem‑vindo de volta! Usa o menu abaixo 👇")
        # TODO: dispatch to role menu once implemented
        return

    await msg.answer(
        "👋 Olá! Preciso que partilhes o teu nº de telemóvel para te identificar.",
        reply_markup=share_phone_kb()
    )
