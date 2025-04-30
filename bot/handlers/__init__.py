# bot/handlers/__init__.py
"""
Register all Telegram routers with the Dispatcher.

Order matters:
1)  system_handlers must be first (intercepts critical events).
2)  Authentication next.
3)  Then user-role-specific handlers.
4)  Debug handlers last (lowest priority).
"""

from typing import List

from aiogram import Dispatcher, Router

from .system_handlers import router as system_router
from .auth_handlers import router as auth_router
from .patient_handlers import router as patient_router
from .caregiver_handlers import router as caregiver_router
from .physiotherapist_handlers import router as physio_router
from .accountant_handlers import router as accountant_router
from .administrator_handlers import router as admin_router
from .debug_handlers import router as debug_router
from .add_user_handlers import router as add_user_router

routers: List[Router] = [
    system_router,
    auth_router,
    patient_router,
    caregiver_router,
    physio_router,
    accountant_router,
    admin_router,
    debug_router,
    add_user_router,
]

def register_routers(dp: Dispatcher) -> None:
    """Include all routers into the dispatcher in the correct order."""
    for router in routers:
        dp.include_router(router)
