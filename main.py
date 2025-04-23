"""
Clínica Fisina – Telegram Bot
© 2024 Jorge AVLobo
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from contextlib import suppress
from datetime import timedelta

from aiogram import Bot, Dispatcher, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.redis import RedisStorage
from aiogram import BaseMiddleware
from aiogram import ThrottlingMiddleware
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

import redis.asyncio as aioredis

# ────────────────────── Settings & Guards ──────────────────────

from dotenv import load_dotenv

load_dotenv()

REQUIRED_ENV = [
    "TELEGRAM_TOKEN",
    "TELEGRAM_SECRET_TOKEN",
    "WEBHOOK_URL",
    "REDIS_HOST",
]

_missing = [var for var in REQUIRED_ENV if not os.getenv(var)]
if _missing:
    raise RuntimeError(f"Missing env vars: {', '.join(_missing)}")

BOT_TOKEN      = os.environ["TELEGRAM_TOKEN"]
SECRET_TOKEN   = os.environ["TELEGRAM_SECRET_TOKEN"]
WEBHOOK_URL    = os.environ["WEBHOOK_URL"]
REDIS_HOST     = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT     = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB       = int(os.getenv("REDIS_DB", "1"))

# ────────────────────── Logging ──────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# PostgreSQL handler
from infra.db_logger import setup_pg_logging

setup_pg_logging()

# ────────────────────── Database pools ──────────────────────

from infra.db_async import DBPools

# ────────────────────── Bot & Dispatcher ──────────────────────

redis_pool = aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")

bot = Bot(
    BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

dp = Dispatcher(storage=RedisStorage(redis_pool))

# Routers
from handlers import basic_cmds, main_menu, option1, option2, option3, option4

for rtr in (
    basic_cmds.router,
    main_menu.router,
    option1.router,
    option2.router,
    option3.router,
    option4.router,
):
    dp.include_router(rtr)

# ────────────────────── Middleware ──────────────────────

class ErrorReportingMiddleware(BaseMiddleware):
    """Loga e devolve mensagem genérica ao utilizador."""

    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except TelegramBadRequest as e:
            logging.warning("TelegramBadRequest ignored: %s", e)
        except Exception as e:  # noqa: BLE001
            logging.exception("Unhandled error")
            if isinstance(event, types.Message):
                await event.answer("⚠️ Ocorreu um erro inesperado :(")

dp.message.middleware(ErrorReportingMiddleware())
dp.message.middleware(ThrottlingMiddleware(rate_limit=1.0))  # anti-flood global

# ────────────────────── Webhook self-check ──────────────────────

async def webhook_self_check():
    while True:
        await asyncio.sleep(3600)  # 1h
        try:
            info = await bot.get_webhook_info()
            if info.url != WEBHOOK_URL:
                await bot.set_webhook(WEBHOOK_URL, secret_token=SECRET_TOKEN)
                logging.warning("Webhook URL was missing – reinstated")
        except Exception:  # noqa: BLE001
            logging.exception("Webhook self-check failed")

# ────────────────────── Startup / Shutdown ──────────────────────

async def on_startup() -> None:
    await DBPools.init()
    await bot.delete_webhook(drop_pending_updates=False)
    await bot.set_webhook(WEBHOOK_URL, secret_token=SECRET_TOKEN)
    asyncio.create_task(webhook_self_check())
    logging.info("Bot started")

async def on_shutdown() -> None:
    logging.info("Shutting down…")
    await bot.session.close()
    await DBPools.close()
    await redis_pool.close()

# ────────────────────── AIOHTTP server (for production) ──────────────────────

from aiohttp import web

def create_app() -> web.Application:
    """Factory para gunicorn / uvicorn workers."""
    app = web.Application()

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=SECRET_TOKEN,
        handle_in_background=True,
    ).register(app, path="/telegram")

    app.on_startup.append(lambda _: on_startup())
    app.on_cleanup.append(lambda _: on_shutdown())
    return app

# ────────────────────── Dev helper (polling) ──────────────────────

async def _dev_polling():
    await on_startup()
    await dp.start_polling(bot)

# ────────────────────── Entrypoint ──────────────────────

if __name__ == "__main__":
    mode = os.getenv("BOT_MODE", "polling")
    if mode == "webhook":  # launch aiohttp server
        import uvicorn
        uvicorn.run(
            "main:create_app",
            factory=True,
            host="0.0.0.0",
            port=int(os.getenv("PORT", 8080)),
        )
    else:  # default to polling for local dev
        try:
            asyncio.run(_dev_polling())
        except (KeyboardInterrupt, SystemExit):
            logging.info("Interrupted by user")
