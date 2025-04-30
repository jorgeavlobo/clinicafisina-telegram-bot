# bot/middlewares/role_check.py
"""
Role-Check Middleware

1.  Obtém da BD o utilizador e injeta em `data`:
        data["user"]   – dict  (registo completo de *users*)
        data["roles"]  – list[str] (nomes dos perfis em minúsculas)

2.  Bloqueia o processamento se o utilizador ainda não tiver
    «active_role» no FSM, **excepto** nos casos permitidos:

    • Estado actual == MenuStates.WAIT_ROLE_CHOICE
    • CallbackQuery cujo data começa por "role:"
    • Comandos      /start  /admin  /whoami
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, Awaitable, Tuple, List, Optional

from aiogram import BaseMiddleware, types, exceptions
from aiogram.fsm.context import FSMContext

from bot.database.connection import get_pool
from bot.database import queries as q
from bot.states.menu_states import MenuStates

log = logging.getLogger(__name__)

# ————————————————————————————————————————————————————————
#  Pequeno cache em memória  (user, roles)  →  TTL 60 s
# ————————————————————————————————————————————————————————
_CACHE: Dict[int, Tuple[Optional[Dict[str, Any]], List[str], float]] = {}
_TTL = 60.0  # seg.

_ALLOWED_CMDS = {"/start", "/admin", "/whoami"}


class RoleCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.T], Awaitable[Any]],            # type: ignore[name-defined]
        event:   types.T,                                        # type: ignore[name-defined]
        data:    Dict[str, Any],
    ) -> Any:                                                    # type: ignore[override]
        tg_user: Optional[types.User] = data.get("event_from_user")

        # ────────────────── 1. injeta user / roles (com cache) ──────────────────
        if tg_user:
            user, roles = await self._get_user_and_roles(tg_user.id)
            if user:
                data["user"]  = user
                data["roles"] = roles

        state: FSMContext = data["state"]

        # ────────────────── 2. casos sempre permitidos ──────────────────
        cur_state = await state.get_state()

        # a) selector ainda activo
        if cur_state == MenuStates.WAIT_ROLE_CHOICE.state:
            return await handler(event, data)

        # b) clique em «role:xxx»
        if isinstance(event, types.CallbackQuery) and event.data and event.data.startswith("role:"):
            return await handler(event, data)

        # c) comandos de utilidade
        if isinstance(event, types.Message) and event.text:
            cmd = event.text.split()[0].lower()
            if cmd in _ALLOWED_CMDS:
                return await handler(event, data)

        # ────────────────── 3. verifica se já há role activo ──────────────────
        if (await state.get_data()).get("active_role"):
            return await handler(event, data)

        # ────────────────── 4. bloqueado ──────────────────
        await self._deny(event)
        uid = tg_user.id if tg_user else "?"
        log.info("Blocado por falta de role activo – user %s", uid)
        return None

    # —————————————————— helpers ——————————————————
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
            try:
                await event.answer(text, show_alert=True)
            except exceptions.TelegramBadRequest:
                pass
        elif isinstance(event, types.Message):
            try:
                await event.reply(text)
            except exceptions.TelegramBadRequest:
                pass
