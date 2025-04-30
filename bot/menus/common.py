# bot/menus/common.py
"""
Botões e utilitários de UI partilhados.
Inclui:
• back_button()                 – inline “Voltar”
• cancel_back_kbd()             – custom reply “Regressar / Cancelar”
• start_menu_timeout()          – elimina menu por inactividade
"""

import asyncio
from aiogram import Bot, exceptions
from aiogram.types import (
    InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, Message,
)
from aiogram.fsm.context import FSMContext

from bot.config import MENU_TIMEOUT, MESSAGE_TIMEOUT

__all__ = ["back_button", "cancel_back_kbd", "start_menu_timeout"]

# ─────────── Botão “Voltar” (inline) ───────────
def back_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="🔵 Voltar", callback_data="back")

# ─────────── Teclado “Regressar / Cancelar” ───────────
def cancel_back_kbd() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="↩️ Regressar à opção anterior"),
                   KeyboardButton(text="❌ Cancelar processo de adição")]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

# ─────────── Timeout automático do menu (inalterado) ───────────
async def _delete_menu_after_delay(
    bot: Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
    menu_timeout: int,
    message_timeout: int,
) -> None:
    await asyncio.sleep(menu_timeout)
    if (await state.get_data()).get("menu_msg_id") != msg_id:
        return
    try:
        await bot.delete_message(chat_id, msg_id)
    except exceptions.TelegramBadRequest:
        return

    warn = await bot.send_message(
        chat_id,
        f"⌛ O menu ficou inactivo durante {menu_timeout} s e foi fechado.\n"
        "Se precisar, use /start ou o botão «Menu».",
    )
    await state.update_data(menu_msg_id=None, menu_chat_id=None)
    asyncio.create_task(_delete_inactivity_message(
        bot, chat_id, warn.message_id, message_timeout
    ))

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
    asyncio.create_task(_delete_menu_after_delay(
        bot, message.chat.id, message.message_id,
        state, menu_timeout, message_timeout,
    ))
