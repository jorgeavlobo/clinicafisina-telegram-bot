# bot/middlewares/role_check.py
"""
Role-Check Middleware

1.  Vai buscar (user, roles) à BD e coloca em `data`:
        data["user"]   – linha completa da tabela *users*
        data["roles"]  – lista de perfis em minúsculas

2.  Bloqueia qualquer update sem «active_role» *excepto*:

    • Selector de perfis
        – estado MenuStates.WAIT_ROLE_CHOICE
        – callback data que começa por "role:"
    • Fluxo de onboarding
        – AuthStates.WAITING_CONTACT
        – AuthStates.CONFIRMING_LINK
    • Comandos utilitários
        – /start   (todas as variantes /start, /start@bot, /start abc …)
        – /admin
        – /whoami
"""

from __future__ import annotations

import logging
import time
from contextlib import suppress
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from aiogram import BaseMiddleware, exceptions, types
from aiogram.fsm.context import FSMContext

from bot.database import queries as q
from bot.database.connection import get_pool
from bot.states.auth_states import AuthStates
from bot.states.menu_states import MenuStates

log = logging.getLogger(__name__)

# ───────────────────────── cache muito simples ─────────────────────────
_CACHE: Dict[int, Tuple[Optional[Dict[str, Any]], List[str], float]] = {}
_TTL = 60.0  # segundos

_ALLOWED_CMDS = {"/admin", "/whoami"}          # /start é tratado à parte


class RoleCheckMiddleware(BaseMiddleware):
    async def __call__(                       # type: ignore[override]
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any],
    ) -> Any:

        # ───── 1) injeta (user, roles) usando cache ─────
        tg_user: Optional[types.User] = data.get("event_from_user")
        if tg_user:
            user, roles = await self._get_user_and_roles(tg_user.id)
            if user:
                data["user"] = user
                data["roles"] = roles

        state: FSMContext = data["state"]
        cur_state = await state.get_state()

        # ───── 2) situações sempre permitidas ─────
        if cur_state in (
            MenuStates.WAIT_ROLE_CHOICE.state,
            AuthStates.WAITING_CONTACT.state,
            AuthStates.CONFIRMING_LINK.state,
        ):
            return await handler(event, data)

        # clique em «role:xxx» dentro do selector
        if isinstance(event, types.CallbackQuery) and \
           event.data and event.data.startswith("role:"):
            return await handler(event, data)

        # comandos utilitários antes do login
        if isinstance(event, types.Message):
            raw = event.text or event.caption          # em canais pode vir como caption
            if raw:
                cmd = raw.split()[0].lower()

                # aceita qualquer /start ( /start , /start@bot , /start payload )
                if cmd.startswith("/start"):
                    return await handler(event, data)

                if cmd in _ALLOWED_CMDS:
                    return await handler(event, data)

        # ───── 3) exige active_role ─────
        if (await state.get_data()).get("active_role"):
            return await handler(event, data)

        # ───── 4) bloqueado ─────
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
