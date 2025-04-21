#!/usr/bin/env python3
"""
main.py — Clínica Fisina Telegram bot
• Aiogram v3.3+ (ApplicationBuilder, webhook mode)
• Redis FSM storage
• PostgreSQL structured logging
• Exposes /healthz and /ping
• Persistent webhook setup + Nginx proxy at 127.0.0.1:8444
"""

# ─────────────── stdlib ───────────────
import asyncio
import logging
import os
from functools import wraps
from typing import Any, Callable, Coroutine

# ──────────── third-party ─────────────
from aiohttp import web
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram import Application, ApplicationBuilder
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from redis.asyncio import Redis
from dotenv import load_dotenv

# ──────────────── local ───────────────
from infra.db_async import DBPools
from infra.db_logger import pg_handler

# ─────────────── Settings ───────────────
load_dotenv()

BOT_TOKEN     = os.getenv("TELEGRAM_TOKEN")
SECRET_TOKEN  = os.getenv("TELEGRAM_SECRET_TOKEN")
DOMAIN        = os.getenv("DOMAIN", "telegram.fisina.pt")
WEBHOOK_PORT  = int(os.getenv("WEBAPP_PORT", 8444))
WEBHOOK_PATH  = f"/{BOT_TOKEN}"
WEBHOOK_URL   = f"https://{DOMAIN}{WEBHOOK_PATH}"

REDIS_HOST    = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT    = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB      = int(os.getenv("REDIS_DB", 0))
REDIS_PREFIX  = os.getenv("REDIS_PREFIX", "fsm")

# ─────────────── Logging ────────────────
logging.basicConfig(
    level=logging.INFO,
    handlers=[pg_handler, logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ────────── Helper Decorator ─────────────
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

# ─────────────── Init ────────────────
@log_and_reraise("DB pool init")
async def init_db_pools() -> None:
    await DBPools.init()
    logger.info("✅ DB pools initialised", extra={"is_system": True})

@log_and_reraise("Redis FSM init")
async def init_storage() -> RedisStorage:
    redis = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    storage = RedisStorage(
        redis=redis,
        state_ttl=86400,
        data_ttl=86400,
        key_builder=DefaultKeyBuilder(prefix=REDIS_PREFIX, with_bot_id=True),
    )
    logger.info("✅ Redis FSM storage ready", extra={"is_system": True})
    return storage

# ─────── Middleware (Error Logging) ───────
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
                chat_id = message.chat.id

            logger.exception(
                "Unhandled exception inside handler",
                extra={
                    "telegram_user_id": telegram_uid,
                    "chat_id": chat_id,
                    "is_system": False,
                },
            )
            raise

# ─────────── Router imports ───────────
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

# ─────── aiohttp + ApplicationBuilder ───────
async def build_app() -> web.Application:
    await init_db_pools()
    storage = await init_storage()

    app = ApplicationBuilder() \
        .token(BOT_TOKEN) \
        .parse_mode(ParseMode.HTML) \
        .secret_token(SECRET_TOKEN) \
        .webhook_path(WEBHOOK_PATH) \
        .webhook_url(WEBHOOK_URL) \
        .skip_updates(False) \
        .storage(storage) \
        .build()

    app.bot_info = await app.bot.me()

    app.message.middleware(LogErrorsMiddleware())
    app.callback_query.middleware(LogErrorsMiddleware())

    for r in ROUTERS:
        name = getattr(r, "__module__", str(r))
        app.include_router(r)
        logger.info(f"✅ Router registered: {name}", extra={"is_system": True})

    # ───── aiohttp Web Application ─────
    aiohttp_app = web.Application()
    SimpleRequestHandler(
        dispatcher=app,
        bot=app.bot,
    ).register(aiohttp_app, path=WEBHOOK_PATH)

    aiohttp_app.router.add_get("/healthz", lambda _: web.Response(text="OK"))
    aiohttp_app.router.add_get("/ping", lambda _: web.Response(text="pong"))

    async def on_shutdown(_: web.AppRunner) -> None:
        await app.shutdown()
        await app.bot.session.close()
        await DBPools.close()
        logger.info("👋 Bot shutdown", extra={"is_system": True})

    aiohttp_app.on_shutdown.append(on_shutdown)
    setup_application(aiohttp_app, app, bot=app.bot)

    return aiohttp_app

# ───────────── Entrypoint ─────────────
def main() -> None:
    async def runner():
        app = await build_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", WEBHOOK_PORT)
        await site.start()
        logger.info(f"🚀 Webhook server ready on 0.0.0.0:{WEBHOOK_PORT}", extra={"is_system": True})
        while True:
            await asyncio.sleep(3600)

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        logger.info("👋 Interrupted by user", extra={"is_system": True})

if __name__ == "__main__":
    main()
