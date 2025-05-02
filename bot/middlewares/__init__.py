# bot/middlewares/__init__.py
"""
Exporta os middlewares registados na aplicação.
"""

from .role_check_middleware     import RoleCheckMiddleware
from .active_menu_middleware    import ActiveMenuMiddleware

__all__ = [
    "RoleCheckMiddleware",
    "ActiveMenuMiddleware",
]
