#!/usr/bin/env python3
"""
main.py — Clínica Fisina Telegram bot
• Aiogram v3.20 (Dispatcher + webhook)
• Redis FSM storage
• PostgreSQL structured logging
• Webhook proxy at 127.0.0.1:8444 via Nginx
• Health + Ping endpoints
• Periodic webhook self-check
• Persistent command menu
"""

# ─────────────── stdlib ───────────────
import asyncio
import logging
import os
from functools import wraps
from typing import Any, Callable, Coroutine

# ──────────── third-party ─────────────
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
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

# ────── Decorator for startup logging ──────
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

@log_and_reraise("Bot init")
async def init_bot() -> Bot:
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    me = await bot.get_me()
    logger.info(f"✅ Logged in as @{me.username} ({me.id})", extra={"is_system": True})

    # Webhook + Command registration
    await bot.set_webhook(
        url=WEBHOOK_URL,
        secret_token=SECRET_TOKEN,
        drop_pending_updates=False,
    )
    logger.info(f"✅ Webhook set to {WEBHOOK_URL}", extra={"is_system": True})

    await bot.set_my_commands([
        BotCommand(command="start",    description="📍 Início"),
        BotCommand(command="services", description="💆 Serviços disponíveis"),
        BotCommand(command="team",     description="👥 Equipa clínica"),
        BotCommand(command="contacts", description="📞 Contactos e localização"),
    ])
    logger.info("✅ Bot commands registered", extra={"is_system": True})

    return bot

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

# ─────── aiohttp App Factory ───────
async def build_app() -> web.Application:
    await init_db_pools()
    storage = await init_storage()
    bot     = await init_bot()

    dispatcher = Dispatcher(storage=storage)
    dispatcher.message.middleware(LogErrorsMiddleware())
    dispatcher.callback_query.middleware(LogErrorsMiddleware())

    for r in ROUTERS:
        dispatcher.include_router(r)

        # Try router.name → fallback to __module__ or repr
        router_name = getattr(r, "name", None) or getattr(r, "__module__", None) or repr(r)

        logger.info(f"✅ Router registered: {router_name}", extra={"is_system": True})

    app = web.Application()

    # Webhook path
    SimpleRequestHandler(dispatcher=dispatcher, bot=bot).register(app, path=WEBHOOK_PATH)

    # Health checks
    app.router.add_get("/healthz", lambda _: web.Response(text="OK"))
    app.router.add_get("/ping",    lambda _: web.Response(text="pong"))

    # Periodic webhook validation
    async def periodic_self_check():
        while True:
            try:
                info = await bot.get_webhook_info()
                logger.info(f"📡 Webhook info: {info.url}", extra={"is_system": True})
            except Exception as e:
                logger.warning(f"⚠️ Webhook self-check failed: {e}")
            await asyncio.sleep(3600)

    async def on_startup(_: web.AppRunner) -> None:
        asyncio.create_task(periodic_self_check())

    async def on_shutdown(_: web.AppRunner) -> None:
        await dispatcher.storage.close()
        await dispatcher.storage.wait_closed()
        await DBPools.close()
        await bot.session.close()
        logger.info("👋 Bot shutdown", extra={"is_system": True})

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    setup_application(app, dispatcher, bot=bot)
    return app

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

if __name__ == "__main__":  # pragma: no cover
    main()
