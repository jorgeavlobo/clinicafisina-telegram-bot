"""
main.py — entry‑point for the Clínica Fisina Telegram bot
(aiogram v3, Redis FSM, PostgreSQL logging) with custom error middleware.
Runs in webhook mode on port 8443 behind Nginx.
"""

import asyncio
import logging
import os
from functools import wraps
from typing import Any, Callable, Coroutine

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from dotenv import load_dotenv
from redis.asyncio import Redis

from infra.db_async import DBPools
from infra.db_logger import pg_handler

# ─── Environment ────────────────────────────────────────────────────────────
load_dotenv()
BOT_TOKEN    = os.getenv("TELEGRAM_TOKEN")
REDIS_HOST   = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT   = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB     = int(os.getenv("REDIS_DB", 0))
REDIS_PREFIX = os.getenv("REDIS_PREFIX", "fsm")
DOMAIN       = os.getenv("DOMAIN", "telegram.fisina.pt")  # for webhook URL

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    handlers=[pg_handler, logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ─── Helper decorator — log + re‑raise during startup steps ─────────────────
def log_and_reraise(step: str) -> Callable[[Callable[..., Coroutine]], Callable[..., Coroutine]]:
    def decorator(func: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception:
                logger.exception(f"❌ Exception during {step}", extra={"is_system": True})
                raise
        return wrapper
    return decorator

# ─── Startup helpers ───────────────────────────────────────────────────────
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

# ─── Custom error‑logging middleware ────────────────────────────────────────
class LogErrorsMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception:
            telegram_uid = getattr(event, "from_user", None)
            telegram_uid = telegram_uid.id if telegram_uid else None
            chat_id = None
            if hasattr(event, "chat") and event.chat:
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
            raise

# ─── Routers ────────────────────────────────────────────────────────────────
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

# ─── Build the aiohttp application ──────────────────────────────────────────
async def build_app() -> web.Application:
    # Initialize infra
    await init_db_pools()
    storage = await init_storage()
    bot     = await init_bot()

    # Dispatcher + middleware
    dispatcher = Dispatcher(storage=storage)
    dispatcher.message.middleware(LogErrorsMiddleware())
    dispatcher.callback_query.middleware(LogErrorsMiddleware())

    # Register your routers
    for r in ROUTERS:
        try:
            dispatcher.include_router(r)
            logger.info(f"✅ Router registered: {r.__module__}", extra={"is_system": True})
        except Exception:
            logger.exception(f"❌ Failed to register router {r}", extra={"is_system": True})
            raise

    # Set the webhook
    webhook_path = f"/{BOT_TOKEN}"
    webhook_url  = f"https://{DOMAIN}{webhook_path}"
    await bot.set_webhook(webhook_url)
    logger.info(f"✅ Webhook set to {webhook_url}", extra={"is_system": True})

    # Create aiohttp app, wire aiogram startup/shutdown hooks
    app = web.Application()
    setup_application(app, dispatcher)

    # Register Telegram → dispatcher request handler
    SimpleRequestHandler(
        dispatcher=dispatcher,
        bot=bot,
        secret_token=None,      # or set your own secret‑token header here
    ).register(app, path=webhook_path)

    # Clean up DB pools on shutdown
    async def on_shutdown(app: web.Application):
        await DBPools.close()
        logger.info("👋 Bot shutdown", extra={"is_system": True})
    app.on_shutdown.append(on_shutdown)

    logger.info("🚀 Webhook server ready", extra={"is_system": True})
    return app

# ─── Entrypoint ─────────────────────────────────────────────────────────────
def main() -> None:
    app = asyncio.run(build_app())
    web.run_app(app, host="0.0.0.0", port=8443)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Interrupted by user", extra={"is_system": True})
