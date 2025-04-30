# bot/middlewares/active_menu_middleware.py
"""
Permite callbacks apenas no inline-keyboard actualmente activo.

Quando um handler grava em FSM:
    • menu_msg_id
    • menu_chat_id
o middleware aceita cliques provenientes dessa mensagem e bloqueia todos
os outros, devolvendo o alerta «Este menu já não está activo.»
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, types
from aiogram.fsm.context import FSMContext


class ActiveMenuMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: types.CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        state: FSMContext | None = data.get("state")
        if state is None:                      # sem contexto FSM
            return await handler(event, data)

        stored = await state.get_data()
        menu_msg_id = stored.get("menu_msg_id")
        menu_chat_id = stored.get("menu_chat_id")

        # se não houver menu registado deixa passar
        if not menu_msg_id or not menu_chat_id:
            return await handler(event, data)

        # só permite se o callback for do menu activo
        if (
            event.message
            and event.message.message_id == menu_msg_id
            and event.message.chat.id == menu_chat_id
        ):
            return await handler(event, data)

        # caso contrário bloqueia e avisa
        await event.answer("Este menu já não está activo.", show_alert=True)
        return
