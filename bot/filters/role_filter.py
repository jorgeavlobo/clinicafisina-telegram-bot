# bot/filters/role_filter.py
from typing import Iterable, List
from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject


class RoleFilter(BaseFilter):
    """
    Uso:
        @router.message(RoleFilter("administrator"))
        @router.message(RoleFilter(["patient", "caregiver"]))
    O filtro passa se pelo menos um dos papéis pedidos existir
    na lista 'roles' injectada pelo RoleCheckMiddleware.
    """

    def __init__(self, roles: str | Iterable[str]) -> None:
        if isinstance(roles, str):
            roles = [roles]
        self.required: List[str] = [r.lower() for r in roles]

    async def __call__(
        self,
        event: TelegramObject,
        roles: list[str] | None = None,    # ← chega como kw-arg individual
        **kwargs,
    ) -> bool:
        if not roles:
            return False                  # utilizador não autenticado
        roles = [r.lower() for r in roles]
        return any(r in roles for r in self.required)
