from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from shared.dal import DAL
from handlers.common.keyboards import visitor_main_kb

router = Router(name="auth_share_phone")

@router.message(F.contact)
async def got_contact(msg: types.Message, state: FSMContext):
    phone = msg.contact.phone_number
    row = await DAL.find_user_by_phone(phone)
    if row:
        await DAL.link_telegram(row["user_id"], msg.from_user.id)
        await msg.answer("✅ Telefone reconhecido! Conta ligada.")
        # TODO: dispatch to role menu
        return
    await msg.answer(
        "⚠️ Não encontrei esse telefone nos nossos registos.
"
        "Serás tratado como visitante por agora.",
        reply_markup=visitor_main_kb()
    )
