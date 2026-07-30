"""Health check router for issuer API."""

from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/health",
    summary="Check issuer API health",
    description=(
        "Allows clients to check whether the Issuer API routes are available. "
        "Returns a success response when the portal router is reachable."
    ),
)
async def health_check():
    return {
        "success": True,
        "data": {"message": "Issuer portal is running."},
        "message": "OK",
        "error_code": None,
    }
