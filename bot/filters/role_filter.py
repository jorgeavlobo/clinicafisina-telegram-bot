# bot/filters/role_filter.py
from typing import Iterable, List, Any
from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject


class RoleFilter(BaseFilter):
    """
    Exemplo:
        @router.message(RoleFilter("administrator"))
        @router.message(RoleFilter(["patient", "caregiver"]))
    Passa se pelo menos um papel pedido existir em data["roles"].
    """

    def __init__(self, roles: str | Iterable[str]) -> None:
        if isinstance(roles, str):
            roles = [roles]
        self.required: List[str] = [r.lower() for r in roles]

    async def __call__(           # <- kwargs!
        self,
        event: TelegramObject,
        **data: Any,
    ) -> bool:
        roles: list[str] | None = data.get("roles")
        if not roles:
            return False
        roles = [r.lower() for r in roles]
        return any(r in roles for r in self.required)
