# bot/states/__init__.py
"""
Re-exporta todos os grupos de estados para facilitar imports:
    from bot.states import AuthStates, MenuStates
"""

from .auth_states import AuthStates
from .menu_states import MenuStates

__all__ = ["AuthStates", "MenuStates"]
