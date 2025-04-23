# bot/middlewares/role_check.py
"""
Middleware que liga telegram_user_id ao registo da BD e injeta:
    data["user"]   -> dict com o registo completo
    data["roles"]  -> list[str] (minúsculas)
"""

from typing import Any, Dict, List
import logging

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.database.connection import get_pool      # usa pool global
from bot.database import queries as q

log = logging.getLogger(__name__)


class RoleCheckMiddleware(BaseMiddleware):
    async def __call__(  # type: ignore[override]
        self,
        handler,
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user:
            pool = await get_pool()
            user = await q.get_user_by_telegram_id(pool, tg_user.id)
            if user:
                roles: List[str] = await q.get_user_roles(pool, user["user_id"])
                roles = [r.lower() for r in roles]
                data["user"] = user
                data["roles"] = roles
                log.debug("RoleCheck: user %s roles=%s", user["user_id"], roles)

        return await handler(event, data)
