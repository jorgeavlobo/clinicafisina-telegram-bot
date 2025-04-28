# bot/menus/common.py
"""
Utilitários partilhados entre teclados inline/reply.

• back_button() –  🔙 Voltar
• start_menu_timeout() – agenda remoção automática do menu após 60 s
"""

from __future__ import annotations

import asyncio
from typing import Dict, Tuple

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, Message, exceptions

__all__ = ["back_button", "start_menu_timeout"]

# ─────────────── Botão [Voltar] ────────────────
def back_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="🔙 Voltar", callback_data="back")


# ─────────────── Timeout de menus ──────────────
# tarefa assíncrona → { (chat_id, msg_id): task }
_TIMEOUT_TASKS: Dict[Tuple[int, int], asyncio.Task] = {}

async def _timeout_worker(
    bot: Bot,
    chat_id: int,
    msg_id: int,
    seconds: int = 60,
) -> None:
    """Espera `seconds` segundos; se a mensagem ainda existir, apaga-a e avisa."""
    try:
        await asyncio.sleep(seconds)
        await bot.delete_message(chat_id, msg_id)
        await bot.send_message(
            chat_id,
            "⏰ Menu fechado por inactividade (60 s). "
            "Escreva /start ou use o botão de menu para voltar a abrir.",
        )
    except exceptions.TelegramBadRequest:
        # mensagem já não existe ou é demasiado antiga
        pass
    finally:
        # retira do dicionário
        _TIMEOUT_TASKS.pop((chat_id, msg_id), None)

def start_menu_timeout(bot: Bot, msg: Message, seconds: int = 60) -> None:
    """
    Cancela qualquer timeout anterior *do mesmo chat* e agenda um novo.
    Chamar assim que um menu é enviado/actualizado.
    """
    # cancela timeouts pendentes no mesmo chat
    for (c_id, m_id), task in list(_TIMEOUT_TASKS.items()):
        if c_id == msg.chat.id:
            task.cancel()
            _TIMEOUT_TASKS.pop((c_id, m_id), None)

    task = asyncio.create_task(_timeout_worker(bot, msg.chat.id, msg.message_id, seconds))
    _TIMEOUT_TASKS[(msg.chat.id, msg.message_id)] = task
