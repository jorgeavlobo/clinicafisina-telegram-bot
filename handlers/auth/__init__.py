# handlers/auth/__init__.py
from .start_router import router as start_router
from .share_phone_router import router as share_phone_router
from .visitor_router import router as visitor_router

__all__ = (
    start_router,
    share_phone_router,
    visitor_router,
)
