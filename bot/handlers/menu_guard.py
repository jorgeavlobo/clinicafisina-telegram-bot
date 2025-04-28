# bot/handlers/menu_guard.py
"""
Funções utilitárias e *router* genérico que:
• garante que apenas o último menu inline permanece activo;
• repõe/actualiza o menu (com timeout de 60 s);
• intercepta cliques em menus antigos e mostra pop-up.
"""
from __future__ import annotations

from aiogram import Router, exceptions
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import SkipHandler          # ← v3.20

from bot.menus.common import start_menu_timeout

router = Router(name="menu_guard")


# ───────────────────────── helpers reutilizáveis ──────────────────────────
async def is_active_menu(cb: CallbackQuery, state: FSMContext) -> bool:
    """True se o clique ocorreu no último menu registado no FSM."""
    data = await state.get_data()
    return cb.message.message_id == data.get("menu_msg_id")


async def replace_menu(
    cb: CallbackQuery,
    state: FSMContext,
    text: str,
    kbd: InlineKeyboardMarkup,
    parse_mode: str = "Markdown",
) -> Message:
    """
    Edita (ou envia nova) mensagem-menu, grava o id no FSM
    e (re)inicia o timeout de 60 s.
    """
    try:
        await cb.message.edit_text(text, reply_markup=kbd, parse_mode=parse_mode)
        msg = cb.message
    except exceptions.TelegramBadRequest:
        try:
            await cb.message.delete()
        except exceptions.TelegramBadRequest:
            pass
        msg = await cb.message.answer(text, reply_markup=kbd, parse_mode=parse_mode)

    await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)
    start_menu_timeout(cb.bot, msg, state)
    return msg


# ───────────────────── fallback: cliques em menus antigos ──────────────────
@router.callback_query()
async def _stale_menu_guard(cb: CallbackQuery, state: FSMContext) -> None:
    """
    Executa-se *antes* dos handlers específicos.
    • Se o menu do clique não for o activo ⇒ mostra pop-up e levanta SkipHandler.
    • Caso contrário deixa o fluxo continuar normalmente.
    """
    if not await is_active_menu(cb, state):
        await cb.answer(
            "⚠️ Este menu já não está activo.\n"
            "Envie /start ou pressione *Menu* para abrir um novo.",
            show_alert=True,
        )
        raise SkipHandler()                  # interrompe restante processamento
