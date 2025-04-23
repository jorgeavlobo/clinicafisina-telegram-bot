# bot/handlers/accountant_handlers.py

from aiogram import Router

router = Router(name="accountant")

# opcional – placeholder de comando
@router.message(commands=["accountant_dummy"])
async def _(message):
    await message.answer("Accountant handler stub está OK.")
