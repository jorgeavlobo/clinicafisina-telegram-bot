"""
bot.py

Main script for the Clinica Fisina Telegram bot, handling user interactions
with FSM state storage in Redis and data/logging in PostgreSQL databases.
"""

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from config import (
    TELEGRAM_TOKEN,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PREFIX,
)

# Initialize bot and storage
bot = Bot(token=TELEGRAM_TOKEN)
storage = RedisStorage(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    prefix=REDIS_PREFIX
)
dp = Dispatcher(bot=bot, storage=storage)

# Example handler (replace with your bot's logic)
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
