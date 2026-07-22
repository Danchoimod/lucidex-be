from fastapi import APIRouter

from src.admin.routers import router as admin_router
from src.auth.routers import auth_router
from src.debug import router as debug_router
from src.invitation.router import router as invitation_router
from src.issuer.router import router as issuer_router
from src.owner.routers import router as owner_router
from src.verifier.router import router as verifier_router

api_v1_router = APIRouter()
api_v1_router.include_router(admin_router)
api_v1_router.include_router(issuer_router)
api_v1_router.include_router(owner_router)
api_v1_router.include_router(verifier_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(invitation_router)
api_v1_router.include_router(debug_router)
