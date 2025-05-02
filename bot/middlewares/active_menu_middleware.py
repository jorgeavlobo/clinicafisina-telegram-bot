# bot/middlewares/active_menu_middleware.py
"""
Bloqueia cliques em inline-keyboards que já não estão activos.

Regra geral o FSM guarda:
    • menu_msg_id
    • menu_chat_id

O middleware aceita callbacks que provenham **exactamente** dessa
mensagem e bloqueia todos os outros, devolvendo o alerta
«Este menu já não está activo.».

*Extra*: se não existir nenhum menu registado (campos a `None`)
bloqueia apenas callbacks originados por teclados de *selector* de
perfil («role:…»), deixando passar os restantes (ex.: confirmação
“link_yes / link_no” durante o onboarding).
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
        if state is None:                         # sem contexto FSM
            return await handler(event, data)

        stored = await state.get_data()
        menu_msg_id  = stored.get("menu_msg_id")
        menu_chat_id = stored.get("menu_chat_id")

        # ───── caso 1: NÃO há menu registado ─────
        if not menu_msg_id or not menu_chat_id:
            # apenas bloqueia callbacks do selector «role:…»
            if event.data and event.data.startswith("role:"):
                await event.answer("Este menu já não está activo.", show_alert=True)
                return
            # outros callbacks (p.ex. onboarding) passam
            return await handler(event, data)

        # ───── caso 2: há um menu registado ─────
        if (
            event.message
            and event.message.message_id == menu_msg_id
            and event.message.chat.id == menu_chat_id
        ):
            # é o teclado activo → deixa passar
            return await handler(event, data)

        # veio de um teclado antigo → bloqueia
        await event.answer("Este menu já não está activo.", show_alert=True)
        return
