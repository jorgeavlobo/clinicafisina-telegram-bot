# bot/handlers/debug_handlers.py
"""
Comandos de depuração / utilidade.

• /whoami  – mostra o utilizador e o perfil activo
• /admin   – demonstra verificação manual de perfil «administrator»
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

router = Router(name="debug")

# ─────────── /whoami ───────────
@router.message(F.text.startswith("/whoami"))
async def who_am_i(
    message: Message,
    state: FSMContext,
    user:   dict | None = None,
) -> None:
    if user:
        data   = await state.get_data()
        active = data.get("active_role")
        await message.answer(
            f"👤 {user['first_name']} {user['last_name']}\n"
            f"Perfil activo: {active or '—'}"
        )
    else:
        await message.answer("Ainda não estás ligado à base de dados.")

# ─────────── /admin (apenas para perfil administrador) ───────────
@router.message(F.text.startswith("/admin"))
async def admin_check(msg: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("active_role") == "administrator":
        await msg.answer("✔️ Tens acesso de administrador!")
    else:
        await msg.answer("❌ Precisas de ser administrador para esse comando.")
