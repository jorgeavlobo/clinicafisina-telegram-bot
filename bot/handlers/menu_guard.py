# bot/handlers/menu_guard.py
"""
menu_guard.py  –  utilitário genérico para todos os handlers inline-menu
────────────────────────────────────────────────────────────────────────

Funções de apoio (não é um Router):

• is_active(cb, state)          → True se o callback pertence ao menu
  actualmente activo (id guardado em FSM).

• replace_menu(cb, state, ...)  → substitui / envia o teclado-inline,
  actualiza FSM (menu_msg_id, menu_chat_id) e arma/rearma o timeout
  de 60 s através de bot.menus.common.start_menu_timeout.

• close_menu(cb, state)         → apaga o menu activo e limpa as chaves
  do FSM.

Todas as funções são _framework-agnostic_; qualquer handler que trabalhe
com menus inline pode importá-las.
"""
from __future__ import annotations

from aiogram import exceptions
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

from bot.menus.common import start_menu_timeout


# ───────────────────────── verificações ──────────────────────────
async def is_active(cb: CallbackQuery, state: FSMContext) -> bool:
    """
    Devolve *True* se o clique foi feito no último menu registado
    (menu_msg_id guardado em FSM);  caso contrário *False*.
    """
    data = await state.get_data()
    return cb.message.message_id == data.get("menu_msg_id")


# ───────────────────────── acções sobre o menu ───────────────────
async def replace_menu(
    cb: CallbackQuery,
    state: FSMContext,
    text: str,
    kbd: InlineKeyboardMarkup,
) -> None:
    """
    Tenta editar a mensagem actual; se esta já não existir, envia nova.
    • Actualiza menu_msg_id / menu_chat_id no FSM
    • Re-inicia o timeout através de start_menu_timeout
    """
    try:
        await cb.message.edit_text(text, reply_markup=kbd, parse_mode="Markdown")
        msg = cb.message
    except exceptions.TelegramBadRequest:
        # foi apagada / modificada → criar nova
        await cb.message.delete()
        msg = await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")
        await state.update_data(menu_msg_id=msg.message_id,
                                menu_chat_id=msg.chat.id)

    # (re)arma timeout global de 60 s
    start_menu_timeout(cb.bot, msg, state)


async def close_menu(cb: CallbackQuery, state: FSMContext) -> None:
    """Apaga a mensagem-menu e limpa as chaves do FSM."""
    try:
        await cb.message.delete()
    except exceptions.TelegramBadRequest:
        pass
    await state.update_data(menu_msg_id=None, menu_chat_id=None)
