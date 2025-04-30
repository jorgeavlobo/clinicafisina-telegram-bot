# bot/menus/common.py
"""
Utilitários partilhados por todos os menus inline.

• back_button()  – devolve um InlineKeyboardButton “Voltar”.
• start_menu_timeout() – agenda a eliminação automática do menu
  se não houver interação em ‹menu_timeout› segundos.
• Após apagar o menu, a mensagem de aviso é também apagada
  automaticamente após ‹message_timeout› segundos.
"""
from __future__ import annotations

import asyncio
from aiogram import Bot, exceptions
from aiogram.types import InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext

from bot.config import MENU_TIMEOUT, MESSAGE_TIMEOUT

__all__ = ["back_button", "start_menu_timeout"]

# ──────────────────────────── Botão “Voltar” ────────────────────────────
def back_button() -> InlineKeyboardButton:
    """
    ⬅️ Botão genérico de retorno com callback-data «back».
    (linha separada nos teclados inline:  [ back_button() ])
    """
    return InlineKeyboardButton(text="⬅️ Voltar", callback_data="back")

# ─────────────────────── Timeout automático do menu ─────────────────────
async def _delete_menu_after_delay(
    bot: Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
    menu_timeout: int,
    message_timeout: int,
) -> None:
    """Aguarda ‹menu_timeout› s; se o menu ainda for o activo, remove-o."""
    await asyncio.sleep(menu_timeout)

    data = await state.get_data()
    if data.get("menu_msg_id") != msg_id:
        return  # já não é o menu activo

    try:
        await bot.delete_message(chat_id, msg_id)
    except exceptions.TelegramBadRequest:
        return

    try:
        warn = await bot.send_message(
            chat_id,
            f"⌛ O menu ficou inactivo durante {menu_timeout}s e foi fechado.\n"
            "Se necessário, use /start ou o botão “Menu” para reabri-lo.",
        )
    except exceptions.TelegramBadRequest:
        return

    await state.update_data(menu_msg_id=None, menu_chat_id=None)

    # apagar a mensagem de aviso após ‹message_timeout› s
    asyncio.create_task(
        _delete_inactivity_message(bot, chat_id, warn.message_id, message_timeout)
    )

async def _delete_inactivity_message(
    bot: Bot, chat_id: int, msg_id: int, delay: int
) -> None:
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, msg_id)
    except exceptions.TelegramBadRequest:
        pass

def start_menu_timeout(
    bot: Bot,
    message: Message,
    state: FSMContext,
    menu_timeout: int = MENU_TIMEOUT,
    message_timeout: int = MESSAGE_TIMEOUT,
) -> None:
    """
    Agenda a remoção automática da mensagem-menu após ‹menu_timeout› s
    e, depois, a remoção da mensagem-aviso após ‹message_timeout› s.

    Deve ser chamada logo após enviar/editar o menu:
        await state.update_data(menu_msg_id=msg.message_id, ...)
        start_menu_timeout(bot, msg, state)
    """
    asyncio.create_task(
        _delete_menu_after_delay(
            bot=bot,
            chat_id=message.chat.id,
            msg_id=message.message_id,
            state=state,
            menu_timeout=menu_timeout,
            message_timeout=message_timeout,
        )
    )
