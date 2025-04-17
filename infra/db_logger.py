# infra/db_logger.py
import logging
import asyncio
from typing import Any
from infra.db_async import DBPools

INSERT_SQL = """
INSERT INTO clinicafisina_telegram_bot
    (level, telegram_user_id, chat_id, message)
VALUES ($1,  $2,               $3,      $4)
"""

class PGHandler(logging.Handler):
    """
    Asynchronous logging handler that writes to PostgreSQL.
    Because logging.Handler.emit is sync, we delegate to
    `asyncio.create_task` so we never block the event‑loop.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Outside of event‑loop (e.g., gunicorn preload); skip
            return

        telegram_uid = getattr(record, "telegram_user_id", None)
        chat_id      = getattr(record, "chat_id", None)
        msg          = self.format(record)
        level        = record.levelname

        async def _write():
            try:
                async with DBPools.pool_logs.acquire() as conn:
                    await conn.execute(INSERT_SQL, level, telegram_uid, chat_id, msg)
            except Exception as e:
                # fall back to stderr if DB fails
                logging.getLogger(__name__).error(
                    "Failed to write log to DB: %s", e, exc_info=True
                )

        loop.create_task(_write())

# create single instance
pg_handler = PGHandler()
pg_handler.setLevel(logging.INFO)
pg_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
