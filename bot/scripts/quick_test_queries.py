import asyncio, logging
from bot.database.connection import get_pool
from bot.database import queries as q
from bot.utils.phone import cleanse

logging.basicConfig(level="INFO")

PHONE = cleanse("351916932985")

def debug_digits(s: str) -> str:
    return " ".join(f"[{c}]" for c in s)

async def main():
    pool = await get_pool()

    print("DEBUG PHONE:", debug_digits(PHONE), "len:", len(PHONE))
    ok = await pool.fetchval("SELECT $1 ~ '^[1-9][0-9]{6,14}$'", PHONE)
    print("DEBUG regex passes in DB? ->", ok)

    # 1) ausência de telegram_user_id
    user = await q.get_user_by_telegram_id(pool, 9999)
    logging.info("get_user_by_telegram_id -> %s", user)

    # 2) cria utilizador dummy
    rec = await pool.fetchrow(
        "INSERT INTO users(first_name, last_name) VALUES('Test','User') RETURNING user_id"
    )
    user_id = rec["user_id"]

    # 3) adiciona telefone de teste
    await pool.execute(
        "INSERT INTO user_phones(user_id, phone_number, is_primary) VALUES($1, $2, TRUE)",
        user_id,
        PHONE,
    )

    # 4) busca pelo telefone
    user = await q.get_user_by_phone(pool, PHONE)
    logging.info("get_user_by_phone -> %s", user)

    # 5) liga telegram id
    await q.link_telegram_id(pool, user_id, 5555)
    logging.info("linked -> %s", await q.get_user_by_telegram_id(pool, 5555))

    # 6) seed role 'patient' e associa
    await pool.execute("INSERT INTO roles(role_name) VALUES('patient') ON CONFLICT DO NOTHING")
    role_id = await pool.fetchval("SELECT role_id FROM roles WHERE role_name='patient'")
    await pool.execute(
        "INSERT INTO user_roles(user_id, role_id) VALUES($1,$2) ON CONFLICT DO NOTHING",
        user_id,
        role_id,
    )

    # 7) lista roles
    roles = await q.get_user_roles(pool, user_id)
    logging.info("roles -> %s", roles)

    await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
