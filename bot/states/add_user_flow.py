# bot/states/add_user_flow.py
"""
Estados do fluxo “Adicionar Utilizador”.

Esta máquina de estados cobre TODO o questionário até à confirmação final.
"""

from aiogram.fsm.state import State, StatesGroup


class AddUserFlow(StatesGroup):
    CHOOSE_TYPE          = State()   # escolha do tipo (Paciente, …) – já feita em administrator_handlers
    FIRST_NAME           = State()
    LAST_NAME            = State()
    DATE_OF_BIRTH        = State()
    PHONE_COUNTRY        = State()
    PHONE_NUMBER         = State()
    EMAIL                = State()
    WANT_ADDRESS         = State()
    ADDRESS_COUNTRY      = State()
    ADDRESS_POSTCODE     = State()
    ADDRESS_CITY         = State()
    ADDRESS_STREET       = State()
    ADDRESS_NUMBER       = State()
    WANT_TAX_ID          = State()
    TAX_COUNTRY          = State()
    TAX_NUMBER           = State()
    CONFIRM_DATA         = State()
    EDIT_FIELD           = State()   # escolha do campo a editar
