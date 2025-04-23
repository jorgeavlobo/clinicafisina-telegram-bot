"""
Async PostgreSQL pools
"""

import os
import ssl
import asyncpg
from typing import Final, Dict

# Parâmetros comuns (host, porta, user, password, ssl…)
DB_KW: Final[Dict[str, object]] = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "timeout":  60,
    "min_size": int(os.getenv("DB_POOL_MIN", 1)),
    "max_size": int(os.getenv("DB_POOL_MAX", 5)),
    # SSL – se DB_SSLMODE == disable → False, caso contrário SSLContext
    "ssl": None
    if os.getenv("DB_SSLMODE", "disable").lower() == "disable"
    else ssl.create_default_context(),
}


class DBPools:
    """
    Armazena pools globalmente.
    Uso: `await DBPools.init()` no startup,
    depois `pool = await DBPools.pool("fisina")`.
    """

    _pools: dict[str, asyncpg.Pool] = {}

    @classmethod
    async def init(cls) -> None:
        """Cria pools; idempotente."""
        if cls._pools:  # já inicializado
            return

        db_map = {
            "fisina": os.getenv("DB_NAME_FISINA", "fisina"),
            "logs":   os.getenv("DB_NAME_LOGS",   "fisina_logs"),
        }

        for key, db_name in db_map.items():
            cls._pools[key] = await asyncpg.create_pool(database=db_name, **DB_KW)

    @classmethod
    async def close(cls) -> None:
        """Fecha todos os pools (para shutdown gracioso)."""
        for pool in cls._pools.values():
            await pool.close()
        cls._pools.clear()

    @classmethod
    async def pool(cls, name: str = "fisina") -> asyncpg.Pool:
        """
        Devolve pool existente ou lança erro se ainda não inicializado.
        """
        pool = cls._pools.get(name)
        if pool is None:
            raise RuntimeError("DBPools not initialised; call DBPools.init() first")
        return pool

    # Helpers convenientes
    @classmethod
    async def fetch(cls, query: str, *args, name: str = "fisina"):
        pool = await cls.pool(name)
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)

    @classmethod
    async def execute(cls, query: str, *args, name: str = "fisina"):
        pool = await cls.pool(name)
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)
