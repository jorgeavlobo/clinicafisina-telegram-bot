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

from bot.config            import MENU_TIMEOUT, MESSAGE_TIMEOUT
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
    """
    Remove o inline-keyboard do menu depois de `menu_timeout` segundos
    de inactividade e mostra um aviso que desaparece após `message_timeout`.
    """
    try:
        await asyncio.sleep(menu_timeout)

        data = await state.get_data()
        if data.get("menu_msg_id") != msg_id:
            # Outro menu foi entretanto aberto → este deixa de ser válido.
            return

        # 1. Oculta o teclado do menu (evita ValidationError → use kwargs)
        with suppress(exceptions.TelegramBadRequest):
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=msg_id,
                reply_markup=None,
            )

        # 2. Limpa registos do menu mas preserva «active_role»
        await clear_keep_role(state)
        await state.update_data(menu_msg_id=None, menu_chat_id=None)

        # 3. Mensagem temporária de aviso
        warn = await bot.send_message(
            chat_id,
            f"⌛️ O menu ficou inactivo durante {menu_timeout}s e foi ocultado.\n"
            "Use /start para o reabrir.",
        )
        await asyncio.sleep(message_timeout)
        with suppress(exceptions.TelegramBadRequest):
            await warn.delete()

    except Exception:
        # Nunca deixar a Task rebentar em background
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

    ➜ **Não** guarda a `Task` no FSM (evita erro “Task is not JSON serializable”).
    Basta lançar uma nova Task; se já existir uma mais antiga, ela verifica
    o `menu_msg_id` e auto-termina sem efeitos.
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
