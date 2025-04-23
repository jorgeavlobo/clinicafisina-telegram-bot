"""
Logging handler que grava registos em PostgreSQL.
"""

import asyncio
import logging
from typing import Any

from asyncpg import Connection
from infra.db_async import DBPools

LOG_TABLE = "clinicafisina_telegram_logs"  # variável para fácil mudança

_INSERT_SQL = f"""
INSERT INTO {LOG_TABLE} (
    lvl, msg, tg_user_id, chat_id, is_system, created_at
) VALUES ($1, $2, $3, $4, $5, now())
"""


class PGHandler(logging.Handler):
    """Envia registo para PostgreSQL de forma assíncrona (fire-and-forget)."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # fora do asyncio, devolve para stderr
            logging.StreamHandler().emit(record)
            return

        loop.create_task(self._write(record))  # não bloquear

    async def _write(self, record: logging.LogRecord) -> None:
        try:
            pool = await DBPools.pool("logs")
            async with pool.acquire() as conn:  # type: Connection
                await conn.execute(
                    _INSERT_SQL,
                    record.levelname,
                    record.getMessage(),
                    getattr(record, "telegram_user_id", None),
                    getattr(record, "chat_id",         None),
                    getattr(record, "is_system",       None),
                )
        except Exception as exc:
            # fallback para stderr para evitar loop infinito
            logging.StreamHandler().emit(
                logging.makeLogRecord(
                    {
                        "msg": f"[PGHandler error] {exc} – original: {record.getMessage()}",
                        "levelno": logging.ERROR,
                        "levelname": "ERROR",
                    }
                )
            )


# Handler singleton
pg_handler = PGHandler()

def setup_pg_logging() -> None:
    """
    Chamada única no arranque para adicionar handler
    (evita múltiplas adições em reload hot).
    """
    root = logging.getLogger()
    if pg_handler not in root.handlers:
        root.addHandler(pg_handler)
