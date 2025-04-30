# bot/states/add_user_flow.py
"""
Máquina de estados completa para o fluxo “Adicionar Utilizador”.

Inclui agora também o passo CHOOSING_ROLE, antes separado em AddUserStates.
"""

from aiogram.fsm.state import State, StatesGroup


class AddUserFlow(StatesGroup):
    CHOOSING_ROLE       = State()   # Paciente / Cuidador / …
    FIRST_NAME          = State()
    LAST_NAME           = State()
    DATE_OF_BIRTH       = State()
    PHONE_COUNTRY       = State()
    PHONE_NUMBER        = State()
    EMAIL               = State()
    WANT_ADDRESS        = State()
    ADDRESS_COUNTRY     = State()
    ADDRESS_POSTCODE    = State()
    ADDRESS_CITY        = State()
    ADDRESS_STREET      = State()
    ADDRESS_NUMBER      = State()
    WANT_TAX_ID         = State()
    TAX_COUNTRY         = State()
    TAX_NUMBER          = State()
    CONFIRM_DATA        = State()
    EDIT_FIELD          = State()
