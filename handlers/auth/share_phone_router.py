from __future__ import annotations

import os
import logging
from aiogram import Router, types, F
from redis.asyncio import Redis

from dal import (
    get_user_by_phone,
    link_telegram_id_to_user,
    get_user_roles,
)
from handlers.common.keyboards import (
    visitor_main_kb,
    regist_menu_kb,
)
from handlers.role_switch.role_switch_router import prompt_role_choice
from handlers.menu.dispatch import dispatch_role_menu

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB   = int(os.getenv("REDIS_DB", 0))

redis: Redis = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

logger = logging.getLogger(__name__)
router = Router(name="auth_share_phone")


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


@router.message(F.contact)
async def handle_shared_contact(message: types.Message) -> None:
    phone = message.contact.phone_number
    chat_id = message.chat.id
    tg_id = message.from_user.id

    user = await get_user_by_phone(phone)

    if user:
        # Linkar Telegram ID e continuar.
        await link_telegram_id_to_user(user.user_id, tg_id)
        roles = await get_user_roles(user.user_id)

        if len(roles) > 1:
            await prompt_role_choice(message, roles)
        elif roles:
            await dispatch_role_menu(message, roles[0])
        else:
            sent = await message.answer(
                "Encontrámos o seu registo mas ainda não tem perfil atribuído!",
                reply_markup=visitor_main_kb(),
            )
            await _replace_last_menu(sent)
        return

    # -------- Telefone não existe na BD --------
    sent = await message.answer(
        "📞 Obrigado! Ainda não temos o seu número no sistema. "
        "Como se quer registar?",
        reply_markup=regist_menu_kb(),
    )
    await _replace_last_menu(sent)
