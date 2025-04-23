# bot/main.py
import asyncio
import logging
import signal
from contextlib import suppress

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from bot.config import (
    BOT_TOKEN, LOG_LEVEL, WEBAPP_PORT,
    WEBHOOK_URL, WEBHOOK_PATH, SECRET_TOKEN,
)
from bot.middlewares.role_check import RoleCheckMiddleware


async def run() -> None:
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    bot = Bot(token=BOT_TOKEN, parse_mode=None)

    # 1. Dispatcher
    dp = Dispatcher(bot=bot)

    # 2. Middlewares (ANTES de incluir routers!)
    role_mw = RoleCheckMiddleware()
    dp.message.middleware(role_mw)
    dp.callback_query.middleware(role_mw)
    # se usares outros tipos de update, acrescenta-os aqui

    # 3. Routers
    from bot.handlers import register_routers
    register_routers(dp)

    # 4. Webhook
    await bot.set_webhook(WEBHOOK_URL, secret_token=SECRET_TOKEN)
    logging.info("Webhook registado em %s", WEBHOOK_URL)

    # 5. Aiohttp app
    app = web.Application()
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=SECRET_TOKEN,
    ).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp)

    # 6. Servidor HTTP interno
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", WEBAPP_PORT).start()
    logging.info("🚀 Webhook server listening on 0.0.0.0:%s", WEBAPP_PORT)

    # 7. Espera por SIGINT/SIGTERM
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)

    try:
        await stop_event.wait()
    finally:
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("Webhook removido antes de sair.")
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run())
