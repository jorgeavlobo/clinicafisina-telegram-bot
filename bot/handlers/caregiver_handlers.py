# bot/handlers/caregiver_handlers.py

from aiogram import Router

router = Router(name="caregiver")

# opcional – placeholder de comando
@router.message(commands=["caregiver_dummy"])
async def _(message):
    await message.answer("Caregiver handler stub está OK.")
