"""
main.py — entry‑point for aiogram v3 bot (Redis FSM + PostgreSQL logging)
with granular error logging.
"""

import asyncio
import logging
import os
from functools import wraps
from typing import Callable, Coroutine, Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aiogram.dispatcher.middlewares.error import ErrorMiddleware
from redis.asyncio import Redis
from dotenv import load_dotenv

from infra.db_async import DBPools
from infra.db_logger import pg_handler

# --------------------------------------------------------------------------- #
#  ENV
# --------------------------------------------------------------------------- #
load_dotenv()

BOT_TOKEN    = os.getenv("TELEGRAM_TOKEN")
REDIS_HOST   = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT   = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB     = int(os.getenv("REDIS_DB", 0))
REDIS_PREFIX = os.getenv("REDIS_PREFIX", "fsm")

# --------------------------------------------------------------------------- #
#  LOGGING
# --------------------------------------------------------------------------- #
logging.basicConfig(
    level=logging.INFO,
    handlers=[pg_handler, logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  Helper decorator to standardise error logging
# --------------------------------------------------------------------------- #
def log_and_reraise(step: str) -> Callable[[Callable[..., Coroutine]], Callable[..., Coroutine]]:
    """
    Decorator: log exception with context `step` and re‑raise.
    """
    def decorator(func: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception:
                logger.exception(
                    f"❌ Exception during {step}",
                    extra={"is_system": True}
                )
                raise
        return wrapper
    return decorator

# --------------------------------------------------------------------------- #
#  Init sections wrapped with logging
# --------------------------------------------------------------------------- #
@log_and_reraise("DB pool init")
async def init_db_pools() -> None:
    await DBPools.init()
    logger.info("✅ DB pools initialised", extra={"is_system": True})

@log_and_reraise("Redis storage init")
async def init_storage() -> RedisStorage:
    redis = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    storage = RedisStorage(
        redis=redis,
        state_ttl=86400,
        data_ttl=86400,
        key_builder=DefaultKeyBuilder(prefix=REDIS_PREFIX, with_bot_id=True),
    )
    logger.info("✅ Redis storage ready", extra={"is_system": True})
    return storage

@log_and_reraise("Bot init")
async def init_bot() -> Bot:
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    logger.info("✅ Bot instance created", extra={"is_system": True})
    return bot

# --------------------------------------------------------------------------- #
#  Error middleware to log every handler exception with user / chat ids
# --------------------------------------------------------------------------- #
class LogErrorsMiddleware(ErrorMiddleware):
    async def on_error(
        self,
        event,
        error: Exception,
        data: dict[str, Any],
    ) -> None:
        # attempt to extract IDs
        telegram_uid = None
        chat_id = None

        if hasattr(event, "from_user"):
            telegram_uid = event.from_user.id
        if hasattr(event, "chat"):
            chat_id = event.chat.id
        elif hasattr(event, "message") and event.message:
            chat_id = event.message.chat.id

        logger.exception(
            "Unhandled exception inside handler",
            extra={
                "telegram_user_id": telegram_uid,
                "chat_id": chat_id,
                "is_system": False,
            }
        )

# --------------------------------------------------------------------------- #
#  Routers
# --------------------------------------------------------------------------- #
from handlers import (
    main_menu,
    option1,
    option2,
    option3,
    option4,
    basic_cmds,
)

ROUTERS = (
    main_menu.router,
    option1.router,
    option2.router,
    option3.router,
    option4.router,
    basic_cmds.router,
)

# --------------------------------------------------------------------------- #
#  Main coroutine
# --------------------------------------------------------------------------- #
async def main() -> None:
    await init_db_pools()
    storage = await init_storage()
    bot     = await init_bot()

    dispatcher = Dispatcher(storage=storage)
    dispatcher.message.middleware(LogErrorsMiddleware())
    dispatcher.callback_query.middleware(LogErrorsMiddleware())

    # router registration
    for r in ROUTERS:
        try:
            dispatcher.include_router(r)
            logger.info(
                f"✅ Router registered: {r.__module__}",
                extra={"is_system": True}
            )
        except Exception:
            logger.exception(
                f"❌ Failed to register router {r}",
                extra={"is_system": True}
            )
            raise

    logger.info("🚀 Starting polling", extra={"is_system": True})
    try:
        await dispatcher.start_polling(bot)
    finally:
        await DBPools.close()
        logger.info("👋 Bot shutdown", extra={"is_system": True})

# --------------------------------------------------------------------------- #
#  Entrypoint
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user", extra={"is_system": True})
