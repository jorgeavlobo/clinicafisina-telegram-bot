# bot/handlers/patient_handlers.py

from aiogram import Router

router = Router(name="patient")

# opcional – placeholder de comando
@router.message(commands=["patient_dummy"])
async def _(message):
    await message.answer("Patient handler stub está OK.")
