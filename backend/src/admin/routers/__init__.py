from fastapi import APIRouter

from src.admin.routers.auth import router as auth_router
from src.admin.routers.health import router as health_router
from src.admin.routers.organizations import router as organizations_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(health_router)
router.include_router(organizations_router)

__all__ = ["router"]
