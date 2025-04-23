from aiogram.fsm.state import StatesGroup, State

class AuthStates(StatesGroup):
    WAITING_CONTACT = State()    # bot pede nº de telefone
    CONFIRMING_LINK = State()    # “Encontrámos perfil X — confirmar ligação?”
