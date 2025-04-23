# bot/handlers/patient_handlers.py
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="patient")

@router.message(Command("patient_dummy"))
async def accountant_dummy(message: Message) -> None:
    """Stub handler só para confirmar que o router está registado."""
    await message.answer("Patient handler stub está OK.")
