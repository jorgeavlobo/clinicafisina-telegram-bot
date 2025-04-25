# bot/states/admin_menu_states.py
from aiogram.fsm.state import StatesGroup, State


class AdminMenuStates(StatesGroup):
    """
    Estados internos do menu de Administrador.
    MAIN  → teclado “Agenda / Utilizadores”
    AGENDA e USERS → sub-menus de 1.º nível
    USERS_SEARCH / USERS_ADD → ramificações próprias
    """
    MAIN         = State()   # menu principal
    AGENDA       = State()   # submenu Agenda
    USERS        = State()   # submenu Utilizadores
    USERS_SEARCH = State()   # (placeholder)
    USERS_ADD    = State()   # (placeholder)
