#!/usr/bin/env python3
"""
Test-drive das queries principais após a migração:

Passos
──────
1.  Procura inexistente por telegram_user_id.
2.  Cria um utilizador “dummy”.
3.  Adiciona telefone principal.
4.  Procura pelo número de telefone.
5.  Faz link do telegram_user_id a *esse* telefone.
6.  Garante a role 'patient' e associa ao utilizador.
7.  Lista as roles do utilizador.

Pode correr quantas vezes quiser: todas as inserções estão protegidas
por `ON CONFLICT DO NOTHING`.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from bot.database.connection import get_pool
from bot.database import queries as q
from bot.utils.phone import cleanse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)

# ─────────────── dados de teste ───────────────
RAW_PHONE        = "351916932985"
PHONE_DIGITS     = cleanse(RAW_PHONE)          # só dígitos
TEST_TG_ID       = 5555                        # qualquer nº ≠ real
DUMMY_FIRST_NAME = "Test"
DUMMY_LAST_NAME  = f"User_{datetime.utcnow():%H%M%S}"  # evite colisões

# ─────────────── helpers ───────────────
def spaced_digits(s: str) -> str:
    return " ".join(f"[{c}]" for c in s)

# ─────────────── Script principal ───────────────
async def main() -> None:
    pool = await get_pool()

    logging.info("PHONE  → %s    len=%d", spaced_digits(PHONE_DIGITS), len(PHONE_DIGITS))
    ok_regex = await pool.fetchval(
        "SELECT $1 ~ '^[1-9][0-9]{6,14}$'::text",
        PHONE_DIGITS,
    )
    logging.info("Regex no PG passa?  %s", ok_regex)

    # 1) procura inexistente
    logging.info("get_user_by_telegram_id(%s)  → %s",
                 TEST_TG_ID, await q.get_user_by_telegram_id(pool, TEST_TG_ID))

    # 2) cria utilizador dummy
    user_id = await q.create_user(pool, DUMMY_FIRST_NAME, DUMMY_LAST_NAME)
    logging.info("Utilizador criado  user_id=%s", user_id)

    # 3) telefone principal
    await q.add_phone(pool, user_id, PHONE_DIGITS, is_primary=True)
    logging.info("Telefone %s inserido/garantido", PHONE_DIGITS)

    # 4) procura por telefone
    logging.info("get_user_by_phone(%s) → %s",
                 PHONE_DIGITS, await q.get_user_by_phone(pool, PHONE_DIGITS))

    # 5) liga telegram_user_id a ESTE telefone
    await q.link_telegram_id(pool, user_id, PHONE_DIGITS, TEST_TG_ID)
    logging.info("Depois de link_telegram_id → %s",
                 await q.get_user_by_telegram_id(pool, TEST_TG_ID))

    # 6) garante role 'patient' e associa
    await pool.execute(
        "INSERT INTO roles(role_name) VALUES('patient') ON CONFLICT DO NOTHING"
    )
    await q.add_user_role(pool, user_id, "patient")

    # 7) lista roles
    roles = await q.get_user_roles(pool, user_id)
    logging.info("Roles para %s → %s", user_id, roles)

    await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
