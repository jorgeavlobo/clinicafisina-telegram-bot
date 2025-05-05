#!/usr/bin/env python3
"""
Pequenos testes manuais às queries base.

• Cria um utilizador dummy
• Adiciona 1 telefone principal
• Verifica procura por nº de telefone
• Associa (ou actualiza) telegram_user_id nesse telefone
• Confirma procura por telegram_user_id
• Adiciona/garante role 'patient' e lista roles
"""

import asyncio
import logging
from datetime import datetime

from bot.database.connection import get_pool
from bot.database import queries as q
from bot.utils.phone import cleanse

logging.basicConfig(level="INFO")

RAW_PHONE = "351916932985"
PHONE = cleanse(RAW_PHONE)           # deixa só dígitos

def debug_digits(s: str) -> str:
    return " ".join(f"[{c}]" for c in s)

async def main() -> None:
    pool = await get_pool()
    logging.info("DEBUG PHONE: %s  len=%d", debug_digits(PHONE), len(PHONE))

    ok = await pool.fetchval(
        "SELECT $1 ~ '^[1-9][0-9]{6,14}$'::text", PHONE
    )
    logging.info("Regex passa no PG? -> %s", ok)

    # 1) procura (inexistente) por telegram_user_id
    user = await q.get_user_by_telegram_id(pool, 9999)
    logging.info("get_user_by_telegram_id(9999) -> %s", user)

    # 2) cria utilizador dummy
    rec = await pool.fetchrow(
        "INSERT INTO users(first_name, last_name) "
        "VALUES('Test', 'User') RETURNING user_id"
    )
    user_id = rec["user_id"]
    logging.info("Novo user_id → %s", user_id)

    # 3) adiciona telefone primário
    await pool.execute(
        """
        INSERT INTO user_phones(user_id, phone_number, is_primary)
        VALUES($1, $2, TRUE)
        ON CONFLICT DO NOTHING
        """,
        user_id,
        PHONE,
    )

    # 4) busca pelo telefone
    user = await q.get_user_by_phone(pool, PHONE)
    logging.info("get_user_by_phone -> %s", user)

    # 5) liga telegram id ao telefone recém-inserido
    await q.link_telegram_id(pool, user_id, PHONE, 5555)
    linked = await q.get_user_by_telegram_id(pool, 5555)
    logging.info("Depois de link_telegram_id -> %s", linked)

    # 6) garante role 'patient' e associa
    await pool.execute(
        "INSERT INTO roles(role_name) VALUES('patient') ON CONFLICT DO NOTHING"
    )
    role_id = await pool.fetchval(
        "SELECT role_id FROM roles WHERE role_name='patient'"
    )
    await pool.execute(
        """
        INSERT INTO user_roles(user_id, role_id)
        VALUES($1,$2)
        ON CONFLICT DO NOTHING
        """,
        user_id,
        role_id,
    )

    # 7) lista roles
    roles = await q.get_user_roles(pool, user_id)
    logging.info("roles -> %s", roles)

    await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
