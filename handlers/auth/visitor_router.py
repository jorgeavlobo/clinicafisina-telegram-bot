from __future__ import annotations

import os
import logging
from aiogram import Router, types
from redis.asyncio import Redis

from handlers.common.keyboards import (
    visitor_main_kb,
    share_phone_kb,
)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB   = int(os.getenv("REDIS_DB", 0))

redis: Redis = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

logger = logging.getLogger(__name__)
router = Router(name="auth_visitor")


async def _replace_last_menu(message: types.Message) -> None:
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


@router.message(lambda m: m.text and m.text.lower() == "voltar")
async def go_back(message: types.Message) -> None:
    """
    Exemplo de botão “Voltar” que devolve ao menu visitante.
    """
    sent = await message.answer(
        "🔙 Menu principal (visitante):",
        reply_markup=visitor_main_kb(),
    )
    await _replace_last_menu(sent)


@router.message()
async def fallback_visitor(message: types.Message) -> None:
    """
    Qualquer outra mensagem de visitante não identificado.
    Sugere partilhar contacto ou ver informações públicas.
    """
    sent = await message.answer(
        "Poderá partilhar o seu contacto para procurarmos o seu registo, "
        "ou consultar informações públicas:",
        reply_markup=share_phone_kb(),
    )
    await _replace_last_menu(sent)
