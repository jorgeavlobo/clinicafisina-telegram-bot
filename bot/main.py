# bot/main.py
"""
Entry point da aplicação Telegram-bot (webhook • aiohttp).

• Liga pool PostgreSQL (singleton)
• Cria Bot  +  Redis-FSM
• Regista middlewares e routers
• Expõe /healthz  e  /ping
• Webhook server + graceful-shutdown
"""

from __future__ import annotations
import asyncio
import logging
import signal
from contextlib import suppress

from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.middleware.base import BaseMiddleware

from bot.config import (
    BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PATH, SECRET_TOKEN, WEBAPP_PORT, LOG_LEVEL,
    REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PREFIX,
)
from bot.middlewares.role_check import RoleCheckMiddleware
from bot.middlewares.active_menu_middleware import ActiveMenuMiddleware
from bot.database import connection                       # ← pool singleton

# ───────────────────────────  TAP DE DEPURAÇÃO  ────────────────────────────
class DebugTapMiddleware(BaseMiddleware):
    """
    Loga *todas* as mensagens que entram no dispatcher.
    Não altera a update – apenas passa ao próximo handler.
    """
    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            logging.warning("▼ RAW MESSAGE from %s: %s",
                            event.from_user.id, repr(event.text))
        return await handler(event, data)

# ────────────────────────────────────────────────────────────────────────────
async def main() -> None:
    # logging base
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    # ───── Bot + pool Postgres ─────
    bot = Bot(token=BOT_TOKEN, parse_mode=None)
    bot.pg_pool = await connection.init()          # anexa pool ao Bot

    # ───── Redis-FSM ─────
    storage = RedisStorage.from_url(
        f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
        key_builder=DefaultKeyBuilder(prefix=REDIS_PREFIX),
    )
    dp = Dispatcher(bot=bot, storage=storage)

    # ───── Middlewares (ordem importa) ─────
    dp.message.outer_middleware(DebugTapMiddleware())      # <- tap
    dp.callback_query.outer_middleware(DebugTapMiddleware())

    dp.message.outer_middleware(RoleCheckMiddleware())
    dp.callback_query.outer_middleware(RoleCheckMiddleware())

    dp.callback_query.outer_middleware(ActiveMenuMiddleware())

    # ───── Routers ─────
    from bot.handlers import register_routers
    register_routers(dp)

    # ───── Webhook ─────
    await bot.set_webhook(WEBHOOK_URL, secret_token=SECRET_TOKEN)
    logging.info("Webhook registado em %s", WEBHOOK_URL)

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=SECRET_TOKEN)\
        .register(app, path=WEBHOOK_PATH)
    setup_application(app, dp)

    # endpoints simples
    app.router.add_get("/healthz", lambda r: web.Response(text="OK"))
    app.router.add_get("/ping",    lambda r: web.Response(text="Pong"))

    # ───── arrancar servidor aiohttp ─────
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, host="0.0.0.0", port=WEBAPP_PORT).start()
    logging.info("🚀 Webhook server ativo em 0.0.0.0:%s", WEBAPP_PORT)

    # ───── graceful-shutdown ─────
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)

    try:
        await stop_event.wait()
    finally:
        logging.info("Iniciar shutdown…")
        await bot.delete_webhook(drop_pending_updates=True)
        await runner.cleanup()
        await connection.close()
        await bot.session.close()
        await storage.close()
        logging.info("Shutdown concluído.")

# ponto de arranque
if __name__ == "__main__":
    asyncio.run(main())
