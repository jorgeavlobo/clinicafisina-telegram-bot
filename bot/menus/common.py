# bot/menus/common.py
"""
Utilitários partilhados por todos os menus inline.

• back_button()  – devolve um InlineKeyboardButton “Voltar”.
• start_menu_timeout() – agenda a eliminação automática do menu
  se não houver interacção em 60 s (ver chamadas nos handlers).
"""

import asyncio
from typing import Callable, Awaitable

from aiogram import Bot, exceptions          # ← import corrigido aqui
from aiogram.types import InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext


__all__ = ["back_button", "start_menu_timeout"]


# ──────────────────────────── Botão “Voltar” ────────────────────────────
def back_button() -> InlineKeyboardButton:
    """🔙 Botão genérico de retorno com callback-data «back»."""
    return InlineKeyboardButton(text="🔙 Voltar", callback_data="back")


# ─────────────────────── Timeout automático do menu ─────────────────────
async def _delete_menu_after_delay(
    bot: Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
    delay: int,
) -> None:
    """Tarefa interna: aguarda ‹delay› s e elimina o menu se ainda existir."""
    await asyncio.sleep(delay)

    data = await state.get_data()
    # Se entretanto foi mostrado outro menu, aborta:
    if data.get("menu_msg_id") != msg_id:
        return

    try:
        await bot.delete_message(chat_id, msg_id)
    except exceptions.TelegramBadRequest:
        # mensagem já não existe ou é demasiado antiga
        pass

    await bot.send_message(
        chat_id,
        "⌛ O menu ficou inactivo durante 60 s e foi fechado.\n"
        "Se precisar, utilize /start ou o botão “Menu” para reabri-lo.",
    )
    # limpa as chaves do menu no FSM
    await state.update_data(menu_msg_id=None, menu_chat_id=None)


def start_menu_timeout(
    bot: Bot,
    message: Message,
    state: FSMContext,
    delay: int = 60,
) -> None:
    """
    Agenda a remoção automática da mensagem-menu após ‹delay› segundos.

    Deve ser chamada IMEDIATAMENTE depois de enviar o menu e
    guardar em FSM:
        await state.update_data(menu_msg_id=msg.message_id, ...)
        common.start_menu_timeout(bot, msg, state)
    """
    asyncio.create_task(
        _delete_menu_after_delay(
            bot=bot,
            chat_id=message.chat.id,
            msg_id=message.message_id,
            state=state,
            delay=delay,
        )
    )
