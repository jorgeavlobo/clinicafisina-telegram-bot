# bot/middlewares/role_check.py

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class RoleCheckMiddleware(BaseMiddleware):
    """
    Middleware placeholder.
    No estado actual só passa o controlo ao handler seguinte.
    Futuramente vai:
      • Ler o telegram_user_id
      • Consultar a BD → roles
      • Colocar 'role' em data dict
      • Bloquear acesso se necessário
    """

    async def __call__(  # aiogram v3 signature
        self,
        handler,
        event: TelegramObject,
        data: dict,
    ):
        # Aqui poderás pôr lógica real depois
        return await handler(event, data)
