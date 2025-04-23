# bot/handlers/accountant_handlers.py
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="accountant")

@router.message(Command("accountant_dummy"))
async def accountant_dummy(message: Message) -> None:
    """Stub handler só para confirmar que o router está registado."""
    await message.answer("Accountant handler stub está OK.")
