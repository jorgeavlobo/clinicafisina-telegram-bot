"""
bot.py

Main script for the Clinica Fisina Telegram bot, handling user interactions
with FSM state storage in Redis and data/logging in PostgreSQL databases.
"""

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
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

# Initialize bot and storage
bot = Bot(token=TELEGRAM_TOKEN)
storage = RedisStorage(redis=redis_client, key_builder=DefaultKeyBuilder(with_prefix=REDIS_PREFIX))
dp = Dispatcher(bot=bot, storage=storage)

# Example handler
from aiogram import Router
from aiogram.filters import CommandStart

router = Router()

@router.message(CommandStart())
async def cmd_start(message):
    await message.reply("Hello! Welcome to the Clinica Fisina Telegram bot.")

# Include the router in the dispatcher
dp.include_router(router)

if __name__ == '__main__':
    dp.run_polling(bot, skip_updates=True)
