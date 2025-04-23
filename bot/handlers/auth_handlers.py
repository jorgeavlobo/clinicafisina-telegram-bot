# bot/handlers/auth_handlers.py
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="auth")

@router.message(Command("auth_dummy"))
async def accountant_dummy(message: Message) -> None:
    """Stub handler só para confirmar que o router está registado."""
    await message.answer("Auth handler stub está OK.")
