# bot/database/connection.py
import asyncpg
import asyncio
from typing import Optional

from bot.config import DATABASE_URL

_pool: Optional[asyncpg.Pool] = None


async def init() -> asyncpg.Pool:
    """Inicializa e devolve o pool (singleton)."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    return _pool


async def get_pool() -> asyncpg.Pool:
    """Obtém um pool já inicializado (ou cria se ainda não existir)."""
    return await init()


async def close() -> None:
    """Fecha graciosamente o pool (chamar no shutdown)."""
    if _pool is not None:
        await _pool.close()


# ----------------------------------------------------------------------
# debug rápido:
if __name__ == "__main__":  # python -m bot.database.connection
    async def _test():
        pool = await get_pool()
        async with pool.acquire() as conn:
            val = await conn.fetchval("SELECT 1")
            print("DB OK:", val)

    asyncio.run(_test())
