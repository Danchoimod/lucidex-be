from fastapi import APIRouter

from src.auth.routers.auth import router as auth_main_router
from src.auth.routers.me import router as me_router

auth_router = APIRouter()
auth_router.include_router(auth_main_router)
auth_router.include_router(me_router)

__all__ = ["auth_router"]
