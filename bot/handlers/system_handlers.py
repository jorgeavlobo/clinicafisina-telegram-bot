# bot/handlers/system_handlers.py
"""
System handlers:
- Role selection when multiple roles are available.
- Healthcheck (/healthz) and Ping (/ping) endpoints for monitoring.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from bot.menus import show_menu
from bot.states.menu_states import MenuStates

router = Router(name="system")

# ─────────────────────────── Role choice ───────────────────────────
@router.callback_query(MenuStates.WAIT_ROLE_CHOICE, F.data.startswith("role:"))
async def role_chosen(cb: CallbackQuery, state: FSMContext, roles: list[str]):
    """Handle role selection when user has multiple roles available."""
    requested = cb.data.split(":", 1)[1]
    if requested not in roles:
        await cb.answer("Não tem permissão para esse perfil.", show_alert=True)
        return
    await cb.answer()
    await show_menu(cb.bot, cb.message.chat.id, state, roles, requested)

# ─────────────────────────── /healthz ──────────────────────────────
@router.message(F.text == "/healthz")
async def healthz(message: Message):
    """
    Simple health check endpoint.
    Returns 200 OK equivalent at bot level.
    Used by Docker healthcheck or external monitoring.
    """
    await message.answer("✅ Bot saudável!")

# ─────────────────────────── /ping ────────────────────────────────
@router.message(F.text == "/ping")
async def ping(message: Message):
    """
    Simple ping-pong check.
    Confirms that the bot is responsive.
    """
    await message.answer("🏓 Pong!")
