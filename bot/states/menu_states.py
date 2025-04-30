# bot/states/menu_states.py
"""
Estados genéricos de navegação de menus.
"""

from aiogram.fsm.state import StatesGroup, State


class MenuStates(StatesGroup):
    WAIT_ROLE_CHOICE = State()   # à espera que o utilizador escolha o perfil
    MENU_ACTIVE      = State()   # qualquer menu principal visível (não-admin)
