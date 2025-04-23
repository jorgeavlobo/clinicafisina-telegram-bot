# bot/handlers/administrator_handlers.py

from aiogram import Router

router = Router(name="administrator")

# opcional – placeholder de comando
@router.message(commands=["administrator_dummy"])
async def _(message):
    await message.answer("Administrator handler stub está OK.")
