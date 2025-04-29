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
        user_id,
        tg_id,
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
