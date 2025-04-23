# bot/database/queries.py
"""
Operações CRUD de baixo nível usadas pela camada de autenticação
e pelo middleware de roles.
"""

from typing import Any, Dict, List, Optional
from asyncpg import Pool, Record

# ---------------------------------------------------------------------
# helpers internos

def _to_dict(rec: Record | None) -> Optional[Dict[str, Any]]:
    """Converte asyncpg.Record para dict simples (ou None)."""
    return dict(rec) if rec else None


# ---------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------

# 1. procurar utilizador por telegram_user_id
async def get_user_by_telegram_id(pool: Pool, tg_id: int) -> Optional[Dict[str, Any]]:
    sql = "SELECT * FROM users WHERE telegram_user_id = $1"
    rec = await pool.fetchrow(sql, tg_id)
    return _to_dict(rec)


# 2. procurar utilizador por telefone (E.164)
async def get_user_by_phone(pool: Pool, phone_e164: str) -> Optional[Dict[str, Any]]:
    sql = """
        SELECT u.*
        FROM   users u
        JOIN   user_phones p USING (user_id)
        WHERE  p.phone_number = $1
        LIMIT  1
    """
    rec = await pool.fetchrow(sql, phone_e164)
    return _to_dict(rec)


# 3. associar telegram_user_id a um utilizador existente
async def link_telegram_id(pool: Pool, user_id: str, tg_id: int) -> None:
    sql = """
        UPDATE users
        SET    telegram_user_id = $2
        WHERE  user_id = $1
          AND (telegram_user_id IS NULL OR telegram_user_id = $2)
    """
    await pool.execute(sql, user_id, tg_id)


# 4. obter lista de roles (strings) de um utilizador
async def get_user_roles(pool: Pool, user_id: str) -> List[str]:
    sql = """
        SELECT r.role_name
        FROM   user_roles ur
        JOIN   roles r USING (role_id)
        WHERE  ur.user_id = $1
    """
    rows = await pool.fetch(sql, user_id)
    return [row["role_name"] for row in rows]
