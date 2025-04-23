import asyncio, logging
from bot.database.connection import get_pool
from bot.database import queries as q

logging.basicConfig(level="INFO")

async def main():
    pool = await get_pool()

    # 1) teste por telegram_user_id inexistente
    user = await q.get_user_by_telegram_id(pool, 9999)
    logging.info("get_user_by_telegram_id -> %s", user)

    # 2) insere utilizador de prova (podes fazer isto via psql também)
    u = await pool.fetchrow("INSERT INTO users(first_name, last_name) VALUES('Test','User') RETURNING user_id")
    user_id = u["user_id"]
    await pool.execute("INSERT INTO user_phones(user_id, phone_number, is_primary) VALUES($1, '+351912345678', TRUE)", user_id)

    # 3) busca por phone
    user = await q.get_user_by_phone(pool, "+351912345678")
    logging.info("get_user_by_phone -> %s", user)

    # 4) liga telegram id
    await q.link_telegram_id(pool, user_id, 5555)
    print(await q.get_user_by_telegram_id(pool, 5555))

    # 5) seed role patient (só se ainda não existir)
    await pool.execute("INSERT INTO roles(role_name) VALUES('patient') ON CONFLICT DO NOTHING")
    role_id = await pool.fetchval("SELECT role_id FROM roles WHERE role_name='patient'")
    await pool.execute("INSERT INTO user_roles(user_id, role_id) VALUES($1,$2) ON CONFLICT DO NOTHING", user_id, role_id)

    # 6) lista roles
    roles = await q.get_user_roles(pool, user_id)
    logging.info("roles -> %s", roles)

    await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
