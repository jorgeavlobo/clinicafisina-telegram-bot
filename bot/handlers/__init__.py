# bot/handlers/__init__.py
"""
Regista, na ordem correcta, todos os routers da aplicação.

NOTA: `menu_guard.py` é apenas um módulo utilitário (não contém Router),
por isso **NÃO** deve ser importado aqui. A tentativa anterior de
`from .menu_guard import router` provocava o erro observado.
"""
from aiogram import Dispatcher, Router

from .auth_handlers import router as auth_router
from .system_handlers import router as system_router
from .patient_handlers import router as patient_router
from .caregiver_handlers import router as caregiver_router
from .physiotherapist_handlers import router as physio_router
from .accountant_handlers import router as accountant_router
from .administrator_handlers import router as admin_router
from .debug_handlers import router as debug_router

_all: list[Router] = [
    auth_router,
    system_router,
    patient_router,
    caregiver_router,
    physio_router,
    accountant_router,
    admin_router,
    debug_router,
]

def register_routers(dp: Dispatcher) -> None:
    for r in _all:
        dp.include_router(r)
