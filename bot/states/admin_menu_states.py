# bot/states/admin_menu_states.py
from aiogram.fsm.state import State, StatesGroup


class AdminMenuStates(StatesGroup):
    """Estados de navegação do menu de administrador."""
    MAIN          = State()   # menu principal
    AGENDA        = State()   # submenu Agenda
    USERS         = State()   # submenu Utilizadores
    USERS_SEARCH  = State()   # placeholder
    USERS_ADD     = State()   # wrapper “Adicionar”
    MESSAGES      = State()   # submenu Mensagens   ←  **NOVO**


class AddUserStates(StatesGroup):
    """Sub-máquina do fluxo “Adicionar utilizador” (placeholder)."""
    CHOOSING_ROLE = State()
