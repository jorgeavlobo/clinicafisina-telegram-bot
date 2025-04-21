from __future__ import annotations

import os
import logging
from aiogram import Router, F, types
from aiogram.filters import CommandStart
from redis.asyncio import Redis

from dal import (
    get_user_by_telegram_id,
    link_telegram_id_to_user,
    get_user_roles,
)
from handlers.common.keyboards import share_phone_kb, visitor_main_kb
from handlers.role_switch.role_switch_router import prompt_role_choice
from handlers.menu.dispatch import dispatch_role_menu

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB   = int(os.getenv("REDIS_DB", 0))

redis: Redis = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

logger = logging.getLogger(__name__)
router = Router(name="auth_start")


async def _replace_last_menu(message: types.Message) -> None:
    """
    Guarda/actualiza o último menu enviado a este utilizador
    para evitar acumular mensagens. TTL = 10 min.
    """
    key = f"last_menu:{message.from_user.id}"
    old_msg_id = await redis.get(key)
    if old_msg_id:
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=int(old_msg_id),
            )
        except Exception:
            pass
    await redis.set(key, message.message_id, ex=600)


@router.message(CommandStart())
async def cmd_start(message: types.Message) -> None:
    """
    Fluxo principal de /start

    1. Já conhecemos o telegram_user_id? -> vai buscar roles e mostra menu
    2. Caso contrário, pede nº de telemóvel.
    """
    tg_id = message.from_user.id
    user = await get_user_by_telegram_id(tg_id)

    if user:
        roles = await get_user_roles(user.user_id)
        if not roles:
            # Utilizador na BD mas sem role -> trata como visitante
            sent = await message.answer(
                "⚠️ O seu utilizador ainda não tem um perfil atribuído. "
                "Contacte a clínica.",
                reply_markup=visitor_main_kb(),
            )
            await _replace_last_menu(sent)
            return

        # Se o utilizador tiver vários roles pergunta qual quer usar
        if len(roles) > 1:
            await prompt_role_choice(message, roles)
        else:
            await dispatch_role_menu(message, roles[0])
        return

    # ---- utilizador desconhecido ----
    sent = await message.answer(
        "👋 Olá! Para continuar, partilhe o seu número de telemóvel "
        "tocando no botão abaixo:",
        reply_markup=share_phone_kb(),
    )
    await _replace_last_menu(sent)
