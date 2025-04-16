import asyncio
from os import getenv

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.base import DefaultKeyBuilder
from redis.asyncio import Redis
from datetime import timedelta
from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PREFIX, TELEGRAM_TOKEN

# Create Redis connection
redis = Redis(host=REDIS_HOST, port=int(REDIS_PORT), db=int(REDIS_DB))

# Create key builder with custom prefix
key_builder = DefaultKeyBuilder(prefix=REDIS_PREFIX)

# Create storage with TTL (e.g., 24 hours)
storage = RedisStorage(
    redis=redis,
    key_builder=key_builder,
    state_ttl=timedelta(hours=24),
    data_ttl=timedelta(hours=24)
)

# Initialize the dispatcher with Redis storage
dp = Dispatcher(storage=storage)

# Set up router
router = Router()

# Command handler for /start
@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.reply("Olá! Bem-vindo à Clínica Fisina.")

# Command handler for /services
@router.message(Command("services"))
async def command_services_handler(message: Message) -> None:
    await message.reply("Os nossos serviços incluem:\n- Service 1\n- Service 2\n- Service 3")

# Command handler for /team
@router.message(Command("team"))
async def command_team_handler(message: Message) -> None:
    await message.reply("Conhece a nossa equipa:\n- Member 1\n- Member 2\n- Member 3")

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
