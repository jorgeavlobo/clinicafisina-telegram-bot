# bot/handlers/__init__.py
"""
Regista todos os routers no Dispatcher.
A ordem importa (do mais geral para o mais específico).
"""

from typing import List
from aiogram import Dispatcher, Router

from .system_handlers       import router as system_router
from .auth_handlers         import router as auth_router
from .role_choice_handlers  import router as role_choice_router   # ← NOVO
from .patient_handlers      import router as patient_router
from .caregiver_handlers    import router as caregiver_router
from .physiotherapist_handlers import router as physio_router
from .accountant_handlers   import router as accountant_router
from .administrator_handlers import router as admin_router
from .add_user_handlers     import router as add_user_router
from .debug_handlers        import router as debug_router
from .debug_fsm_handlers import router as debug_fsm_router

routers: List[Router] = [
    system_router,
    auth_router,
    role_choice_router,      # tem de vir ANTES dos handlers de cada perfil
    patient_router,
    caregiver_router,
    physio_router,
    accountant_router,
    admin_router,
    add_user_router,
    debug_router,
    debug_fsm_router,
]

def register_routers(dp: Dispatcher) -> None:
    for r in routers:
        dp.include_router(r)
