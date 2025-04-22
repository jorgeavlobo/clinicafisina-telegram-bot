# handlers/auth/visitor_router.py
import asyncio
from aiogram import Router, types, F

# ← agora o import vem do módulo comum
from handlers.common.keyboards import visitor_main_kb

router = Router(name="auth_visitor")


@router.message(
    (F.state == None) & F.text  # Qualquer texto enquanto não autenticado
)
async def visitor_menu(message: types.Message) -> None:
    reply = await message.answer(
        "⚠️ Não consigo identificar‑te.\n"
        "Ainda assim, podes ver alguma informação pública 👇",
        reply_markup=visitor_main_kb()           # ← teclado actualizado
    )

    # Apaga o teclado após 2 min para evitar clutter
    async def _expire(msg_id: int):
        await asyncio.sleep(120)
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=msg_id,
                reply_markup=None
            )
        except Exception:
            # A mensagem pode já ter sido removida pelo utilizador ou por outra lógica
            pass

    asyncio.create_task(_expire(reply.message_id))
