from fastapi import APIRouter

from src.ekyc.routers.status import router as status_router
from src.ekyc.routers.verify import router as verify_router

router = APIRouter(prefix="/owner/ekyc", tags=["Owner"])
router.include_router(status_router)
router.include_router(verify_router)

__all__ = ["router"]
