# bot/handlers/physiotherapist_handlers.py

from aiogram import Router

router = Router(name="physiotherapist")

# opcional – placeholder de comando
@router.message(commands=["physiotherapist_dummy"])
async def _(message):
    await message.answer("Physiotherapist handler stub está OK.")
