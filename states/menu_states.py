from aiogram.fsm.state import State, StatesGroup

class MenuStates(StatesGroup):
    """FSM States for the multi-level menu."""
    main = State()      # Main menu state
    option1 = State()   # Submenu for Option 1
    option2 = State()   # Submenu for Option 2
    option3 = State()   # Submenu for Option 3
    option4 = State()   # Submenu for Option 4
