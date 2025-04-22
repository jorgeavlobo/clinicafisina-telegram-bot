"""
Intercepta qualquer texto enquanto o user ainda não foi identificado.
"""

import asyncio
import logging

from aiogram import Router, types, F
from handlers.common.keyboards import visitor_main_kb

logger = logging.getLogger(__name__)
router = Router(name="auth_visitor")


@router.message((F.state == None) & F.text)
async def visitor_menu(message: types.Message) -> None:
    reply = await message.answer(
        "⚠️ Não consigo identificar‑te.\n"
        "Ainda assim, podes ver alguma informação pública 👇",
        reply_markup=visitor_main_kb()
    )

    # Apaga o teclado após 2 min para não poluir o chat
    async def _expire(msg_id: int) -> None:
        await asyncio.sleep(120)
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=msg_id,
                reply_markup=None
            )
        except Exception:
            pass

    asyncio.create_task(_expire(reply.message_id))
