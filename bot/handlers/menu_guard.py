# bot/handlers/menu_guard.py
"""
Router genérico que:

• permite só ao ÚLTIMO menu inline responder a cliques;
• mostra pop-up quando o utilizador clica num menu antigo;
• disponibiliza helpers (is_active_menu / replace_menu) para reutilizar
  nos vários handlers de menus.

Inclua este router ANTES dos routers de cada perfil
(handlers/__init__.py já faz isso).
"""
from __future__ import annotations

from aiogram import Router, F, exceptions
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.menus.common import start_menu_timeout

router = Router(name="menu_guard")

# ───────────────────── helpers reutilizáveis ──────────────────────
async def is_active_menu(cb: CallbackQuery, state: FSMContext) -> bool:
    """
    True se a mensagem do clique for a última mensagem-menu conhecida.
    Se ainda não existir menu registado devolve True (primeiro /start).
    """
    data = await state.get_data()
    menu_id = data.get("menu_msg_id")
    return menu_id is None or cb.message.message_id == menu_id


async def replace_menu(
    cb: CallbackQuery,
    state: FSMContext,
    text: str,
    reply_markup,
) -> None:
    """
    Substitui (ou cria) o menu inline e reinicia o timeout de 60 s.
    """
    try:
        await cb.message.edit_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )
        msg = cb.message
    except exceptions.TelegramBadRequest:
        await cb.message.delete()
        msg = await cb.message.answer(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )
        await state.update_data(menu_msg_id=msg.message_id,
                                menu_chat_id=msg.chat.id)

    start_menu_timeout(cb.bot, msg, state)  # (re)arma timeout

# ─────────────────── filtro para callbacks antigos ─────────────────
class StaleMenuFilter(exceptions.SkipHandler):
    async def __call__(self, cb: CallbackQuery, state: FSMContext) -> bool:
        return not await is_active_menu(cb, state)

# Apanha qualquer callback que pertença a menus conhecidos
router.callback_query.filter(
    F.data.startswith((
        "admin:", "agenda:", "users:",
        "patient:", "caregiver:", "physio:", "accountant:",
    ))
)

# ───────────────────── handler “menu antigo” ──────────────────────
@router.callback_query(StaleMenuFilter())
async def _stale_menu_guard(cb: CallbackQuery):
    await cb.answer(
        "⚠️ Este menu já não está activo.\n"
        "Use /start ou prima *Menu* para abrir um novo.",
        show_alert=True,
    )
    # pára o processamento deste callback em routers seguintes
    raise exceptions.SkipHandler()
