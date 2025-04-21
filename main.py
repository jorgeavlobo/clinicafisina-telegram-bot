#!/usr/bin/env python3
"""
main.py — Clínica Fisina Telegram bot
• Aiogram v3 (webhook mode)
• Redis FSM storage
• PostgreSQL structured logging
• Runs behind Nginx, proxied to 127.0.0.1:8443
"""

# ────────────────────────── stdlib ──────────────────────────
import asyncio
import logging
import os
from functools import wraps
from typing import Any, Callable, Coroutine

# ───────────────────────── third‑party ──────────────────────
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler,
    setup_application,
)
from redis.asyncio import Redis
from dotenv import load_dotenv

# ─────────────────────────── local ──────────────────────────
from infra.db_async import DBPools
from infra.db_logger import pg_handler

# ──────────────────── environment / settings ────────────────
load_dotenv()

BOT_TOKEN    = os.getenv("TELEGRAM_TOKEN")               # required
DOMAIN       = os.getenv("DOMAIN", "telegram.fisina.pt") # used for webhook URL
WEBHOOK_PORT = int(os.getenv("WEBAPP_PORT", 8443))       # container port

# Redis
REDIS_HOST   = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT   = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB     = int(os.getenv("REDIS_DB", 0))
REDIS_PREFIX = os.getenv("REDIS_PREFIX", "fsm")

# ────────────────────────── logging ─────────────────────────
logging.basicConfig(
    level=logging.INFO,
    handlers=[pg_handler, logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# ───────────────── helper decorator (startup steps) ─────────
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

# ────────────────────────── init helpers ────────────────────
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

# ─────────────── custom error‑logging middleware ────────────
class LogErrorsMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception:
            telegram_uid = getattr(event, "from_user", None)
            telegram_uid = telegram_uid.id if telegram_uid else None

            chat_id: Any = None
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
                },
            )
            raise

# ─────────────────────── routers import ─────────────────────
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

# ───────────────────── aiohttp app factory ──────────────────
async def build_app() -> web.Application:
    """Create aiohttp.web.Application with Aiogram dispatcher attached."""
    await init_db_pools()
    storage = await init_storage()
    bot     = await init_bot()

    # Dispatcher with Redis FSM storage
    dp = Dispatcher(storage=storage)
    dp.message.middleware(LogErrorsMiddleware())
    dp.callback_query.middleware(LogErrorsMiddleware())

    for r in ROUTERS:
        dp.include_router(r)
        logger.info(f"✅ Router registered: {r.__module__}", extra={"is_system": True})

    # ─── webhook registration on Aiogram side ───────────────
    webhook_path = f"/{BOT_TOKEN}"
    webhook_url  = f"https://{DOMAIN}{webhook_path}"
    await bot.set_webhook(webhook_url)
    logger.info(f"✅ Webhook set to {webhook_url}", extra={"is_system": True})

    # ─── aiohttp application wiring ─────────────────────────
    app = web.Application()

    # Route POST <webhook_path> → dispatcher
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    ).register(app, path=webhook_path)

    # Graceful shutdown: close pools & storage
    async def on_shutdown(_: web.AppRunner) -> None:
        await dp.storage.close()
        await dp.storage.wait_closed()
        await DBPools.close()
        await bot.session.close()
        logger.info("👋 Bot shutdown", extra={"is_system": True})

    app.on_shutdown.append(on_shutdown)

    # Let Aiogram add a startup task that notifies middlewares etc.
    setup_application(app, dp, bot=bot)

    return app

# ───────────────────────── main() ───────────────────────────
def main() -> None:
    """Entrypoint compatible with Docker CMD."""
    app = asyncio.run(build_app())

    runner = web.AppRunner(app)
    asyncio.run(runner.setup())

    site = web.TCPSite(
        runner,
        host="0.0.0.0",
        port=WEBHOOK_PORT,  # default 8443
    )
    logger.info(f"🚀 Webhook server ready on 0.0.0.0:{WEBHOOK_PORT}", extra={"is_system": True})
    asyncio.run(site.start())

    # Keep the loop alive forever
    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        pass

# ────────────────────────── run ─────────────────────────────
if __name__ == "__main__":  # pragma: no cover
    main()
