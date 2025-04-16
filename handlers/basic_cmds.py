from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command("services"))
async def cmd_services(msg: Message):
    await msg.answer(
        "📋 <b>Our services</b>\n"
        "• Physiotherapy\n"
        "• Osteopathy\n"
        "• Post‑surgery rehab"
    )
    await msg.delete()        # clean UI

@router.message(Command("team"))
async def cmd_team(msg: Message):
    await msg.answer(
        "👩‍⚕️ <b>Meet the team</b>\n"
        "• Ana (Physiotherapist)\n"
        "• Rui (Osteopath)"
    )
    await msg.delete()

@router.message(Command("contacts"))
async def cmd_contacts(msg: Message):
    await msg.answer(
        "📞 <b>Contacts</b>\n"
        "• Phone: +351 910 910 910\n"
        "• Email: geral@fisina.pt"
    )
    await msg.delete()
