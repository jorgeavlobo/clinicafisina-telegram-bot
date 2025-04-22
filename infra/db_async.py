import asyncpg, os
from shared.config import settings
import logging

log = logging.getLogger(__name__)

class DBPools:
    pool: asyncpg.Pool = None

    @classmethod
    async def init(cls):
        if cls.pool:
            return
        cls.pool = await asyncpg.create_pool(
            dsn=os.getenv("DATABASE_URL", "postgresql://jorgeavlobo@localhost/fisina"),
            min_size=1,
            max_size=10,
        )
        log.info("✅ PostgreSQL pool ready")

    @classmethod
    async def close(cls):
        if cls.pool:
            await cls.pool.close()
            log.info("👋 PG pool closed")
