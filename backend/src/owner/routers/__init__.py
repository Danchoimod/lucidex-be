from fastapi import APIRouter

from src.credential.routers import router as credential_router
from src.ekyc.routers import router as ekyc_router
from src.owner.routers.link_settings import router as link_settings_router
from src.owner.routers.oauth_auth import router as oauth_auth_router
from src.owner.routers.oauth_qa import router as oauth_qa_router
from src.owner.routers.registration import router as registration_router
from src.owner.routers.verified_link import router as verified_link_router

router = APIRouter()
router.include_router(registration_router)
router.include_router(oauth_auth_router)
router.include_router(oauth_qa_router)
router.include_router(credential_router)
router.include_router(ekyc_router)
router.include_router(verified_link_router)
router.include_router(link_settings_router)

__all__ = ["router"]

