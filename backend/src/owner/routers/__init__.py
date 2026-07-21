from fastapi import APIRouter

from src.owner.routers.registration import router as registration_router

router = APIRouter()
router.include_router(registration_router)

__all__ = ["router"]
