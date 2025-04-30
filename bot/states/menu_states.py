# bot/states/menu_states.py
"""
Estados globais de navegação de menus comuns a vários roles.
"""
from aiogram.fsm.state import State, StatesGroup

class MenuStates(StatesGroup):
    """
    Estados de menu comuns:
    WAIT_ROLE_CHOICE – estado de espera pela escolha de perfil (role) ativo.
    """
    WAIT_ROLE_CHOICE = State()
