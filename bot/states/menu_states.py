# bot/states/menu_states.py
from aiogram.fsm.state import State, StatesGroup

class MenuStates(StatesGroup):
    WAIT_ROLE_CHOICE = State()      # quando o utilizador tem >1 role
