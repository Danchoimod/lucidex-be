from fastapi import APIRouter

from app.api.v1.admin.router import router as admin_router
from app.api.v1.issuer.router import router as issuer_router
from app.api.v1.owner.router import router as owner_router
from app.api.v1.verifier.router import router as verifier_router

api_v1_router = APIRouter()
api_v1_router.include_router(admin_router)
api_v1_router.include_router(issuer_router)
api_v1_router.include_router(owner_router)
api_v1_router.include_router(verifier_router)

