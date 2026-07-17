from fastapi import APIRouter

from src.owner.routers.registration import router as registration_router
from src.owner.routers.login import router as login_router

router = APIRouter()
router.include_router(registration_router)
router.include_router(login_router)

__all__ = ["router"]
