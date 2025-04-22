"""
Data‑access layer – todas as queries isoladas.
"""

import asyncpg
import logging
from typing import Optional, List, Any

_LOG = logging.getLogger(__name__)


class DAL:
    """Gateway assíncrono para Postgres (usa pool do infra.db_async)."""

    def __init__(self, pool: asyncpg.pool.Pool):
        self.pool = pool

    # ------------- users -------------
    async def get_user_by_telegram(self, telegram_id: int) -> Optional[dict]:
        q = """
        SELECT u.*, array_agg(r.role_name) AS roles
        FROM users u
        LEFT JOIN user_roles ur USING (user_id)
        LEFT JOIN roles      r  USING (role_id)
        WHERE telegram_user_id = $1
        GROUP BY u.user_id;
        """
        async with self.pool.acquire() as con:
            row = await con.fetchrow(q, telegram_id)
            return dict(row) if row else None

    async def link_telegram_to_user(self, user_id, telegram_id):
        q = "UPDATE users SET telegram_user_id=$1 WHERE user_id=$2;"
        async with self.pool.acquire() as con:
            await con.execute(q, telegram_id, user_id)

    # ------------- phones -------------
    async def get_user_by_phone(self, phone: str) -> Optional[dict]:
        q = """
        SELECT u.*
        FROM user_phones p
        JOIN users u USING (user_id)
        WHERE REPLACE(phone_number, '+', '') = $1
        LIMIT 1;
        """
        async with self.pool.acquire() as con:
            row = await con.fetchrow(q, phone)
            return dict(row) if row else None

    # helpers usados pelos routers ------------------
    async def link_telegram_by_phone(self, phone: str, telegram: int):
        user = await self.get_user_by_phone(phone)
        if user:
            await self.link_telegram_to_user(user["user_id"], telegram)
        return user
