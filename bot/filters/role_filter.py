# bot/filters/role_filter.py
from typing import Iterable, List
from aiogram.filters import Filter
from aiogram.types import Message


class RoleFilter(Filter):
    """
    Uso:
        @router.message(RoleFilter("administrator"))
        @router.message(RoleFilter(["patient", "caregiver"]))
    O handler só passa se o utilizador tiver (≥1) dos papéis indicados.
    """

    def __init__(self, roles: str | Iterable[str]) -> None:
        if isinstance(roles, str):
            roles = [roles]
        self.required: List[str] = [r.lower() for r in roles]

    async def __call__(self, event: Message, roles: List[str] | None = None) -> bool:
        if not roles:
            return False
        roles = [r.lower() for r in roles]
        return any(r in roles for r in self.required)
