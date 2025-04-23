# bot/handlers/auth_handlers.py

from aiogram import Router

router = Router(name="auth")

# opcional – placeholder de comando
@router.message(commands=["auth_dummy"])
async def _(message):
    await message.answer("Auth handler stub está OK.")
