# bot/filters/role_filter.py
from typing import Iterable, List
from aiogram.filters import Filter        # ⬅️  Importa Filter
from aiogram.types import Message         # ou TelegramObject


class RoleFilter(Filter):
    """
    Uso:
        @router.message(RoleFilter("administrator"))
        @router.message(RoleFilter(["patient", "caregiver"]))
    O handler só passa se o utilizador tiver (pelo menos) um dos papéis.
    """

    def __init__(self, roles: str | Iterable[str]) -> None:
        if isinstance(roles, str):
            roles = [roles]
        self.required: List[str] = [r.lower() for r in roles]

    async def __call__(
        self,
        event: Message,                     # 1.º argumento -> update
        roles: list[str] | None = None,    # este nome TEM de coincidir
    ) -> bool:
        if not roles:                      # middleware não injectou? -> falha
            return False
        roles = [r.lower() for r in roles]
        return any(r in roles for r in self.required)
