# handlers/auth/visitor_router.py
import asyncio
from aiogram import Router, types, F
from keyboards import kb_visitor_menu

router = Router(name="auth_visitor")


@router.message(
    (F.state == None) & F.text,   # Qualquer texto enquanto não autenticado
)
async def visitor_menu(message: types.Message) -> None:
    reply = await message.answer(
        "⚠️ Não consigo identificar‑te.\n"
        "Ainda assim, podes ver alguma informação pública 👇",
        reply_markup=kb_visitor_menu()
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
            pass   # Mensagem já pode ter sido apagada

    asyncio.create_task(_expire(reply.message_id))
