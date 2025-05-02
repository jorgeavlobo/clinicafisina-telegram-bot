# bot/menus/common.py
"""
Botões e utilitários de UI partilhados.

• back_button() / cancel_back_kbd()
• start_menu_timeout() – apaga o menu depois de X s
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

# ───────────────────────── timeout do menu ─────────────────────────
async def _hide_menu_after(
    bot: Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
    menu_timeout: int,
    message_timeout: int,
) -> None:
    """
    Após `menu_timeout` s tenta apagar COMPLETAMENTE a mensagem-menu.
    Se não puder, remove pelo menos o inline-keyboard. Depois limpa
    os campos do menu na FSM mas mantém *active_role*.
    """
    try:
        await asyncio.sleep(menu_timeout)

        data = await state.get_data()
        if data.get("menu_msg_id") != msg_id:          # outro menu activo entretanto
            return

        # 1) tenta apagar a mensagem
        deleted: bool = False
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            deleted = True
        except exceptions.TelegramBadRequest:
            # Não conseguimos apagar (mensagem antiga, sem permissões, …)
            deleted = False

        # 2) Se não foi possível, ao menos remove o teclado
        if not deleted:
            with suppress(exceptions.TelegramBadRequest):
                await bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=msg_id,
                    reply_markup=None,
                )

        # limpa campos do menu e preserva active_role
        await clear_keep_role(state)
        await state.update_data(menu_msg_id=None, menu_chat_id=None)

        # aviso temporário
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
        # nunca deixar a Task estourar em background
        pass


def start_menu_timeout(
    bot: Bot,
    message: Message,
    state: FSMContext,
    menu_timeout: int = MENU_TIMEOUT,
    message_timeout: int = MESSAGE_TIMEOUT,
) -> None:
    """
    Inicia (ou reinicia) o cronómetro de inactividade do menu.

    ⚠️  Não guarda o objecto `asyncio.Task` no FSM – evita erros de
       serialização na storage.
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
