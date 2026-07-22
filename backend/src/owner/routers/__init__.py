from fastapi import APIRouter

from src.owner.routers.oauth_auth import router as oauth_auth_router
from src.owner.routers.oauth_qa import router as oauth_qa_router
from src.owner.routers.registration import router as registration_router

router = APIRouter()
router.include_router(registration_router)
router.include_router(oauth_auth_router)
router.include_router(oauth_qa_router)

__all__ = ["router"]
