from aiogram import Router, types, F

router = Router(name="role_switch")

@router.callback_query(F.data.startswith("role_"))
async def switch(call: types.CallbackQuery):
    role = call.data.split("_", 1)[1]
    await call.answer()
    await call.message.answer(f"🔄 Mudaste para perfil: {role.title()} (demo)")
