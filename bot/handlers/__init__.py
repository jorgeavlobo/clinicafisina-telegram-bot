from .auth import router as auth_router
from .accountant_handlers import router as accountant_router
from .patient_handlers import router as patient_router
from .caregiver_handlers import router as caregiver_router
from .physiotherapist_handlers import router as physiotherapist_router
from .administrator_handlers import router as administrator_router

all_routers = (
    auth_router,
    accountant_router,
    patient_router,
    caregiver_router,
    physiotherapist_router,
    administrator_router,
)
