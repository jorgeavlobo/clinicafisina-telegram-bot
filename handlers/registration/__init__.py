# handlers/registration/__init__.py
from .regist_menu_router import router as regist_menu_router
from .regist_patient_router import router as regist_patient_router
from .regist_caregiver_router import router as regist_caregiver_router

__all__ = (
    "regist_menu_router",
    "regist_patient_router",
    "regist_caregiver_router",
)
