from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile, status

from src.auth.dependencies import require_current_actor
from src.owner.models import Owner
from src.owner.schemas import OwnerProfileResponse, UpdateOwnerProfileRequest
from src.owner.services import profile as profile_service
from src.schemas.common import ApiResponse

router = APIRouter(prefix="/owner/profile", tags=["Owner - Profile"])


@router.get(
    "",
    response_model=ApiResponse[OwnerProfileResponse],
    status_code=status.HTTP_200_OK,
    summary="[Owner] Get Profile Information",
    description="Retrieve personal profile details of the authenticated owner.",
)
async def get_profile(
    actor_info: Annotated[tuple, Depends(require_current_actor)],
) -> ApiResponse[OwnerProfileResponse]:
    actor, _, _ = actor_info
    owner: Owner = actor  # type: ignore

    data = await profile_service.get_profile(owner)
    return ApiResponse[OwnerProfileResponse](
        success=True,
        data=data,
        message="Owner profile retrieved.",
        error_code=None,
    )


@router.patch(
    "",
    response_model=ApiResponse[OwnerProfileResponse],
    status_code=status.HTTP_200_OK,
    summary="[Owner] Update Profile Information",
    description=(
        "Update editable profile fields (full name, phone number, avatar URL, or upload a new avatar image file directly)."
    ),
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "full_name": {"type": "string", "example": "Nguyen Van A"},
                            "phone": {"type": "string", "example": "0912345678"},
                            "avatar_url": {
                                "type": "string",
                                "example": "https://storage.googleapis.com/bucket/avatar.png",
                            },
                        },
                    }
                },
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "full_name": {"type": "string"},
                            "phone": {"type": "string"},
                            "avatar_url": {"type": "string"},
                            "avatar": {"type": "string", "format": "binary"},
                        },
                    }
                },
            }
        }
    },
)
async def update_profile(
    request: Request,
    actor_info: Annotated[tuple, Depends(require_current_actor)],
) -> ApiResponse[OwnerProfileResponse]:
    actor, _, _ = actor_info
    owner: Owner = actor  # type: ignore

    content_type = request.headers.get("content-type", "")
    avatar_bytes: bytes | None = None
    avatar_filename: str | None = None
    avatar_mime: str | None = None

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        fn = form.get("full_name")
        ph = form.get("phone")
        url = form.get("avatar_url")
        file_obj = form.get("avatar") or form.get("file")

        if file_obj is not None and hasattr(file_obj, "filename") and getattr(file_obj, "filename", None):
            avatar_bytes = await file_obj.read()
            avatar_filename = getattr(file_obj, "filename")
            avatar_mime = getattr(file_obj, "content_type", None)

        payload = UpdateOwnerProfileRequest(
            full_name=str(fn) if fn is not None and isinstance(fn, str) else None,
            phone=str(ph) if ph is not None and isinstance(ph, str) else None,
            avatar_url=str(url) if url is not None and isinstance(url, str) else None,
        )
    else:
        body = await request.json() if request.headers.get("content-length", "0") != "0" else {}
        payload = UpdateOwnerProfileRequest(**body)

    data = await profile_service.update_profile(
        owner=owner,
        payload=payload,
        avatar_file_content=avatar_bytes,
        avatar_filename=avatar_filename,
        avatar_content_type=avatar_mime,
    )
    return ApiResponse[OwnerProfileResponse](
        success=True,
        data=data,
        message="Your profile has been updated.",
        error_code=None,
    )


@router.post(
    "/avatar",
    response_model=ApiResponse[OwnerProfileResponse],
    status_code=status.HTTP_200_OK,
    summary="[Owner] Upload Avatar Image",
    description="Upload a JPG or PNG avatar image (max 5MB) directly to Cloud Storage and update profile.",
)
async def upload_avatar(
    file: Annotated[UploadFile, File(...)],
    actor_info: Annotated[tuple, Depends(require_current_actor)],
) -> ApiResponse[OwnerProfileResponse]:
    actor, _, _ = actor_info
    owner: Owner = actor  # type: ignore

    content = await file.read()
    data = await profile_service.upload_avatar(
        owner=owner,
        file_content=content,
        filename=file.filename or "",
        content_type=file.content_type or "",
    )
    return ApiResponse[OwnerProfileResponse](
        success=True,
        data=data,
        message="Your profile has been updated.",
        error_code=None,
    )
