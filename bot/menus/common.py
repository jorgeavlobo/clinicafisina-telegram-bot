# bot/menus/common.py
"""
Botões e utilitários de UI partilhados.

• back_button() / cancel_back_kbd()
• start_menu_timeout() – oculta o menu depois de X s
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Optional

from aiogram import Bot, exceptions
from aiogram.types import (
    InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, Message,
)
from aiogram.fsm.context import FSMContext

from bot.config import MENU_TIMEOUT, MESSAGE_TIMEOUT
from bot.utils.fsm_helpers import clear_keep_role

__all__ = ["back_button", "cancel_back_kbd", "start_menu_timeout"]


# ───────────────────────── botões / teclados ─────────────────────────
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


# ───────────────────────── timeout do menu ─────────────────────────
async def _hide_menu_after(
    bot: Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
    menu_timeout: int,
    message_timeout: int,
) -> None:
    """Remove o inline-keyboard após `menu_timeout` s."""
    try:
        await asyncio.sleep(menu_timeout)

        data = await state.get_data()
        if data.get("menu_msg_id") != msg_id:
            return                                   # outro menu já foi aberto

        # ① usar argumentos nomeados → evita ValidationError do aiogram/pydantic
        with suppress(exceptions.TelegramBadRequest):
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=msg_id,
                reply_markup=None,
            )

        # limpa registos do menu mas mantém active_role
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

    except Exception:            # nunca deixar a Task rebentar em background
        pass


def start_menu_timeout(
    bot: Bot,
    message: Message,
    state: FSMContext,
    menu_timeout: int = MENU_TIMEOUT,
    message_timeout: int = MESSAGE_TIMEOUT,
) -> None:
    """
    (Re)inicia o cronómetro que esconde o menu por inactividade.

    • Cancela o task anterior (se existir) para garantir que só um cronómetro
      está activo por utilizador.
    """
    # ② cancelar cronómetro antigo
    old_task: Optional[asyncio.Task] = (await state.get_data()).get("_menu_timeout_task")
    if old_task and not old_task.done():
        old_task.cancel()

    new_task = asyncio.create_task(
        _hide_menu_after(
            bot, message.chat.id, message.message_id,
            state, menu_timeout, message_timeout,
        )
    )
    asyncio.create_task(new_task)   # guarda-se no FSM
    asyncio.get_event_loop()
    # guarda referência para poder cancelar da próxima vez
    state.update_data(_menu_timeout_task=new_task)
