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
        keyboard=[[  # one row – two buttons
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
    """
    Wait *menu_timeout* seconds and then try to remove the menu.

    • If deletion succeeds → nothing else to do.
    • If it fails (e.g. user already scrolled up) → strip the message text
      and inline-keyboard to a single ZERO-WIDTH SPACE so the chat history
      looks cleaner and users cannot press dead buttons.
    • Finally, wipe menu-related FSM fields but keep the active role,
      and optionally show a short warning that auto-hiding happened.
    """
    try:
        await asyncio.sleep(menu_timeout)

        data = await state.get_data()
        if data.get("menu_msg_id") != msg_id:
            # A newer menu exists – abort silently.
            return

        # 1) Try hard-delete
        deleted = False
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            deleted = True
        except exceptions.TelegramBadRequest:
            deleted = False

        # 2) Fallback: blank the message
        if not deleted:
            with suppress(exceptions.TelegramBadRequest):
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text="\u200B",  # ZERO-WIDTH SPACE
                    reply_markup=None,
                )

        # 3) Clear menu-related state but keep active_role intact
        await clear_keep_role(state)

        # – Remove this ID from the historical list, if stored
        menu_ids: List[int] = data.get("menu_ids", [])
        if msg_id in menu_ids:
            menu_ids.remove(msg_id)

        await state.update_data(
            menu_msg_id=None,
            menu_chat_id=None,
            menu_ids=menu_ids,
        )

        # 4) Optional toast-style warning message
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
        # Never let a background Task explode
        pass


def start_menu_timeout(
    bot: Bot,
    message: Message,
    state: FSMContext,
    menu_timeout: int = MENU_TIMEOUT,
    message_timeout: int = MESSAGE_TIMEOUT,
) -> None:
    """
    Start (or restart) the inactivity timer for a menu message.

    ⚠️ The asyncio.Task is *not* stored inside the FSM to avoid
       serialization issues in the chosen storage backend.
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
    Reuse the current menu message (edit it) when possible, otherwise send a
    fresh one. In both cases, persist the visible message ID inside the FSM.

    This utility removes the perceptible “jump” when transitioning between
    menus because Telegram only performs an *edit* (no animation) instead of
    a delete-and-send cycle.

    Parameters
    ----------
    bot : Bot
        The aiogram Bot instance.
    state : FSMContext
        The user/session FSM context for keeping track of the menu.
    chat_id : int
        Where the menu should appear (usually `cb.message.chat.id`).
    message : Message | None
        The message to be edited. Pass `None` to force creation of a new one.
    text : str
        New caption/text of the menu.
    kbd : InlineKeyboardMarkup
        Inline-keyboard to attach.
    parse_mode : str, default "Markdown"
        How Telegram should parse *text*.
    """
    try:
        if message:  # Try editing first – smoother UX
            await bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=message.message_id,
                reply_markup=kbd,
                parse_mode=parse_mode,
            )
            visible_msg = message
        else:
            raise exceptions.TelegramBadRequest  # Jump to except: create new
    except exceptions.TelegramBadRequest:
        # Either no original message, or editing failed (e.g., >4096 chars)
        visible_msg = await bot.send_message(
            chat_id=chat_id,
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
