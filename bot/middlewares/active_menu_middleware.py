# bot/middlewares/active_menu_middleware.py
"""
Garante que o utilizador só interage com o *último* menu activo.

Regras
──────
1.  Se o FSM tiver `menu_msg_id`/`menu_chat_id`, **apenas** callbacks
    dessa mensagem são entregues ao handler; todos os outros recebem
    pop-up «Este menu já não está activo.».

2.  Se *não* existir menu registado:
       • Durante o onboarding (AuthStates.WAITING_CONTACT /
         AuthStates.CONFIRMING_LINK) – callbacks são permitidos.
       • Caso contrário – qualquer callback recebe o mesmo pop-up
         _e_ o middleware tenta apagar (ou pelo menos desactivar)
         o teclado que originou o clique.

A limpeza imediata evita que o utilizador volte a clicar num teclado
antigo que ficou esquecido no histórico.
"""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, types, exceptions
from aiogram.fsm.context import FSMContext

from bot.states.auth_states import AuthStates

log = logging.getLogger(__name__)


class ActiveMenuMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: types.CallbackQuery,
        data: dict[str, Any],
    ) -> Any:

        state: FSMContext | None = data.get("state")
        if state is None:                     # sem FSM → nada a fazer
            return await handler(event, data)

        stored = await state.get_data()
        menu_msg_id  = stored.get("menu_msg_id")
        menu_chat_id = stored.get("menu_chat_id")

        # ───────────────────────── caso A – há menu registado ─────────────────────────
        if menu_msg_id and menu_chat_id:
            if (
                event.message
                and event.message.message_id == menu_msg_id
                and event.message.chat.id == menu_chat_id
            ):
                # é o teclado activo → deixa passar
                return await handler(event, data)

            # veio de teclado antigo → bloqueia + tenta limpar
            await self._deny_and_cleanup(event)
            return

        # ───────────────────────── caso B – nenhum menu registado ─────────────────────
        cur_state = await state.get_state()
        if cur_state in (
            AuthStates.WAITING_CONTACT.state,
            AuthStates.CONFIRMING_LINK.state,
        ):
            # estamos no fluxo de onboarding → deixar passar
            return await handler(event, data)

        # fora do onboarding → tratar como menu morto
        await self._deny_and_cleanup(event)
        return

    # ------------------------------------------------------------------------
    @staticmethod
    async def _deny_and_cleanup(cb: types.CallbackQuery) -> None:
        """
        Mostra pop-up «menu inactivo» e tenta desactivar o teclado que
        originou o callback (delete ou, em último caso, remove reply_markup).
        """
        with suppress(exceptions.TelegramBadRequest):
            await cb.answer("Este menu já não está activo.", show_alert=True)

        # tentar apagar a mensagem inteira…
        deleted = False
        if cb.message:
            try:
                await cb.message.delete()
                deleted = True
            except exceptions.TelegramBadRequest:
                deleted = False

            # …ou pelo menos remover o teclado
            if not deleted:
                with suppress(exceptions.TelegramBadRequest):
                    await cb.message.edit_reply_markup(reply_markup=None)

        log.debug("Callback de menu inactivo bloqueado (user=%s)", cb.from_user.id)
