# bot/handlers/debug_handlers.py
from aiogram import Router
from aiogram.filters import Command
from bot.filters.role_filter import RoleFilter

router = Router(name="debug")     # 👉 nome diferente de “system”

@router.message(Command("whoami"))
async def who_am_i(message, user: dict | None = None, roles: list[str] | None = None):
    if user:
        await message.answer(
            f"👤 {user['first_name']} {user['last_name']}\n"
            f"Roles: {roles}"
        )
    else:
        await message.answer("Ainda não estás ligado à base de dados.")

@router.message(Command("admin"), RoleFilter("administrator"))
async def admin_only(msg):
    await msg.answer("✔️ Tens acesso de administrador!")

@router.message(Command("admin"))
async def admin_denied(msg):
    await msg.answer("❌ Precisas de ser administrador para esse comando.")
