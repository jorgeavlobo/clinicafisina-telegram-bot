# infra/db_logger.py
"""
Asynchronous logging handler that writes every record ≥INFO to the
`clinicafisina_telegram_bot` table in the *logs* database.
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

_LOG = logging.getLogger(__name__)


class PGHandler(logging.Handler):
    """
    Non‑blocking PostgreSQL log handler.
    While the application is still starting, the pools are not available;
    we silently drop those early records after logging *one* warning.
    """

    _warned_no_pool = False   # class‑wide flag: warn only once

    # ------------------------------------------------------------------ #
    def emit(self, record: logging.LogRecord) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # outside of an event‑loop (module import) → skip

        # pools not ready yet?  drop record, warn once, and move on
        if DBPools.pool_logs is None:
            if not PGHandler._warned_no_pool:
                _LOG.warning("DB pools not yet initialised – "
                             "log records will be dropped temporarily")
                PGHandler._warned_no_pool = True
            return

        telegram_uid: Any = getattr(record, "telegram_user_id", None)
        chat_id:      Any = getattr(record, "chat_id", None)
        is_system:    bool = bool(getattr(record, "is_system", False))

        msg   = self.format(record)
        level = record.levelname

        async def _write() -> None:
            try:
                async with DBPools.pool_logs.acquire() as conn:
                    await conn.execute(
                        _INSERT_SQL,
                        level, telegram_uid, chat_id, is_system, msg,
                    )
            except Exception as exc:                       # noqa: BLE001
                _LOG.error("Failed to write log to DB: %s", exc, exc_info=True)

        loop.create_task(_write())


# --------------------------------------------------------------------------- #
#  Singleton instance plugged into the root logger by main.py
# --------------------------------------------------------------------------- #
pg_handler = PGHandler()
pg_handler.setLevel(logging.INFO)
pg_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
)
