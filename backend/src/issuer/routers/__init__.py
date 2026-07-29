"""Routers package for issuer module."""

from fastapi import APIRouter

from src.issuer.routers.credentials import router as credentials_router
from src.issuer.routers.health import router as health_router
from src.issuer.routers.invitation import router as invitation_router
from src.issuer.routers.registration import router as registration_router

router = APIRouter(prefix="/issuer", tags=["Issuer"])
router.include_router(health_router)
router.include_router(registration_router)
router.include_router(invitation_router)
router.include_router(credentials_router)

__all__ = ["router"]
