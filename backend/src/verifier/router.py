from fastapi import APIRouter

router = APIRouter(prefix="/verifier", tags=["Verifier"])

# TODO: Add Verifier portal endpoints in the dedicated implementation session.

@router.get(
    "/health",
    summary="Check verifier API health",
    description=(
        "Allows clients to check whether the Verifier API routes are available. "
        "Returns a success response when the portal router is reachable."
    ),
)
async def health_check():
    return {
        "success": True,
        "data": {"message": "Verifier portal is running."},
        "message": "OK",
        "error_code": None,
    }
