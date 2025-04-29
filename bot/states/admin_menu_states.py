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
    USERS_ADD    = State()   # (placeholder, not used directly for FSM transitions)

# Estados para o fluxo de adição de utilizador (Admin Menu - Fase 1)
class AddUserStates(StatesGroup):
    """
    FSM states for the Admin 'Add User' flow.
    This includes sequential prompts for user details and confirmation.
    """
    CHOOSING_ROLE = State()   # choosing user type via inline buttons
    FIRST_NAME    = State()   # waiting for first name(s)
    LAST_NAME     = State()   # waiting for last name(s)
    BIRTHDATE     = State()   # waiting for date of birth
    PHONE         = State()   # waiting for phone number
    EMAIL         = State()   # waiting for email address
    ADDRESS       = State()   # waiting for address (optional)
    NIF           = State()   # waiting for NIF (optional)
    CONFIRM       = State()   # showing summary and waiting for confirm/edit/cancel (inline)
    EDIT_FIELD    = State()   # choosing which field to edit (inline list)
