# bot/handlers/caregiver_handlers.py
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="caregiver")

@router.message(Command("caregiver_dummy"))
async def accountant_dummy(message: Message) -> None:
    """Stub handler só para confirmar que o router está registado."""
    await message.answer("Caregiver handler stub está OK.")
