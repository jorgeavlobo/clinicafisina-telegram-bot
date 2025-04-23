import asyncpg, asyncio
from bot.config import DB_URL

_pool = None

async def init():
    global _pool
    _pool = await asyncpg.create_pool(DB_URL)

async def get_conn():
    if _pool is None:
        await init()
    return _pool

# debug
if __name__ == "__main__":
    async def _test():
        async with (await get_conn()).acquire() as conn:
            v = await conn.fetchval("SELECT 1")
            print("DB OK:", v)
    asyncio.run(_test())
