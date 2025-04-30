# bot/menus/common.py
"""
Utilitários partilhados por todos os menus inline.
• back_button()  – devolve um InlineKeyboardButton “Voltar”.
• start_menu_timeout() – elimina automaticamente o menu se ficar inactivo.
"""
import asyncio
from aiogram import Bot, exceptions
from aiogram.types import InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext

from bot.config import MENU_TIMEOUT, MESSAGE_TIMEOUT

__all__ = ["back_button", "start_menu_timeout"]

# ─────────────────────────── Botão “Voltar” ────────────────────────────
def back_button() -> InlineKeyboardButton:
    """
    🔵 Botão de retorno (callback-data = «back»).
    *Devolve o próprio botão* (não uma lista) para que cada teclado
    decida se o quer pôr numa linha própria: `[back_button()]`.
    """
    return InlineKeyboardButton(text="🔵 Voltar", callback_data="back")

# ─────────────────────── Timeout automático do menu ─────────────────────
async def _delete_menu_after_delay(
    bot: Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
    menu_timeout: int,
    message_timeout: int,
) -> None:
    await asyncio.sleep(menu_timeout)
    if (await state.get_data()).get("menu_msg_id") != msg_id:
        return                              # já não é o menu activo
    try:
        await bot.delete_message(chat_id, msg_id)
    except exceptions.TelegramBadRequest:
        return

    warn = await bot.send_message(
        chat_id,
        f"⌛ O menu ficou inactivo durante {menu_timeout} s e foi fechado.\n"
        "Se precisar, use /start ou o botão «Menu».",
    )
    await state.update_data(menu_msg_id=None, menu_chat_id=None)

    # apagar o aviso passados ‹message_timeout› s
    asyncio.create_task(_delete_inactivity_message(
        bot, chat_id, warn.message_id, message_timeout
    ))

async def _delete_inactivity_message(
    bot: Bot, chat_id: int, msg_id: int, delay: int
) -> None:
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, msg_id)
    except exceptions.TelegramBadRequest:
        pass

def start_menu_timeout(
    bot: Bot,
    message: Message,
    state: FSMContext,
    menu_timeout: int = MENU_TIMEOUT,
    message_timeout: int = MESSAGE_TIMEOUT,
) -> None:
    asyncio.create_task(_delete_menu_after_delay(
        bot, message.chat.id, message.message_id,
        state, menu_timeout, message_timeout,
    ))
