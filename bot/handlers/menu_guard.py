# bot/handlers/menu_guard.py
"""
Router genérico que:
• garante que apenas o menu inline mais recente responde aos cliques;
• mostra pop-up se o utilizador carregar num menu antigo;
• oferece helpers (is_active_menu / replace_menu) reutilizáveis.

Tem de ser incluído ANTES dos routers de cada perfil
(handlers/__init__.py já o faz).
"""
from __future__ import annotations

from aiogram import Router, F, exceptions
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import BaseFilter                     # ✅ correcto em 3.20

from bot.menus.common import start_menu_timeout

# ───────────────── SkipHandler compatível 3.20 ────────────────────
try:
    from aiogram.exceptions import SkipHandler as _SkipHandler      # ≥ 3.2
except (ImportError, AttributeError):
    class _SkipHandler(Exception):
        """Fallback para interromper a cadeia de handlers."""


router = Router(name="menu_guard")

# ───────────────────── helpers reutilizáveis ──────────────────────
async def is_active_menu(cb: CallbackQuery, state: FSMContext) -> bool:
    data = await state.get_data()
    menu_id = data.get("menu_msg_id")
    return menu_id is None or cb.message.message_id == menu_id


async def replace_menu(
    cb: CallbackQuery,
    state: FSMContext,
    text: str,
    reply_markup,
) -> None:
    """Substitui (ou cria) o menu e reinicia o timeout de 60 s."""
    try:
        await cb.message.edit_text(text, reply_markup=reply_markup,
                                   parse_mode="Markdown")
        msg = cb.message
    except exceptions.TelegramBadRequest:
        await cb.message.delete()
        msg = await cb.message.answer(text, reply_markup=reply_markup,
                                      parse_mode="Markdown")
        await state.update_data(menu_msg_id=msg.message_id,
                                menu_chat_id=msg.chat.id)

    start_menu_timeout(cb.bot, msg, state)

# ─────────────── filtro + handler para menus antigos ───────────────
class _StaleMenu(BaseFilter):
    async def __call__(self, cb: CallbackQuery, state: FSMContext) -> bool:
        return not await is_active_menu(cb, state)


# captura callbacks dos nossos menus conhecidos
router.callback_query.filter(
    F.data.startswith((
        "admin:", "agenda:", "users:",
        "patient:", "caregiver:", "physio:", "accountant:",
    ))
)

@router.callback_query(_StaleMenu())
async def _stale_menu_guard(cb: CallbackQuery):
    await cb.answer(
        "⚠️ Este menu já não está activo.\n"
        "Envie /start ou prima *Menu* para abrir um novo.",
        show_alert=True,
    )
    raise _SkipHandler()        # impede que outros routers tratem este clique
