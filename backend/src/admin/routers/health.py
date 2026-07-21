from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/health",
    summary="Check admin API health",
    description=(
        "Allows clients to check whether the Admin API routes are available. "
        "Returns a success response when the portal router is reachable."
    ),
)
async def health_check():
    return {
        "success": True,
        "data": {"message": "Admin portal is running."},
        "message": "OK",
        "error_code": None,
    }
