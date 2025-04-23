"""
Agrupa todos os routers de handlers e disponibiliza
uma função `register_routers(dp)` para o módulo main.py.
"""

from aiogram import Dispatcher, Router

# importa os routers individuais (já devem existir)
from .auth_handlers import router as auth_router
from .patient_handlers import router as patient_router
from .caregiver_handlers import router as caregiver_router
from .physiotherapist_handlers import router as physio_router
from .accountant_handlers import router as accountant_router
from .administrator_handlers import router as admin_router

# Se algum ficheiro ainda não tem router, comenta a import ou cria stub

# lista ordenada (decisão tua)
all_routers: list[Router] = [
    auth_router,
    patient_router,
    caregiver_router,
    physio_router,
    accountant_router,
    admin_router,
]


def register_routers(dispatcher: Dispatcher) -> None:
    """Inclui todos os routers no dispatcher principal."""
    for r in all_routers:
        dispatcher.include_router(r)
