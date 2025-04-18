"""
Asynchronous logging.Handler that writes every log ≥INFO to PostgreSQL.
Falls back to stderr if the pool is not ready (startup failure).
"""

import asyncio
import logging
from typing import Any

from infra.db_async import DBPools

INSERT_SQL = """
INSERT INTO clinicafisina_telegram_bot
       (level, telegram_user_id, chat_id, is_system, message)
VALUES ($1,    $2,               $3,      $4,        $5)
"""

class PGHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        telegram_uid: Any = getattr(record, "telegram_user_id", None)
        chat_id: Any      = getattr(record, "chat_id", None)
        is_system: bool   = bool(getattr(record, "is_system", False))
        msg: str          = self.format(record)
        level: str        = record.levelname

        async def _write() -> None:
            try:
                if DBPools.pool_logs is None:
                    raise RuntimeError("pool_logs is None (startup failure)")

                async with DBPools.pool_logs.acquire() as conn:
                    await conn.execute(
                        INSERT_SQL,
                        level, telegram_uid, chat_id, is_system, msg
                    )
            except Exception as e:
                logging.getLogger(__name__).error(
                    "Failed to write log to DB: %s", e, exc_info=True
                )

        loop.create_task(_write())

# singleton
pg_handler = PGHandler()
pg_handler.setLevel(logging.INFO)
pg_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
