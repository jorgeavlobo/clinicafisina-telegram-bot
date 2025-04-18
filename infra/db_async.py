# infra/db_async.py
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME_FISINA = os.getenv("DB_NAME_FISINA", "fisina")
DB_NAME_LOGS   = os.getenv("DB_NAME_LOGS", "logs")

class DBPools:
    pool_fisina: asyncpg.Pool | None = None
    pool_logs:   asyncpg.Pool | None = None

    @classmethod
    async def init(cls):
        cls.pool_fisina = await asyncpg.create_pool(
            host=DB_HOST, port=DB_PORT, user=DB_USER,
            password=DB_PASSWORD, database=DB_NAME_FISINA,
            min_size=1, max_size=5
        )
        cls.pool_logs = await asyncpg.create_pool(
            host=DB_HOST, port=DB_PORT, user=DB_USER,
            password=DB_PASSWORD, database=DB_NAME_LOGS,
            min_size=1, max_size=5
        )

    @classmethod
    async def close(cls):
        if cls.pool_fisina:
            await cls.pool_fisina.close()
        if cls.pool_logs:
            await cls.pool_logs.close()
