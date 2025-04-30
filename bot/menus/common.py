# bot/menus/common.py
"""
Utilitários partilhados por todos os menus inline.

• back_button() – devolve um InlineKeyboardButton “Voltar”.
• start_menu_timeout() – agenda a eliminação automática do menu
  se não houver interação em ‹menu_timeout› segundos.
• Após apagar o menu, a mensagem de aviso é também apagada
  automaticamente após ‹message_timeout› segundos.
"""
import asyncio
from aiogram import Bot, exceptions
from aiogram.types import InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext

from bot.config import MENU_TIMEOUT, MESSAGE_TIMEOUT

__all__ = ["back_button", "start_menu_timeout"]

# ──────────────────────────── Botão “Voltar” ────────────────────────────
def back_button() -> InlineKeyboardButton:
    """
    🔵 Botão genérico de retorno com callback-data «back».

    ⚠️ IMPORTANTE: quando inserir o botão num teclado, envolva-o numa lista
    para formar a linha, p.ex.:
        InlineKeyboardMarkup(inline_keyboard=[[back_button()]])
    """
    return InlineKeyboardButton(text="🔵 Voltar", callback_data="back")

# ──────────────── Rotinas internas de limpeza por timeout ───────────────
async def _delete_menu_after_delay(
    bot: Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
    menu_timeout: int,
    message_timeout: int,
) -> None:
    """Espera ‹menu_timeout› s; se o menu ainda for o activo, apaga-o."""
    await asyncio.sleep(menu_timeout)

    # Confirma se este ainda é o menu activo
    data = await state.get_data()
    if data.get("menu_msg_id") != msg_id:
        return

    # Tenta remover a mensagem-menu
    try:
        await bot.delete_message(chat_id, msg_id)
    except exceptions.TelegramBadRequest:
        return  # já não existe

    # Envia aviso de inactividade
    try:
        warn = await bot.send_message(
            chat_id,
            f"⌛ O menu ficou inactivo durante {menu_timeout} s e foi fechado.\n"
            "Se precisar, utilize /start ou o botão «Menu» para reabri-lo.",
        )
    except exceptions.TelegramBadRequest:
        return

    # Limpa registo de menu activo
    await state.update_data(menu_msg_id=None, menu_chat_id=None)

    # Agenda remoção automática do aviso
    asyncio.create_task(
        _delete_inactivity_message(bot, chat_id, warn.message_id, message_timeout)
    )


async def _delete_inactivity_message(
    bot: Bot,
    chat_id: int,
    msg_id: int,
    delay: int,
) -> None:
    """Remove o aviso de inactividade após ‹delay› segundos."""
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, msg_id)
    except exceptions.TelegramBadRequest:
        pass

# ───────────────────────── API pública ─────────────────────────
def start_menu_timeout(
    bot: Bot,
    message: Message,
    state: FSMContext,
    menu_timeout: int = MENU_TIMEOUT,
    message_timeout: int = MESSAGE_TIMEOUT,
) -> None:
    """
    Agenda a remoção automática da mensagem-menu após ‹menu_timeout› segundos
    e, em seguida, a remoção da mensagem de aviso passado ‹message_timeout›.

    Deve ser chamada IMEDIATAMENTE depois de enviar/editar o menu e
    guardar em FSM:
        await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)
        start_menu_timeout(bot, msg, state)
    """
    asyncio.create_task(
        _delete_menu_after_delay(
            bot=bot,
            chat_id=message.chat.id,
            msg_id=message.message_id,
            state=state,
            menu_timeout=menu_timeout,
            message_timeout=message_timeout,
        )
    )
