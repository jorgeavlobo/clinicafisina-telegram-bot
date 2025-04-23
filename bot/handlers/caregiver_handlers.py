# bot/handlers/caregiver_handlers.py

from aiogram import Router, types
from aiogram.filters import Command

router = Router(name="caregiver")

@router.message(Command("caregiver_dummy"))
async def accountant_dummy(msg: types.Message):
    await msg.answer("Caregiver handler stub está OK.")
