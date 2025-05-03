# bot/middlewares/active_menu_middleware.py
"""
Guarantees the user can only interact with the *latest* active menu.

Behaviour
─────────
1. When the FSM stores `menu_msg_id/menu_chat_id`, **only** callbacks
   coming from that exact message are forwarded to the router handler.
   All others trigger a pop-up “Este menu já não está activo.” and the
   middleware fully removes the obsolete menu via
   `ui_helpers.close_menu_with_alert()`.

2. If *no* menu is registered:
      • During onboarding (AuthStates.WAITING_CONTACT /
        AuthStates.CONFIRMING_LINK) – callbacks are allowed.
      • Otherwise – same pop-up + cleanup as above.

Implementation note
───────────────────
Actual pop-up + deletion/blanking logic is centralised in
`bot.menus.ui_helpers.close_menu_with_alert`, keeping this middleware
thin and DRY.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, types
from aiogram.fsm.context import FSMContext

from bot.states.auth_states   import AuthStates
from bot.menus.ui_helpers     import close_menu_with_alert  # unified helper

log = logging.getLogger(__name__)


class ActiveMenuMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: types.CallbackQuery,
        data: dict[str, Any],
    ) -> Any:

        state: FSMContext | None = data.get("state")
        if state is None:                         # no FSM → nothing to enforce
            return await handler(event, data)

        stored        = await state.get_data()
        menu_msg_id   = stored.get("menu_msg_id")
        menu_chat_id  = stored.get("menu_chat_id")

        # ───────────── Case A – a menu is registered ─────────────
        if menu_msg_id and menu_chat_id:
            if (
                event.message
                and event.message.message_id == menu_msg_id
                and event.message.chat.id == menu_chat_id
            ):
                # The callback comes from the *active* keyboard → allow.
                return await handler(event, data)

            # Callback from an obsolete keyboard → deny & clean.
            await close_menu_with_alert(
                cb=event,
                alert_text="Este menu já não está activo.",
            )
            log.debug("Obsolete menu callback blocked (user=%s)", event.from_user.id)
            return

        # ───────────── Case B – no menu registered ───────────────
        cur_state = await state.get_state()
        if cur_state in (
            AuthStates.WAITING_CONTACT.state,
            AuthStates.CONFIRMING_LINK.state,
        ):
            # Onboarding flow → allow callback.
            return await handler(event, data)

        # Any other situation → treat as dead menu.
        await close_menu_with_alert(
            cb=event,
            alert_text="Este menu já não está activo.",
        )
        log.debug("Callback blocked (no menu) – user=%s", event.from_user.id)
        return
