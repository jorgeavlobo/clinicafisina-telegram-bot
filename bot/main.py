import asyncio, logging
from aiogram import Bot, Dispatcher
from bot.config import BOT_TOKEN, LOG_LEVEL
from bot.middlewares.role_check import RoleCheckMiddleware

async def run():
    logging.basicConfig(level=LOG_LEVEL)
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.message.middleware(RoleCheckMiddleware())
    # importa routers vazios
    from bot.handlers import register_routers
    register_routers(dp)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(run())
