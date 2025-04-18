# infra/db_logger.py
"""
Logging.Handler that writes every record ≥INFO to the
`clinicafisina_telegram_bot` table in the `logs` database.

A single instance (`pg_handler`) is imported and added to the root logger
in main.py.

The handler is **non‑blocking**: emit() schedules the INSERT with
`asyncio.create_task`, so the event‑loop never waits on I/O.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from infra.db_async import DBPools

_INSERT_SQL = """
INSERT INTO clinicafisina_telegram_bot
       (level, telegram_user_id, chat_id, is_system, message)
VALUES ($1,    $2,               $3,      $4,        $5)
"""

_LOG = logging.getLogger(__name__)     # local fallback


class PGHandler(logging.Handler):
    """Asynchronous PostgreSQL log handler."""

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        # get the current running loop – skip if we are in a non‑async
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        # extract extra fields safely
        telegram_uid: Any = getattr(record, "telegram_user_id", None)
        chat_id:      Any = getattr(record, "chat_id", None)
        is_system:    bool = bool(getattr(record, "is_system", False))

        # format AFTER we pull the extra attrs, otherwise they may be lost
        msg:   str  = self.format(record)
        level: str  = record.levelname

        # coro that does the actual INSERT
        async def _write() -> None:
            try:
                if DBPools.pool_logs is None:
                    raise RuntimeError("pool_logs is None (startup failure)")

                async with DBPools.pool_logs.acquire() as conn:
                    await conn.execute(
                        _INSERT_SQL,
                        level,
                        telegram_uid,
                        chat_id,
                        is_system,
                        msg,
                    )
            except Exception as exc:   # pylint: disable=broad-except
                # last‑chance fallback to stderr
                _LOG.error("Failed to write log to DB: %s", exc, exc_info=True)

        # schedule without awaiting
        loop.create_task(_write())


# --------------------------------------------------------------------------- #
#  Singleton instance plugged into the root logger by main.py
# --------------------------------------------------------------------------- #
pg_handler = PGHandler()
pg_handler.setLevel(logging.INFO)
pg_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
)
