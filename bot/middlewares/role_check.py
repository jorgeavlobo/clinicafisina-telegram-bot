# bot/middlewares/role_check.py
"""
Garante que o utilizador tem um perfil ativo antes de continuar.

Se o FSM estiver em MenuStates.WAIT_ROLE_CHOICE (selector de perfil),
o middleware deixa passar – é exatamente esse handler que vai definir
o perfil ativo. Também ignora CallbackQueries cujo callback_data
comece por "role:" (botões do selector).
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict

from aiogram import BaseMiddleware, types
from aiogram.fsm.context import FSMContext

from bot.states.menu_states import MenuStates

log = logging.getLogger(__name__)

class RoleCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Any],
        event: types.TelegramObject,
        data: Dict[str, Any],
    ) -> Any:

        state: FSMContext = data["state"]

        # ------------------------------------------------------------------
        # • Permitir sempre o comando /start (início do fluxo de login).
        # • Se estamos no seletor de perfis, deixa passar.
        # • Se o callback é "role:xyz" (botão de seleção de perfil), deixa passar.
        # ------------------------------------------------------------------
        if isinstance(event, types.Message) and getattr(event, "text", "").startswith("/start"):
            return await handler(event, data)
        if await state.get_state() == MenuStates.WAIT_ROLE_CHOICE.state:
            return await handler(event, data)

        if isinstance(event, types.CallbackQuery) and \
           event.data and event.data.startswith("role:"):
            return await handler(event, data)

        # ------------------------------------------------------------------
        # Fora isso, exige perfil ativo no FSM.
        # ------------------------------------------------------------------
        user_data = await state.get_data()
        if not user_data.get("active_role"):
            if isinstance(event, types.CallbackQuery):
                await event.answer(
                    "Ainda não tem permissões atribuídas. "
                    "Contacte a receção/administração.",
                    show_alert=True,
                )
            elif isinstance(event, types.Message):
                await event.reply(
                    "Ainda não tem permissões atribuídas. "
                    "Contacte a receção/administração.",
                )
            log.info("Bloqueado por falta de role ativo – user %s", event.from_user.id)
            return

        return await handler(event, data)
