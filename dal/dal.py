"""
dal/dal.py  –  Data‑Access‑Layer (asyncpg)
Todas as funções retornam dict‑like `asyncpg.Record`
"""

import asyncpg
from typing import Optional, Sequence, Any
from contextlib import asynccontextmanager
import os
import logging

logger = logging.getLogger(__name__)

PG_DSN = os.getenv("DB_DSN", "postgresql://jorgeavlobo@localhost/fisina")


@asynccontextmanager
async def _get_conn():
    conn: asyncpg.Connection = await asyncpg.connect(PG_DSN)
    try:
        yield conn
    finally:
        await conn.close()


# ---------- USERS -----------------------------------------------------------

async def fetch_user_by_telegram_id(telegram_id: int) -> Optional[asyncpg.Record]:
    sql = "SELECT * FROM users WHERE telegram_user_id = $1"
    async with _get_conn() as conn:
        return await conn.fetchrow(sql, telegram_id)


async def link_telegram_id(user_id: str, telegram_id: int) -> None:
    sql = "UPDATE users SET telegram_user_id = $1 WHERE user_id = $2"
    async with _get_conn() as conn:
        await conn.execute(sql, telegram_id, user_id)


async def fetch_user_by_phone(phone: str) -> Optional[asyncpg.Record]:
    sql = """
        SELECT u.*
        FROM users u
        JOIN user_phones p USING (user_id)
        WHERE p.phone_number = $1
    """
    async with _get_conn() as conn:
        return await conn.fetchrow(sql, phone)


async def fetch_roles(user_id: str) -> Sequence[str]:
    sql = """
        SELECT r.role_name
        FROM user_roles ur
        JOIN roles r USING (role_id)
        WHERE ur.user_id = $1
    """
    async with _get_conn() as conn:
        rows = await conn.fetch(sql, user_id)
        return [row["role_name"] for row in rows]


# ---------- VISITOR LOG -----------------------------------------------------

async def log_visitor_action(*, telegram_id: int, action: str, extra: Any = None) -> None:
    sql = """
        INSERT INTO visitor_log (telegram_user_id, action, payload)
        VALUES ($1,$2,$3)
    """
    async with _get_conn() as conn:
        await conn.execute(sql, telegram_id, action, extra)
