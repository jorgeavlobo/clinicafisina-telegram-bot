# bot/filters/role_filter.py
from typing import Iterable, List
from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject


class RoleFilter(BaseFilter):
    """
    Usa-se como  @router.message(RoleFilter("administrator"))
    ou           @router.message(RoleFilter(["patient", "caregiver"]))
    O handler só corre se pelo menos um dos roles requisitados
    existir na lista data["roles"] injectada pelo RoleCheckMiddleware.
    """

    def __init__(self, roles: str | Iterable[str]) -> None:
        if isinstance(roles, str):
            roles = [roles]
        self.required: List[str] = [r.lower() for r in roles]

    async def __call__(self, event: TelegramObject, data: dict) -> bool:
        user_roles: list[str] | None = data.get("roles")
        if not user_roles:
            return False                # utilizador não autenticado
        # comparação case-insensitive
        user_roles = [r.lower() for r in user_roles]
        return any(r in user_roles for r in self.required)
