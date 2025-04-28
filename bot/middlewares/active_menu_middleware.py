# bot/middlewares/active_menu_middleware.py
from aiogram import exceptions
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.dispatcher.middlewares.base import BaseMiddleware

class ActiveMenuMiddleware(BaseMiddleware):
    """
    Middleware to ensure only active menus (inline keyboards) can be interacted with.
    """

    async def __call__(self, handler, event, data):
        # Only act if the event is a CallbackQuery
        if isinstance(event, CallbackQuery):
            cb = event
        elif hasattr(event, "callback_query") and event.callback_query:
            cb = event.callback_query
        else:
            return await handler(event, data)

        state: FSMContext = data.get("state")
        state_data = await state.get_data() if state else {}
        active_msg_id = state_data.get("menu_msg_id")
        active_chat_id = state_data.get("menu_chat_id")

        if not active_msg_id or not active_chat_id or \
           cb.message.message_id != active_msg_id or cb.message.chat.id != active_chat_id:
            try:
                await cb.message.delete()
            except exceptions.TelegramBadRequest:
                pass

            await cb.answer("⚠️ Este menu já não está activo.", show_alert=True)
            return  # ← NÃO fazemos raise! Apenas terminamos a função para bloquear

        # Menu válido → continuar
        return await handler(event, data)
