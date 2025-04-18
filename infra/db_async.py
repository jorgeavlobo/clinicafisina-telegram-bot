# infra/db_async.py  – only two tiny additions  ❰❰❰

import os, asyncpg
from dotenv import load_dotenv
load_dotenv()

DB_KW = dict(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 5432)),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    # ← THIS is the whole fix:
    ssl=False if os.getenv("DB_SSLMODE", "disable") == "disable" else None,
    timeout=float(os.getenv("DB_CONNECT_TIMEOUT", 10)),   # seconds
    min_size=1, max_size=5,
)

class DBPools:
    pool_fisina: asyncpg.Pool | None = None
    pool_logs:   asyncpg.Pool | None = None

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
        if cls.pool_fisina: await cls.pool_fisina.close()
        if cls.pool_logs:   await cls.pool_logs.close()
