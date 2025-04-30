# bot/middlewares/active_menu_middleware.py
"""
Middleware para garantir que apenas o menu activo responde a interacções de inline keyboard.
Ignora cliques em botões de menus que já não estão activos, informando o utilizador.
"""
from aiogram import exceptions
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

class ActiveMenuMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: CallbackQuery, data: dict):
        # Obter contexto FSM para verificar mensagem de menu activa
        state: FSMContext = data.get("state")
        if state is None:
            # Sem FSM, prosseguir normalmente
            return await handler(event, data)
        state_data = await state.get_data()
        active_msg_id = state_data.get("menu_msg_id")
        active_chat_id = state_data.get("menu_chat_id")
        if not active_msg_id or not active_chat_id:
            # Se não há menu activo registado, ignorar a callback
            try:
                await event.answer("Este menu já não está activo.", show_alert=True)
            except exceptions.TelegramBadRequest:
                pass
            return  # não chama o handler seguinte
        # Verificar se a callback se refere à mensagem actualmente activa
        msg = event.message
        if msg is None or msg.message_id != active_msg_id or msg.chat.id != active_chat_id:
            # Mensagem não corresponde ao menu activo
            try:
                await event.answer("Este menu já não está activo.", show_alert=True)
            except exceptions.TelegramBadRequest:
                pass
            return  # descarta a callback sem processar handlers
        # Se passou nas verificações, continua para o próximo handler
        return await handler(event, data)
