# bot/menus/common.py
"""
Shared UI helpers and buttons.

• back_button() / cancel_back_kbd()
• start_menu_timeout() – hides a menu after X s of inactivity
• replace_or_create_menu() – edits the current menu message (preferred) or
  sends a new one, always updating the FSM so other helpers may track it.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import List, Optional

from aiogram import Bot, exceptions
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    Message,
)
from aiogram.fsm.context import FSMContext

from bot.config import MENU_TIMEOUT, MESSAGE_TIMEOUT
from bot.utils.fsm_helpers import clear_keep_role

__all__ = [
    "back_button",
    "cancel_back_kbd",
    "start_menu_timeout",
    "replace_or_create_menu",
]

# ───────────────────────── buttons / keyboards ─────────────────────────
def back_button() -> InlineKeyboardButton:
    """Inline button for returning to the previous step."""
    return InlineKeyboardButton(text="⬅️ Voltar", callback_data="back")


def cancel_back_kbd() -> ReplyKeyboardMarkup:
    """Reply-keyboard with *Cancel* / *Back* options (used in add-user flow)."""
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text="↩️ Regressar à opção anterior"),
            KeyboardButton(text="❌ Cancelar processo de adição"),
        ]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

# ───────────────────────── menu timeout logic ─────────────────────────
async def _hide_menu_after(
    bot: Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
    menu_timeout: int,
    message_timeout: int,
) -> None:
    """Background task that auto-hides an inactive menu."""
    try:
        await asyncio.sleep(menu_timeout)

        data = await state.get_data()
        if data.get("menu_msg_id") != msg_id:
            return                                      # newer menu exists

        # 1) hard-delete if possible
        deleted = False
        try:
            await bot.delete_message(chat_id, msg_id)
            deleted = True
        except exceptions.TelegramBadRequest:
            deleted = False

        # 2) else blank message
        if not deleted:
            with suppress(exceptions.TelegramBadRequest):
                await bot.edit_message_text(
                    chat_id, msg_id, "\u200B", reply_markup=None
                )

        # 3) purge state but keep active_role
        await clear_keep_role(state)

        menu_ids: List[int] = data.get("menu_ids", [])
        if msg_id in menu_ids:
            menu_ids.remove(msg_id)

        await state.update_data(
            menu_msg_id=None,
            menu_chat_id=None,
            menu_ids=menu_ids,
        )

        # 4) toast notice
        warn: Optional[Message] = None
        with suppress(exceptions.TelegramBadRequest):
            warn = await bot.send_message(
                chat_id,
                f"⌛️ O menu ficou inactivo durante {menu_timeout}s e foi ocultado.\n"
                "Use /start para o reabrir.",
            )
        if warn:
            await asyncio.sleep(message_timeout)
            with suppress(exceptions.TelegramBadRequest):
                await warn.delete()
    except Exception:
        pass                                            # never explode


def start_menu_timeout(
    bot: Bot,
    message: Message,
    state: FSMContext,
    menu_timeout: int = MENU_TIMEOUT,
    message_timeout: int = MESSAGE_TIMEOUT,
) -> None:
    """Launch the auto-hide coroutine for a given menu message."""
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

# ───────────────────────── replace / create helper ─────────────────────────
async def replace_or_create_menu(
    bot: Bot,
    state: FSMContext,
    chat_id: int,
    *,
    message: Message | None,
    text: str,
    kbd: InlineKeyboardMarkup,
    parse_mode: str = "Markdown",
) -> Message:
    """
    Edit the current menu message when possible; otherwise send a new one.

    A second (silent) edit attempt is made **without** parse_mode if the first
    fails with a Markdown/HTML parse error – this avoids falling back to a
    brand-new message (and therefore avoids the visual jump) when the only
    problem is bad markup.
    """
    visible_msg: Message | None = None

    # First try – as requested
    if message:
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=message.message_id,
                reply_markup=kbd,
                parse_mode=parse_mode,
            )
            visible_msg = message            # success
        except exceptions.TelegramBadRequest as e:
            # Parse error? Try again without parse_mode
            if "parse" in str(e).lower():
                try:
                    await bot.edit_message_text(
                        text=text,
                        chat_id=chat_id,
                        message_id=message.message_id,
                        reply_markup=kbd,
                        parse_mode=None,
                    )
                    visible_msg = message
                except exceptions.TelegramBadRequest:
                    visible_msg = None       # will create new
            else:
                visible_msg = None           # any other 400 → create new

    # If editing was impossible or message is None → create fresh menu
    if visible_msg is None:
        visible_msg = await bot.send_message(
            chat_id,
            text=text,
            reply_markup=kbd,
            parse_mode=parse_mode,
        )

    # ── FSM bookkeeping ────────────────────────────────────────────
    data = await state.get_data()
    menu_ids: List[int] = data.get("menu_ids", [])
    if visible_msg.message_id not in menu_ids:
        menu_ids.append(visible_msg.message_id)

    await state.update_data(
        menu_msg_id=visible_msg.message_id,
        menu_chat_id=visible_msg.chat.id,
        menu_ids=menu_ids,
    )
    return visible_msg
