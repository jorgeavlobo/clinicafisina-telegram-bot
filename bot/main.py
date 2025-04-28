# bot/main.py
"""
Entry point for the Telegram bot application.

- Initializes bot, middlewares, and routers
- Sets up webhook server using aiohttp
- Handles graceful shutdown
"""

import asyncio
import logging
import signal
from contextlib import suppress

from aiohttp import web
from aiogram import Bot, Dispatcher, exceptions
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from bot.config import (
    BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PATH, SECRET_TOKEN, WEBAPP_PORT, LOG_LEVEL,
    REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PREFIX,
)
from bot.middlewares.role_check import RoleCheckMiddleware
from bot.middlewares.active_menu_middleware import ActiveMenuMiddleware


async def main() -> None:
    """Main async entrypoint for the bot lifecycle."""

    # ─────────── Logging ───────────
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    # ─────────── Bot & Storage ───────────
    bot = Bot(token=BOT_TOKEN, parse_mode=None)

    redis_dsn = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    storage = RedisStorage.from_url(
        redis_dsn,
        key_builder=DefaultKeyBuilder(prefix=REDIS_PREFIX),
    )

    dp = Dispatcher(bot=bot, storage=storage)

    # ─────────── Middlewares ───────────
    dp.message.outer_middleware(RoleCheckMiddleware())
    dp.callback_query.outer_middleware(RoleCheckMiddleware())
    dp.callback_query.outer_middleware(ActiveMenuMiddleware())

    # ─────────── Routers ───────────
    from bot.handlers import register_routers  # Late import to avoid circular imports
    register_routers(dp)

    # ─────────── Webhook Setup ───────────
    await bot.set_webhook(WEBHOOK_URL, secret_token=SECRET_TOKEN)
    logging.info("Webhook registado em %s", WEBHOOK_URL)

    app = web.Application()
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=SECRET_TOKEN,
    ).register(app, path=WEBHOOK_PATH)

    setup_application(app, dp)

    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, host="0.0.0.0", port=WEBAPP_PORT).start()
    logging.info("🚀 Webhook server ativo em 0.0.0.0:%s", WEBAPP_PORT)

    # ─────────── Graceful Shutdown ───────────
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)

    try:
        await stop_event.wait()
    finally:
        logging.info("Iniciar shutdown...")
        await bot.delete_webhook(drop_pending_updates=True)
        await runner.cleanup()
        await bot.session.close()
        await storage.close()
        logging.info("Shutdown concluído com sucesso.")


if __name__ == "__main__":
    asyncio.run(main())
