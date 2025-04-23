# bot/middlewares/role_check.py
"""
Middleware que carrega (user, roles) a partir do telegram_user_id, colocando:
    data["user"]   -> dict com o registo de users
    data["roles"]  -> lista[str] com os papéis
Se não houver ligação, apenas prossegue.
"""

from typing import Any, Dict
import logging

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.database.connection import get_pool
from bot.database import queries as q

log = logging.getLogger(__name__)


class RoleCheckMiddleware(BaseMiddleware):
    async def __call__(            # type: ignore[override]
        self,
        handler,
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")      # aiogram injeta aqui
        if tg_user:
            pool = await get_pool()
            user = await q.get_user_by_telegram_id(pool, tg_user.id)
            if user:
                roles = await q.get_user_roles(pool, user["user_id"])
                data["user"] = user
                data["roles"] = roles
                log.debug("RoleCheck: user %s roles=%s", user["user_id"], roles)
        # segue fluxo normal
        return await handler(event, data)
