import os
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from redis.asyncio import Redis  # using redis-py asyncio for Redis connection
from dotenv import load_dotenv

# Load environment variables from .env (for local development; in Docker, env vars are set directly)
load_dotenv()

# Read configuration from environment
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")  # Telegram Bot API token
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB   = int(os.getenv("REDIS_DB", 0))
REDIS_PREFIX = os.getenv("REDIS_PREFIX", "fsm")

# Set up logging (optional, for debugging)
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher with Redis FSM storage
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
# Connect to Redis and configure FSM storage with 24h TTL for states and data
redis = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
storage = RedisStorage(
    redis=redis,
    state_ttl=86400,       # 24 hours TTL for state
    data_ttl=86400,        # 24 hours TTL for data (context)
    key_builder=DefaultKeyBuilder(prefix=REDIS_PREFIX, with_bot_id=True)  # use a prefix for keys, include bot id to avoid collisions
)
dispatcher = Dispatcher(storage=storage)

# Import routers from handlers and include them in the dispatcher
from handlers import main_menu, option1, option2, option3, option4
dispatcher.include_router(main_menu.router)
dispatcher.include_router(option1.router)
dispatcher.include_router(option2.router)
dispatcher.include_router(option3.router)
dispatcher.include_router(option4.router)

from handlers import basic_cmds
dispatcher.include_router(basic_cmds.router)

# Entry point: start polling updates
async def main():
    # On startup, you could set bot commands or other initialization if needed.
    logging.info("Starting bot...")
    await dispatcher.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
