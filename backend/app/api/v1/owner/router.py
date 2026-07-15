from fastapi import APIRouter

router = APIRouter(prefix="/owner", tags=["Owner"])

# TODO: Add Owner portal endpoints in the dedicated implementation session.

@router.get(
    "/health",
    summary="Check owner API health",
    description=(
        "Allows clients to check whether the Owner API routes are available. "
        "Returns a success response when the portal router is reachable."
    ),
)
async def health_check():
    return {
        "success": True,
        "data": {"message": "Owner portal is running."},
        "message": "OK",
        "error_code": None,
    }
