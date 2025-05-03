# bot/menus/common.py
"""
Shared UI helpers.

• back_button() / cancel_back_kbd()
• start_menu_timeout()          – background timer that hides an **idle** menu
• hide_menu_now()               – helper that hides a menu *immediately*
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import List, Optional

from aiogram import Bot, exceptions
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, Message,
)

from bot.config import MENU_TIMEOUT, MESSAGE_TIMEOUT
from bot.utils.fsm_helpers import clear_keep_role

__all__ = [
    "back_button",
    "cancel_back_kbd",
    "start_menu_timeout",
    "hide_menu_now",
]

# ────────────────────────── keyboards ──────────────────────────
def back_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="⬅️ Voltar", callback_data="back")


def cancel_back_kbd() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text="↩️ Regressar à opção anterior"),
            KeyboardButton(text="❌ Cancelar processo de adição"),
        ]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

# ─────────────────────── helpers – hide menu now ───────────────
async def hide_menu_now(
    bot: Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
    message_timeout: int = MESSAGE_TIMEOUT,
) -> None:
    """
    Try to delete the message *right away*; if Telegram refuses,
    fall back to:

    • remove inline-keyboard
    • replace text with ZERO-WIDTH SPACE

    State fields menu_* are cleared but **active_role** is preserved.
    """
    # 1) delete
    deleted = False
    try:
        await bot.delete_message(chat_id, msg_id)
        deleted = True
    except exceptions.TelegramBadRequest:
        deleted = False

    # 2) visual fallback
    if not deleted:
        with suppress(exceptions.TelegramBadRequest):
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text="\u200B",           # invisible char
                reply_markup=None,
            )

    # 3) housekeeping
    await clear_keep_role(state)
    data = await state.get_data()
    menu_ids: List[int] = data.get("menu_ids", [])
    if msg_id in menu_ids:
        menu_ids.remove(msg_id)

    await state.update_data(
        menu_msg_id=None,
        menu_chat_id=None,
        menu_ids=menu_ids,
    )

    # 4) short heads-up (auto-delete)
    warn: Optional[Message] = None
    with suppress(exceptions.TelegramBadRequest):
        warn = await bot.send_message(
            chat_id,
            "⌛️ O menu anterior foi ocultado.",
        )
    if warn:
        await asyncio.sleep(message_timeout)
        with suppress(exceptions.TelegramBadRequest):
            await warn.delete()

# ───────────────────── background idle timer ───────────────────
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

        # there is a newer menu – abort
        data = await state.get_data()
        if data.get("menu_msg_id") != msg_id:
            return

        # reuse the immediate helper
        await hide_menu_now(
            bot, chat_id, msg_id, state,
            message_timeout=message_timeout,
        )

    except Exception:               # never let a task blow up silently
        pass


def start_menu_timeout(
    bot: Bot,
    message: Message,
    state: FSMContext,
    menu_timeout: int = MENU_TIMEOUT,
    message_timeout: int = MESSAGE_TIMEOUT,
) -> None:
    """
    Starts (or restarts) the idle-timeout for the current menu.
    """
    asyncio.create_task(
        _hide_menu_after(
            bot,
            message.chat.id,
            message.message_id,
            state,
            menu_timeout,
            message_timeout,
        )
    )
