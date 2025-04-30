# bot/states/admin_menu_states.py
from aiogram.fsm.state import State, StatesGroup


class AdminMenuStates(StatesGroup):
    """Estados de navegação do menu de administrador."""
    MAIN          = State()   # Menu principal "Administrador"
    AGENDA        = State()   # Sub-menu Agenda
    USERS         = State()   # Sub-menu Utilizadores
    MESSAGES      = State()   # Sub-menu Mensagens  ← NOVO
    USERS_SEARCH  = State()   # Fluxo Procurar (placeholder)
    USERS_ADD     = State()   # Fluxo Adicionar – estado "wrapper"


class AddUserStates(StatesGroup):
    """
    Sub-máquina de estados (filha de USERS_ADD) para o fluxo “Adicionar Utilizador”.
    Nesta fase só precisamos escolher o tipo de utilizador; outros passos virão depois.
    """
    CHOOSING_ROLE = State()
    # (fases seguintes virão aqui: FIRST_NAME, LAST_NAME, …)
