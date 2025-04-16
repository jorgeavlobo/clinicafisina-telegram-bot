import asyncio
from os import getenv

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.key_builders import DefaultKeyBuilder
from redis.asyncio import Redis
from config import (
    TELEGRAM_TOKEN,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PREFIX,
)

# Initialize Redis client
redis_client = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)

# Initialize storage with custom prefix
storage = RedisStorage(
    redis=redis_client,
    key_builder=DefaultKeyBuilder(with_prefix=REDIS_PREFIX)
)

# Initialize bot and dispatcher with storage
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(storage=storage)

# Set up router
router = Router()

# Command handler for /start
@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.reply("Hello! Welcome to the Clinica Fisina Telegram bot.")

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
    await message.reply("Contact us at:\n- Email: contact@clinic.com\n- Phone: +123456789")

# Include the router in the dispatcher
dp.include_router(router)

# Run the bot
async def main() -> None:
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
