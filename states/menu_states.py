from aiogram.fsm.state import State, StatesGroup


class MenuStates(StatesGroup):
    main = State()

    # inline sub‑menus
    option1 = State()
    option2 = State()
    option3 = State()
    option4 = State()

    # reply‑keyboard submenu for 4.2
    option42 = State()
