# bot/database/connection.py
"""
Singleton para o pool asyncpg usado em toda a aplicação.

• Lê a variável DATABASE_URL de bot.config
• Funções expostas:
      init()      → cria/devolve pool (primeira chamada inicializa)
      get_pool()  → alias de conveniência para init()
      close()     → fecha pool de forma limpa (invocar no shutdown)
"""

from __future__ import annotations

import asyncpg
from typing import Optional

from bot.config import DATABASE_URL   # ← mantém o nome existente na tua config

_pool: Optional[asyncpg.Pool] = None


async def init() -> asyncpg.Pool:
    """
    Cria, se necessário, e devolve o pool global.

    Chama esta função uma única vez (por ex. no main.py) e reutiliza a pool
    em todo o código.
    """
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=DATABASE_URL,
            min_size=1,
            max_size=10,
        )
    return _pool


async def get_pool() -> asyncpg.Pool:
    """Alias directo para init()."""
    return await init()


async def close() -> None:
    """Fecha graciosamente o pool (deve ser chamado no shutdown)."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


# ---------- teste rápido ----------
if __name__ == "__main__":           # python -m bot.database.connection
    import asyncio

    async def _test():
        pool = await get_pool()
        async with pool.acquire() as conn:
            val = await conn.fetchval("SELECT 1")
            print("DB OK:", val)

    asyncio.run(_test())
