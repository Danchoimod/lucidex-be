from fastapi import APIRouter

from src.credential.routers.claim_credential import router as claim_router
from src.credential.routers.get_credential import router as detail_router
from src.credential.routers.list_credentials import router as list_router

router = APIRouter(prefix="/owner", tags=["Owner"])
router.include_router(list_router)
router.include_router(detail_router)
router.include_router(claim_router)

__all__ = ["router"]
