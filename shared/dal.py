# shared/dal.py  (substitui o teu ficheiro — mantém só se te fizer sentido)

"""
Data‑access layer – versão estendida.
"""

from typing import Optional, Sequence
import asyncpg
from asyncpg.exceptions import UniqueViolationError
from infra.db_async import DBPools


class DALException(Exception):
    pass


class DAL:
    # ---------- LEITURA ----------
    @staticmethod
    async def get_user_by_telegram_id(tg_id: int) -> Optional[asyncpg.Record]:
        async with DBPools.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM users WHERE telegram_user_id = $1",
                tg_id,
            )

    @staticmethod
    async def find_user_by_phone(phone: str) -> Optional[asyncpg.Record]:
        phone = DAL._normalize_phone(phone)
        async with DBPools.pool.acquire() as conn:
            return await conn.fetchrow(
                """
                SELECT u.* FROM users u
                JOIN user_phones p USING (user_id)
                WHERE p.phone_number = $1
                """,
                phone,
            )

    @staticmethod
    async def get_roles(user_id) -> Sequence[str]:
        async with DBPools.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT r.role_name
                FROM user_roles ur
                JOIN roles r USING (role_id)
                WHERE ur.user_id = $1
                """,
                user_id,
            )
            return [r["role_name"] for r in rows]

    # ---------- ESCRITA ----------
    @staticmethod
    async def create_user(
        first_name: str,
        last_name: str,
        telegram_user_id: int | None = None,
    ) -> asyncpg.Record:
        async with DBPools.pool.acquire() as conn:
            try:
                return await conn.fetchrow(
                    """
                    INSERT INTO users (first_name, last_name, telegram_user_id)
                    VALUES ($1, $2, $3)
                    RETURNING *
                    """,
                    first_name,
                    last_name,
                    telegram_user_id,
                )
            except UniqueViolationError as e:
                raise DALException("User already exists") from e

    @staticmethod
    async def link_telegram(user_id, tg_id: int) -> None:
        async with DBPools.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users SET telegram_user_id = $1
                WHERE user_id = $2
                """,
                tg_id,
                user_id,
            )

    @staticmethod
    async def insert_phone(user_id, phone: str, primary: bool = True) -> None:
        phone = DAL._normalize_phone(phone)
        async with DBPools.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO user_phones (user_id, phone_number, is_primary)
                VALUES ($1, $2, $3)
                ON CONFLICT (phone_number) DO NOTHING
                """,
                user_id,
                phone,
                primary,
            )

    @staticmethod
    async def add_role(user_id, role_name: str) -> None:
        async with DBPools.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO user_roles (user_id, role_id)
                VALUES ($1,
                        (SELECT role_id FROM roles WHERE role_name = $2))
                ON CONFLICT DO NOTHING
                """,
                user_id,
                role_name,
            )

    # ---------- HELPERS ----------
    @staticmethod
    def _normalize_phone(phone: str) -> str:
        return "".join(ch for ch in phone if ch.isdigit())
