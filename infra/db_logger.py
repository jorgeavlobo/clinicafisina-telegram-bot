import logging, asyncpg, asyncio, os
from infra.db_async import DBPools

class PGHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        asyncio.create_task(self.write(record))

    async def write(self, record):
        try:
            pool = DBPools.pool
            if not pool:
                return
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO logs(level, message) VALUES($1,$2)",
                    record.levelname, self.format(record)
                )
        except Exception:
            pass

pg_handler = PGHandler()
pg_handler.setLevel(logging.INFO)
pg_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
