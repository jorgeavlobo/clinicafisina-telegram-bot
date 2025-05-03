# bot/menus/common.py
"""
Shared UI buttons and helpers.

• back_button() / cancel_back_kbd()
• start_menu_timeout() – deletes menu after X s (idle)
• hide_menu_now()      – deletes / blanks menu **immediately** (no warning)
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import List, Optional

from aiogram import Bot, exceptions
from aiogram.types import (
    InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, Message,
)
from aiogram.fsm.context import FSMContext

from bot.config import MENU_TIMEOUT, MESSAGE_TIMEOUT
from bot.utils.fsm_helpers import clear_keep_role

# export-list
__all__ = ["back_button", "cancel_back_kbd",
           "start_menu_timeout", "hide_menu_now"]

# ────────────────────────── buttons / keyboards ──────────────────────────
def back_button() -> InlineKeyboardButton:
    """Inline “Back” button used across the bot."""
    return InlineKeyboardButton(text="⬅️ Voltar", callback_data="back")


def cancel_back_kbd() -> ReplyKeyboardMarkup:
    """Reply-keyboard shown in long forms (e.g. add-user flow)."""
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text="↩️ Regressar à opção anterior"),
            KeyboardButton(text="❌ Cancelar processo de adição"),
        ]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

# ────────────────────────── hide / timeout helpers ─────────────────────────
async def _hide_menu_after(
    bot: Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
    menu_timeout: int,
    message_timeout: int,
    warn_user: bool = True,            # NEW ▸ controls “⌛️ menu inactivo…” toast
) -> None:
    """
    Delete **or** blank a menu message after *menu_timeout* seconds.

    Workflow:
      1. `await asyncio.sleep(menu_timeout)`
      2. Try to `deleteMessage`; fallback → `editMessageText` to ZERO WIDTH SPACE
      3. Clean FSM menu-tracking fields (keeps *active_role* intact)
      4. Optionally (`warn_user=True`) send a temporary “⌛️ menu inactive” notice
         that auto-deletes after *message_timeout* seconds.

    When called with *menu_timeout == 0* the effect is **instantaneous**.
    """
    try:
        await asyncio.sleep(menu_timeout)

        data = await state.get_data()
        if data.get("menu_msg_id") != msg_id:          # newer menu already open
            return

        # 1) try hard-delete
        deleted = False
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            deleted = True
        except exceptions.TelegramBadRequest:
            deleted = False

        # 2) if delete failed → blank the message (zero-width space, no keyboard)
        if not deleted:
            with suppress(exceptions.TelegramBadRequest):
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text="\u200B",                     # ZERO-WIDTH SPACE
                    reply_markup=None,
                )

        # 3) clear menu-tracking fields but **preserve** active_role
        await clear_keep_role(state)

        menu_ids: List[int] = data.get("menu_ids", [])
        if msg_id in menu_ids:
            menu_ids.remove(msg_id)

        await state.update_data(
            menu_msg_id=None,
            menu_chat_id=None,
            menu_ids=menu_ids,                         # may become []
        )

        # 4) optional toast to inform user
        if warn_user:
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
        # never let the background Task explode
        pass


def start_menu_timeout(
    bot: Bot,
    message: Message,
    state: FSMContext,
    menu_timeout: int = MENU_TIMEOUT,
    message_timeout: int = MESSAGE_TIMEOUT,
) -> None:
    """
    Arm (or re-arm) the idle-timeout for a freshly sent menu.

    We *do not* store the asyncio.Task in FSM — avoids serialisation problems.
    """
    asyncio.create_task(
        _hide_menu_after(
            bot,
            message.chat.id,
            message.message_id,
            state,
            menu_timeout,
            message_timeout,
            warn_user=True,            # default behaviour
        )
    )


def hide_menu_now(
    bot: Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
) -> None:
    """
    Instantly delete / blank a menu **without** showing the idle-warning.

    Intended for use inside CallbackQuery handlers right after a user click.
    """
    asyncio.create_task(
        _hide_menu_after(
            bot,
            chat_id,
            msg_id,
            state,
            menu_timeout=0,
            message_timeout=0,
            warn_user=False,           # suppress “⌛️ …” toast
        )
    )
