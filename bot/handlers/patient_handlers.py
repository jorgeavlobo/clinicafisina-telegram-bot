# bot/handlers/patient_handlers.py

from aiogram import Router, types
from aiogram.filters import Command

router = Router(name="patient")

@router.message(Command("patient_dummy"))
async def accountant_dummy(msg: types.Message):
    await msg.answer("Patient handler stub está OK.")
