# bot/handlers/auth_handlers.py

from aiogram import Router, types
from aiogram.filters import Command

router = Router(name="auth")

@router.message(Command("auth_dummy"))
async def accountant_dummy(msg: types.Message):
    await msg.answer("Auth handler stub está OK.")
