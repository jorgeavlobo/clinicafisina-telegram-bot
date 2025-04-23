# bot/handlers/accountant_handlers.py

from aiogram import Router, types
from aiogram.filters import Command

router = Router(name="accountant")

@router.message(Command("accountant_dummy"))
async def accountant_dummy(msg: types.Message):
    await msg.answer("Accountant handler stub está OK.")
