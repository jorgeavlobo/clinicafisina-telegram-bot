# shared/dal.py
"""
Data‑Access Layer (DAL) simples e reutilizável.

✅  Requisitos cumpridos
    • Conexões obtidas via infra.db_async.DBPools
    • Retries exponenciais p/ falhas transitórias
    • Funções helper await‑able: fetch, fetchrow, execute, executemany
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Sequence

from infra.db_async import DBPools
from psycopg import errors as pg_errors       # type: ignore

_LOG = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Helpers internos
# ──────────────────────────────────────────────────────────────
_TRANSIENT_ERRORS: tuple[type[Exception], ...] = (
    pg_errors.AdminShutdown,
    pg_errors.CannotConnectNow,
    pg_errors.ConnectionFailure,
    pg_errors.DeadlockDetected,
)


async def _with_retry(
    fn,
    *args,
    retries: int = 3,
    backoff: float = 0.5,
    **kwargs,
):
    """
    Executa `fn` com tentativas extra em caso de erro transitório.
    backoff exponencial → 0.5 s, 1 s, 2 s …
    """
    attempt = 0
    while True:
        try:
            return await fn(*args, **kwargs)
        except _TRANSIENT_ERRORS as exc:
            attempt += 1
            if attempt > retries:
                _LOG.error("DAL: giving up after %s retries – %r", retries, exc)
                raise
            delay = backoff * (2 ** (attempt - 1))
            _LOG.warning("DAL: transient error (%s). Retry in %.1f s …", exc.__class__.__name__, delay)
            await asyncio.sleep(delay)


# ──────────────────────────────────────────────────────────────
# API pública
# ──────────────────────────────────────────────────────────────
async def fetch(query: str, *params) -> list[dict[str, Any]]:
    """
    Devolve todas as linhas ➜ list[dict]
    """
    async def _run(conn):
        stmt = await conn.prepare(query)
        rows = await stmt.fetch(*params)
        return [dict(r) for r in rows]

    async with DBPools.get_conn() as conn:
        return await _with_retry(_run, conn)


async def fetchrow(query: str, *params) -> dict[str, Any] | None:
    """
    Devolve 1 linha ou None
    """
    async def _run(conn):
        stmt = await conn.prepare(query)
        row = await stmt.fetchrow(*params)
        return dict(row) if row else None

    async with DBPools.get_conn() as conn:
        return await _with_retry(_run, conn)


async def execute(query: str, *params) -> str:
    """
    Executa INSERT/UPDATE/DELETE – devolve status string
    """
    async def _run(conn):
        res = await conn.execute(query, *params)
        return res

    async with DBPools.get_conn() as conn:
        return await _with_retry(_run, conn)


async def executemany(query: str, seq_of_params: Sequence[Sequence[Any]]) -> None:
    """
    Executa a mesma query com vários conjuntos de parâmetros.
    """
    async def _run(conn):
        await conn.executemany(query, seq_of_params)

    async with DBPools.get_conn() as conn:
        await _with_retry(_run, conn)
