# bot/handlers/__init__.py
"""
Regista todos os routers, assegurando que:
1)  menu_guard é o PRIMEIRO (intercepta cliques em menus antigos);
2)  system_handlers continua a correr antes dos específicos;
3)  restante ordem mantém-se.
"""
from aiogram import Dispatcher, Router

from .menu_guard               import router as menu_guard_router   # 🆕 1.º!
from .system_handlers          import router as system_router
from .auth_handlers            import router as auth_router
from .patient_handlers         import router as patient_router
from .caregiver_handlers       import router as caregiver_router
from .physiotherapist_handlers import router as physio_router
from .accountant_handlers      import router as accountant_router
from .administrator_handlers   import router as admin_router
from .debug_handlers           import router as debug_router

_all: list[Router] = [
    menu_guard_router,   # <- sempre primeiro
    system_router,
    auth_router,
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
