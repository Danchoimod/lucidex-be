from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["Admin"])



@router.get("/hello", summary="Hello admin")
async def hello_admin():
    return {
        "success": True,
        "data": {"message": "Hello admin"},
        "message": "OK",
        "error_code": None,
    }