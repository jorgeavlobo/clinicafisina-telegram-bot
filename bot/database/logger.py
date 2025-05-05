# bot/database/logger.py
"""
Gravação assíncrona de registos (logs) em PostgreSQL.

• Os registos são inseridos na tabela *clinicafisina_telegram_bot* com:
      level, telegram_user_id, chat_id, is_system, message
• Caso a pool de ligações ainda não esteja pronta, ou ocorra erro
  na escrita, o registo é enviado para stderr (fallback seguro).
• Nenhuma alteração de estrutura é necessária depois da migração
  do telegram_user_id para user_phones — o campo continua BIGINT.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any

from infra.db_async import DBPools

# ------------------------------------------------------------------ #
#  SQL de inserção — 1 linha por log
# ------------------------------------------------------------------ #
_INSERT_SQL = """
INSERT INTO clinicafisina_telegram_bot
       (level, telegram_user_id, chat_id, is_system, message)
VALUES ($1,   $2,               $3,      $4,        $5)
"""

class PGHandler(logging.Handler):
    """
    Handler assíncrono que escreve registos em PostgreSQL.

    • Formata sempre o registo primeiro (evita avaliações tardias).
    • Enquanto a pool não estiver disponível, escreve em stderr.
    • Em caso de excepção na escrita, faz fallback para stderr
      (nunca volta a chamar logging para evitar loops).
    """

    def emit(self, record: logging.LogRecord) -> None:
        # -------- formatação imediata (thread-safe) -------- #
        formatted: str = self.format(record)

        # -------- fallback se ainda não há pool -------- #
        if DBPools.pool_logs is None:
            print(formatted, file=sys.stderr)
            return

        # -------- campos estruturados opcionais -------- #
        telegram_uid: Any = getattr(record, "telegram_user_id", None)
        chat_id:      Any = getattr(record, "chat_id", None)
        is_system:    bool = bool(getattr(record, "is_system", False))
        level_name:   str  = record.levelname

        async def _write() -> None:
            try:
                async with DBPools.pool_logs.acquire() as conn:
                    await conn.execute(
                        _INSERT_SQL,
                        level_name,
                        telegram_uid,
                        chat_id,
                        is_system,
                        formatted,
                    )
            except Exception as exc:  # pragma: no cover
                # Último recurso: nunca re-entra no sistema de logging.
                print(f"PGHandler error: {exc}\n{formatted}", file=sys.stderr)

        # -------- agenda a escrita no event-loop -------- #
        try:
            asyncio.get_running_loop().create_task(_write())
        except RuntimeError:
            # Fora de um event-loop (ex.: preload do gunicorn)
            print(formatted, file=sys.stderr)


# ------------------------------------------------------------------ #
#  Instância singleton pronta a usar
# ------------------------------------------------------------------ #
pg_handler = PGHandler()
pg_handler.setLevel(logging.INFO)
pg_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
