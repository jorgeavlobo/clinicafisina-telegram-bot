from .auth import router as auth_router
from .patient_handlers import router as patient_router
# …
from .accountant_handlers import router as accountant_router

all_routers = (
    auth_router,
    patient_router,
    # …
    accountant_router,
)
