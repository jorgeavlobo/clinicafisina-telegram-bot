import asyncio
from os import getenv

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

# Get the bot token from environment variables
TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN")

# Initialize the dispatcher with default in-memory storage
dp = Dispatcher()

# Set up router
router = Router()

# Command handler for /start
@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.reply("Olá! Bem-vindo à Clínica Fisina.")

# Command handler for /services
@router.message(Command("services"))
async def command_services_handler(message: Message) -> None:
    await message.reply("Our services include:\n- Service 1\n- Service 2\n- Service 3")

# Command handler for /team
@router.message(Command("team"))
async def command_team_handler(message: Message) -> None:
    await message.reply("Meet our team:\n- Member 1\n- Member 2\n- Member 3")

# Command handler for /contacts
@router.message(Command("contacts"))
async def command_contacts_handler(message: Message) -> None:
    await message.reply("Contacte-nos:\n- Email: geral@fisina.pt\n- Phone: +351 910 910 910")

# Include the router in the dispatcher
dp.include_router(router)

# Run the bot
async def main() -> None:
    bot = Bot(token=TELEGRAM_TOKEN)
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
