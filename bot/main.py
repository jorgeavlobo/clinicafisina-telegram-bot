# bot/main.py
import asyncio
import logging
import signal
from contextlib import suppress

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler,
    setup_application,
)
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder

from bot.config import (
    # Telegram / webhook
    BOT_TOKEN,
    WEBHOOK_URL,
    WEBHOOK_PATH,
    SECRET_TOKEN,
    WEBAPP_PORT,
    LOG_LEVEL,
    # Redis FSM
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PREFIX,
)
from bot.middlewares.role_check import RoleCheckMiddleware


async def run() -> None:
    # ─────────── Log global ───────────
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    # ─────────── Bot + RedisStorage ───────────
    bot = Bot(token=BOT_TOKEN, parse_mode=None)

    redis_dsn = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    storage = RedisStorage.from_url(
        redis_dsn,
        key_builder=DefaultKeyBuilder(prefix=REDIS_PREFIX),
    )

    dp = Dispatcher(bot=bot, storage=storage)

    # ─────────── Middleware de roles (ESC. EXTERNO) ───────────
    role_mw = RoleCheckMiddleware()
    dp.message.outer_middleware(role_mw)
    dp.callback_query.outer_middleware(role_mw)
    # se mais tipos de update forem usados, acrescentar:
    #   dp.chat_member.outer_middleware(role_mw)  etc.

    # ─────────── Routers ───────────
    from bot.handlers import register_routers  # import tardio p/ evitar ciclos
    register_routers(dp)

    # ─────────── Registar / actualizar webhook ───────────
    await bot.set_webhook(WEBHOOK_URL, secret_token=SECRET_TOKEN)
    logging.info("Webhook registado em %s", WEBHOOK_URL)

    # ─────────── Aiohttp app + handler ───────────
    app = web.Application()
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=SECRET_TOKEN,
    ).register(app, path=WEBHOOK_PATH)

    # faz attach de on_startup / on_shutdown ao app
    setup_application(app, dp)

    # ─────────── Servidor HTTP interno ───────────
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, host="0.0.0.0", port=WEBAPP_PORT).start()
    logging.info("🚀 Webhook server em 0.0.0.0:%s", WEBAPP_PORT)

    # ─────────── Espera por SIGINT / SIGTERM ───────────
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)

    try:
        await stop_event.wait()
    finally:
        # ─────────── Shutdown limpo ───────────
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("Webhook removido antes de sair.")
        await runner.cleanup()
        await bot.session.close()
        await storage.close()   # fecha ligação Redis


if __name__ == "__main__":
    asyncio.run(run())
