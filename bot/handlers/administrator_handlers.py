# bot/handlers/administrator_handlers.py

from aiogram import Router, types
from aiogram.filters import Command

router = Router(name="administrator")

@router.message(Command("administrator_dummy"))
async def accountant_dummy(msg: types.Message):
    await msg.answer("Administrator handler stub está OK.")
