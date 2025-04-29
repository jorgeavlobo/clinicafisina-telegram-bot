# bot/database/queries.py
"""
Operações CRUD de baixo nível usadas pela camada de autenticação
e pelo middleware de roles.
"""
from typing import Any, Dict, List, Optional
from asyncpg import Pool, Record

# ---------- helpers ----------
def _to_dict(rec: Record | None) -> Optional[Dict[str, Any]]:
    return dict(rec) if rec else None

# ---------- API ----------
async def get_user_by_telegram_id(pool: Pool, tg_id: int) -> Optional[Dict[str, Any]]:
    rec = await pool.fetchrow("SELECT * FROM users WHERE telegram_user_id = $1", tg_id)
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
    rows = await pool.fetch(
        """
        SELECT r.role_name
        FROM   user_roles ur
        JOIN   roles r USING (role_id)
        WHERE  ur.user_id = $1
        """,
        user_id,
    )
    return [row["role_name"] for row in rows]

# ---------- insertion operations ----------
async def create_user(pool: Pool, first_name: str, last_name: str, tax_id: Optional[str] = None) -> str:
    """Insert a new user and return the generated user_id."""
    rec = await pool.fetchrow(
        """
        INSERT INTO users (first_name, last_name, tax_id_number)
        VALUES ($1, $2, $3)
        RETURNING user_id
        """,
        first_name, last_name, tax_id
    )
    return str(rec["user_id"]) if rec else None

async def add_user_role(pool: Pool, user_id: str, role_name: str) -> None:
    """Add a role to the given user (role_name corresponds to roles.role_name)."""
    role_rec = await pool.fetchrow("SELECT role_id FROM roles WHERE role_name = $1", role_name)
    if not role_rec:
        return
    role_id = role_rec["role_id"]
    await pool.execute(
        "INSERT INTO user_roles (user_id, role_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
        user_id, role_id
    )

async def add_email(pool: Pool, user_id: str, email: str, is_primary: bool = False) -> None:
    """Add an email for the user."""
    await pool.execute(
        """
        INSERT INTO user_emails (user_id, email, is_primary)
        VALUES ($1, $2, $3)
        ON CONFLICT DO NOTHING
        """,
        user_id, email, is_primary
    )

async def add_phone(pool: Pool, user_id: str, phone_number: str, is_primary: bool = False) -> None:
    """Add a phone number for the user."""
    await pool.execute(
        """
        INSERT INTO user_phones (user_id, phone_number, is_primary)
        VALUES ($1, $2, $3)
        ON CONFLICT DO NOTHING
        """,
        user_id, phone_number, is_primary
    )

async def add_address(pool: Pool, user_id: str, country: Optional[str] = None, city: Optional[str] = None,
                      postal_code: Optional[str] = None, street: Optional[str] = None,
                      street_number: Optional[str] = None, is_primary: bool = False) -> None:
    """Add an address for the user."""
    await pool.execute(
        """
        INSERT INTO addresses (user_id, country, city, postal_code, street, street_number, is_primary)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT DO NOTHING
        """,
        user_id, country, city, postal_code, street, street_number, is_primary
    )
