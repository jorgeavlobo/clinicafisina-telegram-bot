from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
import logging

router = Router()
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  /services
# ------------------------------------------------------------------ #
@router.message(Command("services"))
async def cmd_services(msg: Message):
    await msg.answer(
        "📋 <b>Our services</b>\n"
        "• Physiotherapy\n"
        "• Osteopathy\n"
        "• Post‑surgery rehab"
    )
    logger.info(
        "/services answered",
        extra={
            "telegram_user_id": msg.from_user.id,
            "chat_id": msg.chat.id,
            "is_system": False,
        },
    )
    await msg.delete()

# ------------------------------------------------------------------ #
#  /team
# ------------------------------------------------------------------ #
@router.message(Command("team"))
async def cmd_team(msg: Message):
    await msg.answer(
        "👩‍⚕️ <b>Meet the team</b>\n"
        "• Ana (Physiotherapist)\n"
        "• Rui (Osteopath)"
    )
    logger.info(
        "/team answered",
        extra={
            "telegram_user_id": msg.from_user.id,
            "chat_id": msg.chat.id,
            "is_system": False,
        },
    )
    await msg.delete()

# ------------------------------------------------------------------ #
#  /contacts
# ------------------------------------------------------------------ #
@router.message(Command("contacts"))
async def cmd_contacts(msg: Message):
    await msg.answer(
        "📞 <b>Contacts</b>\n"
        "• Phone: +351 910 910 910\n"
        "• Email: geral@fisina.pt"
    )
    logger.info(
        "/contacts answered",
        extra={
            "telegram_user_id": msg.from_user.id,
            "chat_id": msg.chat.id,
            "is_system": False,
        },
    )
    await msg.delete()
