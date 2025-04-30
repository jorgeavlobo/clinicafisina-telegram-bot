# bot/database/queries.py
"""
Operações CRUD de alto e baixo nível para PostgreSQL via asyncpg.

• Mantém as funções originais usadas por autenticação e middleware.
• Acrescenta add_user() — cria utilizador completo (role, email, telefone).
• date_of_birth agora opcional (None).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import date

from asyncpg import Pool, Record


# ───────────────────────── helpers internos ─────────────────────────
def _to_dict(rec: Record | None) -> Optional[Dict[str, Any]]:
    return dict(rec) if rec else None


# ───────────────────────── consultas de leitura ─────────────────────────
async def get_user_by_telegram_id(pool: Pool, tg_id: int) -> Optional[Dict[str, Any]]:
    rec = await pool.fetchrow(
        "SELECT * FROM users WHERE telegram_user_id = $1", tg_id
    )
    return _to_dict(rec)


async def get_user_by_phone(pool: Pool, phone_digits: str) -> Optional[Dict[str, Any]]:
    rec = await pool.fetchrow(
        """
        SELECT u.*
        FROM   users u
        JOIN   user_phones p USING (user_id)
        WHERE  p.phone_number = $1
        LIMIT  1
        """,
        phone_digits,
    )
    return _to_dict(rec)


async def link_telegram_id(pool: Pool, user_id: str, tg_id: int) -> None:
    """
    Liga telegram_user_id a um utilizador, de forma idempotente.
    """
    await pool.execute(
        """
        UPDATE users
        SET    telegram_user_id = $2
        WHERE  user_id = $1
          AND (telegram_user_id IS NULL OR telegram_user_id = $2)
        """,
        user_id, tg_id,
    )


async def get_user_roles(pool: Pool, user_id: str) -> List[str]:
    """
    Devolve a lista de papéis atribuídos ao utilizador,
    sempre como strings minúsculas.
    """
    rows = await pool.fetch(
        """
        SELECT r.role_name
        FROM   user_roles ur
        JOIN   roles       r USING (role_id)
        WHERE  ur.user_id = $1
        """,
        user_id,
    )
    return [row["role_name"].lower() for row in rows]


# ───────────────────────── inserções granulares ─────────────────────────
async def create_user(
    pool: Pool,
    first_name: str,
    last_name: str,
    tax_id: Optional[str] = None,
) -> str:
    rec = await pool.fetchrow(
        """
        INSERT INTO users (first_name, last_name, tax_id_number)
        VALUES ($1, $2, $3)
        RETURNING user_id
        """,
        first_name, last_name, tax_id,
    )
    return str(rec["user_id"])


async def add_user_role(pool: Pool, user_id: str, role_name: str) -> None:
    role_id = await pool.fetchval(
        "SELECT role_id FROM roles WHERE role_name = $1",
        role_name,
    )
    if role_id:
        await pool.execute(
            """
            INSERT INTO user_roles (user_id, role_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            """,
            user_id, role_id,
        )


async def add_email(
    pool: Pool,
    user_id: str,
    email: str,
    is_primary: bool = False,
) -> None:
    await pool.execute(
        """
        INSERT INTO user_emails (user_id, email, is_primary)
        VALUES ($1, $2, $3)
        ON CONFLICT DO NOTHING
        """,
        user_id, email, is_primary,
    )


async def add_phone(
    pool: Pool,
    user_id: str,
    phone_number: str,
    is_primary: bool = False,
) -> None:
    await pool.execute(
        """
        INSERT INTO user_phones (user_id, phone_number, is_primary)
        VALUES ($1, $2, $3)
        ON CONFLICT DO NOTHING
        """,
        user_id, phone_number, is_primary,
    )


async def add_address(
    pool: Pool,
    user_id: str,
    *,
    country: Optional[str] = None,
    city: Optional[str] = None,
    postal_code: Optional[str] = None,
    street: Optional[str] = None,
    street_number: Optional[str] = None,
    is_primary: bool = False,
) -> None:
    await pool.execute(
        """
        INSERT INTO addresses
              (user_id, country, city, postal_code,
               street, street_number, is_primary)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
        ON CONFLICT DO NOTHING
        """,
        user_id, country, city, postal_code,
        street, street_number, is_primary,
    )


# ───────────────────────── inserção “tudo-em-um” ─────────────────────────
async def add_user(
    pool: Pool,
    *,
    role: str,
    first_name: str,
    last_name: str,
    date_of_birth: Optional[date],
    phone_cc: str,
    phone: str,
    email: str,
    created_by: Optional[str] = None,          # ← agora opcional
) -> str:
    """
    Cria utilizador + role + e-mail + telefone primários.
    Devolve o user_id (UUID).
    """
    async with pool.acquire() as conn, conn.transaction():
        user_id = await conn.fetchval(
            """
            INSERT INTO users (first_name, last_name, date_of_birth, created_by)
            VALUES ($1,$2,$3,$4)
            RETURNING user_id
            """,
            first_name, last_name, date_of_birth, created_by,
        )

        role_id = await conn.fetchval(
            "SELECT role_id FROM roles WHERE role_name=$1", role
        )
        if role_id:
            await conn.execute(
                "INSERT INTO user_roles (user_id, role_id) VALUES ($1,$2)",
                user_id, role_id,
            )

        await conn.execute(
            """
            INSERT INTO user_emails (user_id, email, is_primary)
            VALUES ($1,$2,TRUE)
            """,
            user_id, email,
        )

        await conn.execute(
            """
            INSERT INTO user_phones (user_id, phone_number, is_primary)
            VALUES ($1,$2,TRUE)
            """,
            user_id, f"{phone_cc}{phone}",
        )

    return str(user_id)
