from aiogram import Router, types, F

from handlers.common.keyboards import regist_menu_kb, share_phone_kb

router = Router(name="regist_menu")

@router.callback_query(F.data == "visitor_register")
async def cb_register(call: types.CallbackQuery):
    await call.message.edit_text(
        "Que tipo de registo pretendes fazer?",
        reply_markup=regist_menu_kb()
    )
