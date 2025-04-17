"""
main.py  –  entry point for aiogram v3 bot with Redis FSM
           and PostgreSQL logging.
"""

import os
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from redis.asyncio import Redis
from dotenv import load_dotenv

from infra.db_async import DBPools          # NEW
from infra.db_logger import pg_handler      # NEW

# --------------------------------------------------------------------------- #
#  Environment
# --------------------------------------------------------------------------- #
load_dotenv()

BOT_TOKEN    = os.getenv("TELEGRAM_TOKEN")          # ← keep existing env name
REDIS_HOST   = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT   = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB     = int(os.getenv("REDIS_DB", 0))
REDIS_PREFIX = os.getenv("REDIS_PREFIX", "fsm")

# --------------------------------------------------------------------------- #
#  Logging: send everything ≥INFO to PostgreSQL, errors still reach stderr
# --------------------------------------------------------------------------- #
logging.basicConfig(
    level=logging.INFO,
    handlers=[pg_handler, logging.StreamHandler()]   # keep console for errors
)

# --------------------------------------------------------------------------- #
#  Bot & FSM storage
# --------------------------------------------------------------------------- #
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

redis = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
storage = RedisStorage(
    redis=redis,
    state_ttl=86400,
    data_ttl=86400,
    key_builder=DefaultKeyBuilder(prefix=REDIS_PREFIX, with_bot_id=True),
)

dispatcher = Dispatcher(storage=storage)

# Routers ------------------------------------------------------------------- #
from handlers import (
    main_menu,
    option1,
    option2,
    option3,
    option4,
    basic_cmds,
)

for r in (
    main_menu.router,
    option1.router,
    option2.router,
    option3.router,
    option4.router,
    basic_cmds.router,
):
    dispatcher.include_router(r)

# --------------------------------------------------------------------------- #
#  Startup / shutdown
# --------------------------------------------------------------------------- #
async def main() -> None:
    # DB pools
    await DBPools.init()
    logging.info("Starting bot…")

    try:
        await dispatcher.start_polling(bot)
    finally:
        await DBPools.close()

if __name__ == "__main__":
    asyncio.run(main())
