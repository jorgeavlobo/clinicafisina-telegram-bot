# bot/handlers/menu_guard.py
"""
Router genérico que:
• garante que só o ÚLTIMO menu inline responde;
• mostra pop-up quando o utilizador clica em menus antigos;
• fornece helpers (is_active_menu / replace_menu) partilhados pelos
  vários handlers de menus.

Tem de ser incluído ANTES dos outros routers (ver handlers/__init__.py).
"""
from __future__ import annotations

import asyncio
from datetime import timedelta

from aiogram import Router, F, exceptions
from aiogram.filters import Filter
from aiogram.types import CallbackQuery, EditMessageReplyMarkup
from aiogram.fsm.context import FSMContext

from bot.menus.common import start_menu_timeout

router = Router(name="menu_guard")

# ───────────────────── helpers reutilizáveis ──────────────────────
async def is_active_menu(cb: CallbackQuery, state: FSMContext) -> bool:
    """
    Devolve *True* se a mensagem onde ocorreu o clique é a última
    mensagem-menu conhecida.  
    Se ainda não existir menu registado (primeiro /start) devolve True.
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
    Substitui/edita o menu actual e reinicia o timeout de 60 s.
    Se a mensagem original já não existir, envia nova.
    """
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

    # (re)arma timeout
    start_menu_timeout(cb.bot, msg, state)

# ─────────────────── filtro para callbacks antigos ─────────────────
class StaleMenuFilter(Filter):
    async def __call__(self,
                       cb: CallbackQuery,
                       state: FSMContext) -> bool:
        return not await is_active_menu(cb, state)

# Apanha qualquer callback que comece por prefixos usados nos menus
router.callback_query.filter(
    F.data.startswith((
        "admin:", "agenda:", "users:", "patient:",
        "caregiver:", "physio:", "accountant:",
    ))
)

# ───────────────────── handler único de “menu antigo” ──────────────
@router.callback_query(StaleMenuFilter())
async def _stale_menu_guard(cb: CallbackQuery):
    await cb.answer(
        "⚠️ Este menu já não está activo.\n"
        "Envie /start ou prima *Menu* para abrir um novo.",
        show_alert=True,
    )
    # impede qualquer outro router de tratar este callback
    raise exceptions.SkipHandler()
