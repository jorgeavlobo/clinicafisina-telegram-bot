# bot/middlewares/role_check.py
"""
Role-Check Middleware

1.  Vai à BD buscar o utilizador e injeta em `data`:
        data["user"]   – dict (linha completa de *users*)
        data["roles"]  – list[str] (nomes dos perfis em minúsculas)

2.  Bloqueia qualquer update que não tenha «active_role»
    gravado no FSM, EXCEPTO nos casos permitidos:

    •   Selector de perfis
          – estado MenuStates.WAIT_ROLE_CHOICE
          – callback data que começa por "role:"
    •   Fluxo de onboarding
          – AuthStates.WAITING_CONTACT
          – AuthStates.CONFIRMING_LINK
    •   Comandos utilitários /start  /admin  /whoami
"""

from __future__ import annotations

import logging
import time
from contextlib import suppress
from typing import Any, Dict, Callable, Awaitable, Tuple, List, Optional

from aiogram import BaseMiddleware, types, exceptions
from aiogram.fsm.context import FSMContext

from bot.database.connection import get_pool
from bot.database import queries as q
from bot.states.menu_states import MenuStates
from bot.states.auth_states import AuthStates     # ← necessário p/ onboarding

log = logging.getLogger(__name__)

# ───────────────────────── cache simples ─────────────────────────
_CACHE: Dict[int, Tuple[Optional[Dict[str, Any]], List[str], float]] = {}
_TTL = 60.0  # segundos

_ALLOWED_CMDS = {"/start", "/admin", "/whoami"}


class RoleCheckMiddleware(BaseMiddleware):
    async def __call__(                     # type: ignore[override]
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any],
    ) -> Any:

        tg_user: Optional[types.User] = data.get("event_from_user")

        # ───── 1. injeta (user, roles) com cache ─────
        if tg_user:
            user, roles = await self._get_user_and_roles(tg_user.id)
            if user:
                data["user"] = user
                data["roles"] = roles

        state: FSMContext = data["state"]
        cur_state = await state.get_state()

        # ───── 2. situações que passam SEM verificar role ─────
        if cur_state in (
            MenuStates.WAIT_ROLE_CHOICE.state,
            AuthStates.WAITING_CONTACT.state,
            AuthStates.CONFIRMING_LINK.state,
        ):
            return await handler(event, data)

        # clique em "role:xxx" dentro do selector
        if isinstance(event, types.CallbackQuery) and \
           event.data and event.data.startswith("role:"):
            return await handler(event, data)

        # comandos utilitários pré-login
        if isinstance(event, types.Message) and event.text:
            if event.text.split()[0].lower() in _ALLOWED_CMDS:
                return await handler(event, data)

        # ───── 3. exige active_role ─────
        if (await state.get_data()).get("active_role"):
            return await handler(event, data)

        # ───── 4. bloqueado ─────
        await self._deny(event)
        uid = tg_user.id if tg_user else "?"
        log.info("Blocado por falta de role activo – user %s", uid)
        return None

    # ───────────────── helpers ─────────────────
    async def _get_user_and_roles(
        self,
        tg_id: int,
    ) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        now = time.time()
        cached = _CACHE.get(tg_id)
        if cached and now - cached[2] < _TTL:
            return cached[0], cached[1]

        pool = await get_pool()
        user = await q.get_user_by_telegram_id(pool, tg_id)
        roles: List[str] = []
        if user:
            roles = [r.lower() for r in await q.get_user_roles(pool, user["user_id"])]

        _CACHE[tg_id] = (user, roles, now)
        return user, roles

    @staticmethod
    async def _deny(event: types.TelegramObject) -> None:
        text = (
            "Ainda não tem permissões atribuídas.\n"
            "Contacte a receção/administrador."
        )
        if isinstance(event, types.CallbackQuery):
            with suppress(exceptions.TelegramBadRequest):
                await event.answer(text, show_alert=True)
        elif isinstance(event, types.Message):
            with suppress(exceptions.TelegramBadRequest):
                await event.reply(text)
