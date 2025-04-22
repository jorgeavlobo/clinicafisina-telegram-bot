from aiogram import Router, types

router = Router(name="system_fallback")

@router.message()
async def default(msg: types.Message):
    await msg.answer("❓ Não entendi. Usa o menu ou /start para começar.")
