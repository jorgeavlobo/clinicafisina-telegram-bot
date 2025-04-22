#!/usr/bin/env python3
"""Clínica Fisina Telegram bot – entrypoint
Este ficheiro arranca a aplicação, configura webhook, storage Redis,
logging SQL e regista comandos.

⚠️  Requisitos:
    • Variáveis de ambiente (.env ou no host)
    • PostgreSQL (DBPools)
    • Redis em execução
    • Nginx proxy 127.0.0.1:8444
"""

import asyncio, logging, os, sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from dotenv import load_dotenv

from infra.db_async import DBPools
from infra.db_logger import pg_handler
from shared.redis_fsm import build_redis
from shared.config import settings
from shared.dal import DAL
from handlers import all_routers
from states.expire_middleware import ExpireInlineMiddleware

load_dotenv()

logging.basicConfig(level=logging.INFO,
                    handlers=[pg_handler, logging.StreamHandler()])
log = logging.getLogger(__name__)


async def init_bot() -> Bot:
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    me = await bot.get_me()
    log.info("✅ Logged in as @%s (%s)", me.username, me.id, extra={"is_system": True})

    # webhook (idempotente)
    await bot.set_webhook(
        url=settings.WEBHOOK_URL,
        secret_token=settings.SECRET_TOKEN,
        drop_pending_updates=False,
    )
    log.info("✅ Webhook %s", settings.WEBHOOK_URL)

    await bot.set_my_commands([
        BotCommand(command="start",    description="📍 Início"),
        BotCommand(command="services", description="💆 Serviços"),
        BotCommand(command="team",     description="👥 Equipa"),
        BotCommand(command="contacts", description="📞 Contactos"),
    ])
    return bot


async def build_app() -> web.Application:
    await DBPools.init()

    redis = build_redis()
    storage = RedisStorage(
        redis=redis,
        state_ttl=86400,
        data_ttl=86400,
        key_builder=DefaultKeyBuilder(prefix=settings.REDIS_PREFIX, with_bot_id=True),
    )

    bot = await init_bot()
    dispatcher = Dispatcher(storage=storage)
    dispatcher.message.middleware(ExpireInlineMiddleware())
    dispatcher.callback_query.middleware(ExpireInlineMiddleware())

    for r in all_routers:
        dispatcher.include_router(r)
        log.info("✅ Router registered: %s", getattr(r, "name", r.__module__))

    app = web.Application()
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
    SimpleRequestHandler(dispatcher=dispatcher, bot=bot).register(app, path=settings.WEBHOOK_PATH)

    app.router.add_get("/healthz", lambda _: web.Response(text="OK"))
    app.router.add_get("/ping", lambda _: web.Response(text="pong"))

    async def periodic():
        while True:
            await asyncio.sleep(3600)
            try:
                info = await bot.get_webhook_info()
                if info.url != settings.WEBHOOK_URL:
                    log.warning("Webhook drift! Resetting…")
                    await bot.set_webhook(url=settings.WEBHOOK_URL, secret_token=settings.SECRET_TOKEN)
            except Exception as e:
                log.exception("Webhook self‑check failed: %s", e)

    async def on_startup(_):
        asyncio.create_task(periodic())

    async def on_shutdown(_):
        await dispatcher.fsm.storage.close()
        await dispatcher.fsm.storage.wait_closed()
        await DBPools.close()
        await bot.session.close()
        log.info("👋 Shutdown complete")

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    setup_application(app, dispatcher, bot=bot)
    return app


def main() -> None:
    async def runner():
        app = await build_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", settings.WEBHOOK_PORT)
        await site.start()
        log.info("🚀 Running on :%s", settings.WEBHOOK_PORT)
        while True:
            await asyncio.sleep(3600)

    asyncio.run(runner())


if __name__ == "__main__":
    main()
