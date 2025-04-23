# bot/handlers/administrator_handlers.py
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="administrator")

@router.message(Command("administrator_dummy"))
async def accountant_dummy(message: Message) -> None:
    """Stub handler só para confirmar que o router está registado."""
    await message.answer("Administrator handler stub está OK.")
