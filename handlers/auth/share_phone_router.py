# handlers/auth/share_phone_router.py
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from keyboards import kb_visitor_menu
from dal.dal import fetch_user_by_phone, link_telegram_id, log_visitor_action

router = Router(name="auth_share_phone")


@router.message(
    F.contact,            # só mensagens que contêm contacto
    F.state == "awaiting_phone"
)
async def got_phone(message: types.Message, state: FSMContext) -> None:
    tg_id = message.from_user.id
    phone = message.contact.phone_number

    user = await fetch_user_by_phone(phone)

    if user:
        await link_telegram_id(user["user_id"], tg_id)
        await state.clear()
        await message.answer(
            "✅ Número confirmado! A carregar o teu menu…",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await log_visitor_action(telegram_id=tg_id, action="phone_linked", extra=phone)
        # Dispatcher global tratará do menu agora
    else:
        # Telefone não existe → visitante identificado mas não registado
        await state.clear()
        await message.answer(
            "⚠️ Ainda não estás registado na nossa base de dados.",
            reply_markup=kb_visitor_menu()
        )
        await log_visitor_action(telegram_id=tg_id, action="phone_unknown", extra=phone)
