# bot/database/logger.py

import asyncio
import logging
import sys
from typing import Any

from infra.db_async import DBPools

_INSERT_SQL = """
INSERT INTO clinicafisina_telegram_bot
    (level, telegram_user_id, chat_id, is_system, message)
VALUES ($1,  $2,               $3,      $4,        $5)
"""

class PGHandler(logging.Handler):
    """
    Asynchronous logging handler that writes records to PostgreSQL.
    Falls back to stderr until the DB pools are ready, and if any
    write fails later on.
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Always format first (safer – no risk of late eval inside async task)
        formatted: str = self.format(record)

        # ─────────────── fallback BEFORE pools are ready ────────────────
        if DBPools.pool_logs is None:
            print(formatted, file=sys.stderr)
            return

        # Extract structured extras (optional fields)
        telegram_uid: Any = getattr(record, "telegram_user_id", None)
        chat_id:      Any = getattr(record, "chat_id", None)
        is_system:    bool = bool(getattr(record, "is_system", False))
        level:        str  = record.levelname

        async def _write() -> None:
            try:
                async with DBPools.pool_logs.acquire() as conn:
                    await conn.execute(
                        _INSERT_SQL,
                        level,
                        telegram_uid,
                        chat_id,
                        is_system,
                        formatted,
                    )
            except Exception as exc:
                # FINAL fallback – never re‑enter logging!
                print(f"PGHandler error: {exc}\n{formatted}", file=sys.stderr)

        # Schedule without blocking the running event‑loop
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_write())
        except RuntimeError:
            # Not inside an event‑loop (e.g. during gunicorn preload)
            print(formatted, file=sys.stderr)

# --------------------------------------------------------------------- #
#  Singleton handler instance
# --------------------------------------------------------------------- #
pg_handler = PGHandler()
pg_handler.setLevel(logging.INFO)
pg_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
