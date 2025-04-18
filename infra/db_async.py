"""
Async connection‑pool helper using asyncpg.
Adds a longer timeout and disables SSL (matches your psql test).
"""

import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_HOST         = os.getenv("DB_HOST", "host.docker.internal")
DB_PORT         = int(os.getenv("DB_PORT", 5432))
DB_USER         = os.getenv("DB_USER")
DB_PASSWORD     = os.getenv("DB_PASSWORD")
DB_NAME_FISINA  = os.getenv("DB_NAME_FISINA", "fisina")
DB_NAME_LOGS    = os.getenv("DB_NAME_LOGS", "logs")

# Common kwargs for both pools
_common = dict(
    host     = DB_HOST,
    port     = DB_PORT,
    user     = DB_USER,
    password = DB_PASSWORD,
    timeout  = 15,      # seconds (default pool timeout is 5)
    ssl      = False,   # skip TLS handshake; same as your manual psql test
    min_size = 1,
    max_size = 5,
)

class DBPools:
    pool_fisina: asyncpg.Pool | None = None
    pool_logs:   asyncpg.Pool | None = None

    # ------------------------------------------------------------------ #
    @classmethod
    async def init(cls):
        cls.pool_fisina = await asyncpg.create_pool(
            database=DB_NAME_FISINA, **_common
        )
        cls.pool_logs = await asyncpg.create_pool(
            database=DB_NAME_LOGS, **_common
        )

    # ------------------------------------------------------------------ #
    @classmethod
    async def close(cls):
        if cls.pool_fisina:
            await cls.pool_fisina.close()
        if cls.pool_logs:
            await cls.pool_logs.close()
