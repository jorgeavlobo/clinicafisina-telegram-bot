from .accountant_handlers import router as accountant_router
from .administrator_handlers import router as administrator_router
from .auth_handlers import router as auth_router
from .caregiver_handlers import router as caregiver_router
from .patient_handlers import router as patient_router
from .physiotherapist_handlers import router as physiotherapist_router

all_routers = (
    accountant_router,
    administrator_router,
    auth_router,
    caregiver_router,
    patient_router,
    physiotherapist_router,
)
