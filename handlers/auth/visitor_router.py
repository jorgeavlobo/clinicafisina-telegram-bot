import asyncio, logging
from aiogram import Router, types
from handlers.common.keyboards import visitor_main_kb

log = logging.getLogger(__name__)
router = Router(name="auth_visitor")

@router.message()
async def visitor_menu(msg: types.Message):
    reply = await msg.answer(
        "⚠️ Não consigo identificar‑te.
"
        "Ainda assim, podes ver alguma informação pública 👇",
        reply_markup=visitor_main_kb()
    )
    async def expire(mid):
        await asyncio.sleep(120)
        try:
            await msg.bot.edit_message_reply_markup(chat_id=msg.chat.id, message_id=mid, reply_markup=None)
        except Exception:
            pass
    asyncio.create_task(expire(reply.message_id))
