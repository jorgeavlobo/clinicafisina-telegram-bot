# bot/states/__init__.py
"""
Re-exporta todos os grupos de estados para facilitar imports, permitindo:
    from bot.states import AuthStates, MenuStates, AdminMenuStates
"""

from .auth_states import AuthStates
from .menu_states import MenuStates
from .admin_menu_states import AdminMenuStates     # ← novo

__all__ = ["AuthStates", "MenuStates", "AdminMenuStates"]
