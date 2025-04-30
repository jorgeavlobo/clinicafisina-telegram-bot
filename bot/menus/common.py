# bot/menus/common.py
"""
Botões e utilitários de UI partilhados.

• back_button() / cancel_back_kbd()
• start_menu_timeout() – oculta o menu depois de X s
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Dict, Tuple

from aiogram import Bot, exceptions
from aiogram.types import (
    InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, Message,
)
from aiogram.fsm.context import FSMContext

from bot.config            import MENU_TIMEOUT, MESSAGE_TIMEOUT
from bot.utils.fsm_helpers import clear_keep_role

__all__ = ["back_button", "cancel_back_kbd", "start_menu_timeout"]

# --------------------------- botões / teclados ---------------------------
def back_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="🔵 Voltar", callback_data="back")


def cancel_back_kbd() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text="↩️ Regressar à opção anterior"),
            KeyboardButton(text="❌ Cancelar processo de adição"),
        ]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

# ---------------------- gestão de timeouts em memória --------------------
#   chave: (chat_id, message_id) -> asyncio.Task
_TIMEOUTS: Dict[Tuple[int, int], asyncio.Task] = {}


async def _hide_menu_after(
    bot: Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
    menu_timeout: int,
    message_timeout: int,
) -> None:
    try:
        await asyncio.sleep(menu_timeout)

        data = await state.get_data()
        if data.get("menu_msg_id") != msg_id:
            return                                   # outro menu activo

        with suppress(exceptions.TelegramBadRequest):
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=msg_id,
                reply_markup=None,
            )

        await clear_keep_role(state)
        await state.update_data(menu_msg_id=None, menu_chat_id=None)

        warn = await bot.send_message(
            chat_id,
            f"⌛️ O menu ficou inactivo durante {menu_timeout}s e foi ocultado.\n"
            "Use /start para o reabrir.",
        )
        await asyncio.sleep(message_timeout)
        with suppress(exceptions.TelegramBadRequest):
            await warn.delete()

    finally:
        _TIMEOUTS.pop((chat_id, msg_id), None)        # limpeza


# -------------------------- API pública --------------------------
async def start_menu_timeout(
    bot: Bot,
    message: Message,
    state: FSMContext,
    menu_timeout: int = MENU_TIMEOUT,
    message_timeout: int = MESSAGE_TIMEOUT,
) -> None:
    """
    Cancela o cronómetro anterior (se existir) e cria um novo.
    A Task é guardada apenas em memória (_TIMEOUTS).
    """
    key = (message.chat.id, message.message_id)

    # cancela cronómetro anterior para este chat-id (se houver)
    for (c_id, m_id), task in list(_TIMEOUTS.items()):
        if c_id == message.chat.id and not task.done():
            task.cancel()
        _TIMEOUTS.pop((c_id, m_id), None)

    # agenda o novo cronómetro
    _TIMEOUTS[key] = asyncio.create_task(
        _hide_menu_after(
            bot, message.chat.id, message.message_id,
            state, menu_timeout, message_timeout,
        )
    )
