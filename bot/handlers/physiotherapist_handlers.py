# bot/handlers/physiotherapist_handlers.py

from aiogram import Router, types
from aiogram.filters import Command

router = Router(name="physiotherapist")

@router.message(Command("physiotherapist_dummy"))
async def accountant_dummy(msg: types.Message):
    await msg.answer("Physiotherapist handler stub está OK.")
