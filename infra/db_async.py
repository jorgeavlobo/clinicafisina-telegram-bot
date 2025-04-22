# infra/db_async.py
"""
Connection pools for the Fisina bot (asyncpg).

A single helper dict (DB_KW) holds every option that is common to all
databases; only the `database=` name differs between the two pools.
"""

from __future__ import annotations

import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_KW: dict[str, object] = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    # Treat “disable” or empty as *no SSL*
    "ssl":      None if os.getenv("DB_SSLMODE", "disable") != "disable" else False,
    "timeout":  float(os.getenv("DB_CONNECT_TIMEOUT", 60)),
    "min_size": 1,
    "max_size": 5,
}

class DBPools:
    """Two independent pools – one for app data, one for logs."""
    pool_fisina: asyncpg.Pool | None = None
    pool_logs:   asyncpg.Pool | None = None

    # ------------------------------------------------------------------ #
    @classmethod
    async def init(cls) -> None:
        cls.pool_fisina = await asyncpg.create_pool(
            **DB_KW, database=os.getenv("DB_NAME_FISINA", "fisina")
        )
        cls.pool_logs = await asyncpg.create_pool(
            **DB_KW, database=os.getenv("DB_NAME_LOGS", "logs")
        )

    @classmethod
    async def close(cls) -> None:
        if cls.pool_fisina:
            await cls.pool_fisina.close()
        if cls.pool_logs:
            await cls.pool_logs.close()
