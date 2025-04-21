"""
dal.py  –  Data‑Access‑Layer assíncrono.

Reutiliza o pool já inicializado em infra.db_async.DBPools
(por isso **não** cria novo pool).  Todas as funções devolvem
None se nada for encontrado ou lançam excepção para ser
apanhada pelo middleware de erros.
"""
from __future__ import annotations

import logging
from typing import Optional, Sequence

from asyncpg import Record
from infra.db_async import DBPools

logger = logging.getLogger(__name__)


# ───────────────────────── helpers ──────────────────────────
async def fetchrow(query: str, *args) -> Optional[Record]:
    async with DBPools.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def execute(query: str, *args) -> None:
    async with DBPools.acquire() as conn:
        await conn.execute(query, *args)


# ───────────────────────── public API ───────────────────────
async def get_user_by_telegram_id(tg_id: int) -> Optional[Record]:
    """
    Procura utilizador pelo telegram_user_id.
    """
    sql = """
        SELECT *
        FROM   users
        WHERE  telegram_user_id = $1
    """
    return await fetchrow(sql, tg_id)


async def get_user_by_phone(phone: str) -> Optional[Record]:
    """
    Normaliza o nº (remove espaços, +, etc. simples) e procura na tabela user_phones.
    """
    normal = "".join(filter(str.isdigit, phone))
    sql = """
        SELECT u.*
        FROM   users u
        JOIN   user_phones p ON p.user_id = u.user_id
        WHERE  regexp_replace(p.phone_number, '[^0-9]', '', 'g') = $1
    """
    return await fetchrow(sql, normal)


async def link_telegram_id_to_user(user_id: str, tg_id: int) -> None:
    """
    Atribui telegram_user_id e impõe unicidade (remove possíveis ligações antigas).
    """
    async with DBPools.acquire() as conn:
        async with conn.transaction():
            # Limpa qualquer outro user que por engano tenha o mesmo tg_id
            await conn.execute(
                "UPDATE users SET telegram_user_id = NULL WHERE telegram_user_id = $1",
                tg_id,
            )
            # Liga ao user correcto
            await conn.execute(
                "UPDATE users SET telegram_user_id = $1 WHERE user_id = $2",
                tg_id,
                user_id,
            )
    logger.info("🔗 Telegram ID %s associado a user %s", tg_id, user_id)


async def get_user_roles(user_id: str) -> Sequence[str]:
    """
    Devolve lista de nomes de role (strings).
    """
    sql = """
        SELECT r.role_name
        FROM   user_roles ur
        JOIN   roles r ON r.role_id = ur.role_id
        WHERE  ur.user_id = $1
        ORDER  BY r.role_name
    """
    rows = await fetchrow(
        "SELECT array_agg(r.role_name) AS roles "
        "FROM user_roles ur JOIN roles r USING(role_id) "
        "WHERE ur.user_id = $1", user_id
    )
    return rows["roles"] if rows and rows["roles"] else []
