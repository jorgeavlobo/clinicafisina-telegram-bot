# bot/filters/role_filter.py
from typing import Iterable, List
from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject


class RoleFilter(BaseFilter):
    """
    Uso:
        @router.message(RoleFilter("administrator"))
        @router.message(RoleFilter(["patient", "caregiver"]))
    """

    def __init__(self, roles: str | Iterable[str]) -> None:
        if isinstance(roles, str):
            roles = [roles]
        self.required: List[str] = [r.lower() for r in roles]

    async def __call__(         # ← dois posicionais: event, data
        self,
        event: TelegramObject,
        data: dict,             # dict injectado pelo middleware
        **kwargs,
    ) -> bool:
        roles: list[str] | None = data.get("roles")
        if not roles:
            return False
        roles = [r.lower() for r in roles]
        return any(r in roles for r in self.required)
