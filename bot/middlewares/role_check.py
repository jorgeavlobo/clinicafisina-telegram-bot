# bot/middlewares/role_check.py
"""
Middleware único que:
1) Obtém da BD o utilizador (se existir) e injeta em `data`:
       data["user"]  -> dict com o registo completo
       data["roles"] -> list[str] (lowercase)
2) Garante que há *role* activo no FSM antes de deixar o
   processamento prosseguir (excepto durante o selector).

⚠️  Tem de ser registado **antes** de qualquer Middleware que
    dependa de `data["roles"]` (ex.: RoleFilter).
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Callable

from aiogram import BaseMiddleware, types, exceptions
from aiogram.fsm.context import FSMContext

from bot.database.connection import get_pool
from bot.database import queries as q
from bot.states.menu_states import MenuStates

log = logging.getLogger(__name__)

# ───────────────── Cache muito simples (memória) ─────────────────
#   evita ir à BD a cada update; expira ao fim de 60 s
_CACHE: dict[int, tuple[dict[str, Any], list[str], float]] = {}
_TTL = 60.0  # segundos


class RoleCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Any],
        event: types.TelegramObject,
        data: Dict[str, Any],
    ) -> Any:

        tg_user = data.get("event_from_user")
        if tg_user:
            user, roles = await self._get_user_and_roles(tg_user.id)
            if user:
                data["user"] = user
                data["roles"] = roles

        # ───────────────── 1) permissões especiais ─────────────────
        state: FSMContext = data["state"]

        # a) estamos no selector de perfis → passa sempre
        if await state.get_state() == MenuStates.WAIT_ROLE_CHOICE.state:
            return await handler(event, data)

        # b) clique nos botões role:xxx do selector → passa
        if isinstance(event, types.CallbackQuery) and \
           event.data and event.data.startswith("role:"):
            return await handler(event, data)

        # ───────────────── 2) exige active_role ────────────────────
        if not (await state.get_data()).get("active_role"):
            await self._deny(event)
            log.info("Blocado por falta de role activo – user %s", tg_user.id if tg_user else "?")
            return

        # tudo OK → continua
        return await handler(event, data)

    # ───────────────── helpers ─────────────────
    async def _get_user_and_roles(self, tg_id: int) -> tuple[dict[str, Any] | None, list[str]]:
        now = time.time()
        cached = _CACHE.get(tg_id)
        if cached and now - cached[2] < _TTL:
            return cached[0], cached[1]

        pool = await get_pool()
        user = await q.get_user_by_telegram_id(pool, tg_id)
        roles: list[str] = []
        if user:
            roles = [r.lower() for r in await q.get_user_roles(pool, user["user_id"])]

        _CACHE[tg_id] = (user, roles, now)
        return user, roles

    @staticmethod
    async def _deny(event: types.TelegramObject) -> None:
        text = ("Ainda não tem permissões atribuídas.\n"
                "Contacte a receção/administrador.")
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
