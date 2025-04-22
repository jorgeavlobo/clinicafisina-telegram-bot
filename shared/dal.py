"""Data‑access layer.

For now only helper methods used in auth/registration flows.
Later expand with asyncpg pool queries (using infra.db_async).
"""

import asyncpg
from infra.db_async import DBPools

class DAL:
    @staticmethod
    async def get_user_by_telegram_id(tg_id: int):
        async with DBPools.pool.acquire() as conn:
            return await conn.fetchrow("""SELECT * FROM users WHERE telegram_user_id=$1""", tg_id)

    @staticmethod
    async def link_telegram(user_id, tg_id: int):
        async with DBPools.pool.acquire() as conn:
            await conn.execute(
                """UPDATE users SET telegram_user_id=$1 WHERE user_id=$2""", tg_id, user_id
            )

    @staticmethod
    async def find_user_by_phone(phone: str):
        async with DBPools.pool.acquire() as conn:
            return await conn.fetchrow(
                """SELECT u.* FROM users u
                    JOIN user_phones p USING (user_id)
                    WHERE p.phone_number=$1""", phone
            )

    @staticmethod
    async def insert_phone(user_id, phone: str, primary: bool = True):
        async with DBPools.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO user_phones (user_id, phone_number, is_primary)
                       VALUES ($1,$2,$3)
                       ON CONFLICT (phone_number) DO NOTHING""", user_id, phone, primary
            )
