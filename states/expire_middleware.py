"""Middleware to auto‑expire inline keyboards after X seconds (120 by default)."""

import asyncio, logging
from aiogram import types
from aiogram.dispatcher.middlewares.base import BaseMiddleware

log = logging.getLogger(__name__)

class ExpireInlineMiddleware(BaseMiddleware):
    def __init__(self, ttl: int = 120):
        self.ttl = ttl

    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            result = await handler(event, data)
            if event.reply_markup:
                asyncio.create_task(self._expire(event.bot, event.chat.id, event.message_id))
            return result
        return await handler(event, data)

    async def _expire(self, bot, chat_id: int, msg_id: int):
        await asyncio.sleep(self.ttl)
        try:
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg_id, reply_markup=None)
        except Exception:
            pass
