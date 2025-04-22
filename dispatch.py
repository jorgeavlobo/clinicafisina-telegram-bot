"""
Carrega todos os routers e garante que apenas 1 menu inline por chat fica activo.
"""

import logging
from aiogram import Dispatcher, types

_LOG = logging.getLogger(__name__)


class SingleMenuMiddleware:
    """Remove inline‑keyboard antigos no mesmo chat (anti‑lixo)."""

    async def __call__(self, handler, event: types.TelegramObject, data):
        if isinstance(event, types.Message):
            # se a mensagem contém KB inline – apaga a anterior
            if event.reply_markup and event.reply_markup.inline_keyboard:
                old = data["redis"].get(f"k:last_menu:{event.chat.id}")
                if old:
                    try:
                        await event.bot.edit_message_reply_markup(
                            chat_id=event.chat.id,
                            message_id=int(old),
                            reply_markup=None,
                        )
                    except Exception:
                        pass
                data["redis"].setex(
                    f"k:last_menu:{event.chat.id}", 3600, event.message_id
                )
        return await handler(event, data)


def build_dispatcher(storage) -> Dispatcher:
    from handlers import auth, registration  # noqa: circular‑import

    dp = Dispatcher(storage=storage)
    dp.message.middleware(SingleMenuMiddleware())

    # inclui sub‑pacotes recursivamente
    for sub in (auth, registration):
        for r in sub.__all__:
            _LOG.info("✅ Router registado: %s", r)
            dp.include_router(r)

    return dp
