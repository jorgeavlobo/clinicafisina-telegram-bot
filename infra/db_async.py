# infra/db_async.py
"""
Create and close asyncpg connection‑pools for:
  • DB_NAME_FISINA   – production data
  • DB_NAME_LOGS     – application logs
Both pools are initialised at startup by main.py.
"""

from __future__ import annotations

import os
import asyncpg
from dotenv import load_dotenv
import logging

load_dotenv()

DB_HOST        = os.getenv("DB_HOST", "localhost")
DB_PORT        = int(os.getenv("DB_PORT", 5432))
DB_USER        = os.getenv("DB_USER")
DB_PASSWORD    = os.getenv("DB_PASSWORD")
DB_NAME_FISINA = os.getenv("DB_NAME_FISINA", "fisina")
DB_NAME_LOGS   = os.getenv("DB_NAME_LOGS",   "logs")

_LOG = logging.getLogger(__name__)

#: asyncpg timeout (seconds) for establishing **one** connection
_CONNECT_TIMEOUT = 10.0


class DBPools:
    """Singleton holder for the two asyncpg pools."""
    pool_fisina: asyncpg.Pool | None = None
    pool_logs:   asyncpg.Pool | None = None

    # ------------------------------------------------------------------ #
    # life‑cycle
    # ------------------------------------------------------------------ #
    @classmethod
    async def init(cls) -> None:
        """Create both pools.  Raises on failure."""
        _LOG.info("🟡  Creating PostgreSQL pools …")

        common_kwargs = dict(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            min_size=1,
            max_size=5,
            timeout=_CONNECT_TIMEOUT,
            ssl=False,              # <‑‑ important inside Docker bridge
        )

        cls.pool_fisina = await asyncpg.create_pool(
            database=DB_NAME_FISINA,
            **common_kwargs,
        )
        cls.pool_logs = await asyncpg.create_pool(
            database=DB_NAME_LOGS,
            **common_kwargs,
        )

        _LOG.info("✅  PostgreSQL pools ready")

    @classmethod
    async def close(cls) -> None:
        """Close both pools gracefully."""
        _LOG.info("🔻  Closing PostgreSQL pools …")
        if cls.pool_fisina:
            await cls.pool_fisina.close()
        if cls.pool_logs:
            await cls.pool_logs.close()
        _LOG.info("✅  Pools closed")
