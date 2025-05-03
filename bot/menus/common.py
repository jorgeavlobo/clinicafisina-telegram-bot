# bot/menus/common.py
"""
Botões e utilitários de UI partilhados.

• back_button() / cancel_back_kbd()
• start_menu_timeout() – apaga o menu depois de X s
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
    Após `menu_timeout` s tenta **apagar** a mensagem-menu.
    Se não puder, remove teclado e substitui texto por ZERO-WIDTH SPACE.
    No fim, actualiza os campos `menu_*` e limpa/atualiza a lista
    `menu_ids`, preservando `active_role`.
    """
    try:
        await asyncio.sleep(menu_timeout)

        data = await state.get_data()
        if data.get("menu_msg_id") != msg_id:          # há menu mais recente
            return

        # 1) tenta apagar completamente
        deleted = False
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            deleted = True
        except exceptions.TelegramBadRequest:
            deleted = False

        # 2) se não conseguiu, “esvazia” a mensagem
        if not deleted:
            with suppress(exceptions.TelegramBadRequest):
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text="\u200B",                     # ZERO WIDTH SPACE
                    reply_markup=None,
                )

        # 3) limpa registos do menu mas mantém active_role
        await clear_keep_role(state)

        # – remove este ID da lista de menus (se existir)
        menu_ids: List[int] = data.get("menu_ids", [])
        if msg_id in menu_ids:
            menu_ids.remove(msg_id)

        await state.update_data(
            menu_msg_id=None,
            menu_chat_id=None,
            menu_ids=menu_ids,                         # pode ficar []
        )

        # 4) aviso temporário
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

    ⚠️ Não guarda o objecto `asyncio.Task` no FSM – evita erros de
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
