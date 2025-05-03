# bot/menus/ui_helpers.py
"""
Shared UI helpers for inline-menu handling (Aiogram 3.x).

This module centralises every utility that deals with Telegram message
life-cycle, keyboards, menu time-outs and clean-up.  It replaces the old
`bot/menus/common.py` and extends it with new helpers discussed in the
conversation.

Exports (see __all__ at the bottom):
    • back_button()               – back InlineKeyboardButton factory
    • cancel_back_kbd()           – ReplyKeyboardMarkup for cancel/back
    • start_menu_timeout()        – auto-hide inactive menus
    • edit_menu()                 – resilient menu renderer (edit ↦ delete ↦ ZW ↦ new)
    • close_menu_with_alert()     – show pop-up + erase menu
    • delete_messages()           – bulk hard / soft delete of arbitrary messages
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import List, Optional, Sequence, Union

from aiogram import Bot, exceptions, types
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.config import MENU_TIMEOUT, MESSAGE_TIMEOUT
from bot.utils.fsm_helpers import clear_keep_role

# Invisible character used as last-resort placeholder
ZERO_WIDTH = "\u200B"

# ───────────────────────── keyboards / buttons ──────────────────────────
def back_button() -> InlineKeyboardButton:
    """Return a standard “back” InlineKeyboardButton."""
    return InlineKeyboardButton(text="⬅️ Voltar", callback_data="back")


def cancel_back_kbd() -> ReplyKeyboardMarkup:
    """Return a ReplyKeyboard with «back» and «cancel» options."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="↩️ Regressar à opção anterior"),
                KeyboardButton(text="❌ Cancelar processo de adição"),
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

# ────────────────────── auto-hide menu after timeout ───────────────────
async def _hide_menu_after(
    bot: Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
    menu_timeout: int,
    message_timeout: int,
) -> None:
    """
    Wait `menu_timeout` seconds and try to delete the menu message.
    If deletion is not possible, clear its text/keyboard instead.
    Finally, update FSM fields `menu_*` preserving `active_role`.
    """
    try:
        await asyncio.sleep(menu_timeout)

        data = await state.get_data()
        if data.get("menu_msg_id") != msg_id:  # a newer menu is already open
            return

        # 1) hard delete attempt
        deleted = False
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            deleted = True
        except exceptions.TelegramBadRequest:
            deleted = False

        # 2) fallback: blank out the message
        if not deleted:
            with suppress(exceptions.TelegramBadRequest):
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text=ZERO_WIDTH,
                    reply_markup=None,
                )

        # 3) clear FSM records but keep `active_role`
        await clear_keep_role(state)

        # remove this ID from menu_ids (if present)
        menu_ids: List[int] = data.get("menu_ids", [])
        if msg_id in menu_ids:
            menu_ids.remove(msg_id)

        await state.update_data(
            menu_msg_id=None,
            menu_chat_id=None,
            menu_ids=menu_ids,  # may end up empty
        )

        # 4) temporary warning
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
        # Never let the background task explode
        pass


def start_menu_timeout(
    bot: Bot,
    message: Message,
    state: FSMContext,
    menu_timeout: int = MENU_TIMEOUT,
    message_timeout: int = MESSAGE_TIMEOUT,
) -> None:
    """
    Fire-and-forget coroutine that hides a menu after inactivity.

    We do *not* store the asyncio.Task in the FSM to avoid
    serialisation issues in Redis / memory storage.
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

# ───────────────────────── resilient menu renderer ──────────────────────
async def edit_menu(
    *,
    bot: Bot,
    chat_id: int,
    message_id: int | None,
    text: str,
    keyboard: InlineKeyboardMarkup,
) -> Message:
    """
    Render (or replace) an inline menu with best-effort resilience.

    Attempt order:
        1. **edit** the existing message (fastest, no flicker);
        2. **delete** the old message if editing failed;
        3. **zero-width fallback** – blank the message if delete also failed;
        4. **send** a brand-new menu silently (`disable_notification=True`).

    Returns the final `Message` object for timeout handling.
    """
    # 1) direct edit
    if message_id:
        try:
            return await bot.edit_message_text(
                text,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
        except exceptions.TelegramBadRequest:
            # editing not possible (message too old, missing, etc.)
            pass

        # 2) hard delete attempt
        deleted = False
        try:
            await bot.delete_message(chat_id, message_id)
            deleted = True
        except exceptions.TelegramBadRequest:
            deleted = False

        # 3) zero-width fallback if delete failed
        if not deleted:
            with suppress(exceptions.TelegramBadRequest):
                await bot.edit_message_text(
                    ZERO_WIDTH,
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=None,
                )

    # 4) silent send – last resort or when no previous message_id
    return await bot.send_message(
        chat_id,
        text,
        reply_markup=keyboard,
        parse_mode="Markdown",
        disable_notification=True,  # no sound/vibration on client
    )

# ─────────────────────── pop-up + menu removal helper ───────────────────
async def close_menu_with_alert(
    cb: types.CallbackQuery,
    alert_text: str,
) -> None:
    """
    Show a pop-up (`show_alert=True`) and remove the menu message.

    Steps:
        1. Answer the callback with a modal pop-up.
        2. Try to delete the message (title + buttons vanish).
        3. If delete fails, blank the message (ZERO_WIDTH + remove keyboard).
    """
    # 1) modal pop-up – immediate user feedback
    await cb.answer(alert_text, show_alert=True)

    # 2) hard delete attempt
    try:
        await cb.message.delete()
        return  # success – done
    except exceptions.TelegramBadRequest:
        # 3) fallback: blank out the message
        with suppress(exceptions.TelegramBadRequest):
            await cb.message.edit_text(
                ZERO_WIDTH,
                reply_markup=None,
            )

# ───────────────────────── bulk (soft/hard) delete ──────────────────────
async def delete_messages(
    bot: Bot,
    chat_id: int,
    messages: Union[int, Message, Sequence[Union[int, Message]]],
    *,
    soft: bool = False,
) -> None:
    """
    Delete or “soft-delete” one or many messages.

    * soft=False  → direct `deleteMessage` (preferred for chat cleanliness).
    * soft=True   → first try zero-width + keyboard removal, then hard delete
                    if that fails.

    All TelegramBadRequest errors are suppressed to keep the flow resilient.
    """
    # Normalise to iterable
    if isinstance(messages, (int, Message)):
        messages = [messages]

    for m in messages:
        mid = m.message_id if isinstance(m, Message) else m

        if soft:
            # 1) try soft delete (blank the message)
            try:
                await bot.edit_message_text(
                    ZERO_WIDTH,
                    chat_id=chat_id,
                    message_id=mid,
                    reply_markup=None,
                )
                continue  # success – next message
            except exceptions.TelegramBadRequest:
                # fall through to hard delete
                pass

        # 2) hard delete
        with suppress(exceptions.TelegramBadRequest):
            await bot.delete_message(chat_id, mid)

# ───────────────────────── module public API ────────────────────────────
__all__ = [
    "back_button",
    "cancel_back_kbd",
    "start_menu_timeout",
    "edit_menu",
    "close_menu_with_alert",
    "delete_messages",
]
