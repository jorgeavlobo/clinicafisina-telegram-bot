import asyncio
from os import getenv

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
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

# Command handler
@router.message(CommandStart())
async def command_start_handler(message):
    await message.reply("Hello! Welcome to the Clinica Fisina Telegram bot.")

# Include the router in the dispatcher
dp.include_router(router)

# Run the bot
async def main():
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
