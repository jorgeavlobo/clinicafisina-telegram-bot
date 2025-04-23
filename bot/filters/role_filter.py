# bot/filters/role_filter.py
from typing import Iterable, List
from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject


class RoleFilter(BaseFilter):
    """
    @router.message(RoleFilter("administrator"))
    @router.message(RoleFilter(["patient", "caregiver"]))
    Passa se qualquer dos papéis pedidos existir.
    """

    def __init__(self, roles: str | Iterable[str]) -> None:
        if isinstance(roles, str):
            roles = [roles]
        self.required: List[str] = [r.lower() for r in roles]

    async def __call__(              # <- event + kwargs (NÃO há 2.º posicional)
        self,
        event: TelegramObject,
        **data,
    ) -> bool:
        roles: list[str] | None = data.get("roles")   # vem do middleware
        if not roles:
            return False
        roles = [r.lower() for r in roles]
        return any(r in roles for r in self.required)
