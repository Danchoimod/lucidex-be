from src.owner.models import Owner
from src.owner.schemas import OwnerProfileResponse, UpdateOwnerProfileRequest
from src.owner.validators import (
    validate_avatar_file,
    validate_full_name,
    validate_phone_number,
)
from src.utils.gcs_storage import upload_file


async def get_profile(owner: Owner) -> OwnerProfileResponse:
    """Retrieve owner personal profile."""
    return OwnerProfileResponse(
        id=str(owner.id),
        email=owner.email,
        full_name=owner.full_name,
        phone=owner.phone,
        avatar_url=owner.avatar_url,
        dob=owner.dob,
    )


async def update_profile(
    owner: Owner,
    payload: UpdateOwnerProfileRequest,
    avatar_file_content: bytes | None = None,
    avatar_filename: str | None = None,
    avatar_content_type: str | None = None,
) -> OwnerProfileResponse:
    """Update editable fields of owner personal profile, including optional avatar file upload."""
    if payload.full_name is not None:
        validated_name = validate_full_name(payload.full_name)
        owner.full_name = validated_name

    if payload.phone is not None:
        validated_phone = validate_phone_number(payload.phone)
        owner.phone = validated_phone

    if avatar_file_content is not None and avatar_filename is not None:
        validate_avatar_file(avatar_filename, avatar_content_type, len(avatar_file_content))
        object_name = f"avatars/{str(owner.id)}/{avatar_filename}"
        avatar_url = upload_file(
            file_content=avatar_file_content,
            object_name=object_name,
            content_type=avatar_content_type or "image/png",
        )
        owner.avatar_url = avatar_url
    elif payload.avatar_url is not None:
        owner.avatar_url = payload.avatar_url

    await owner.save()
    return await get_profile(owner)



async def upload_avatar(
    owner: Owner, file_content: bytes, filename: str, content_type: str
) -> OwnerProfileResponse:
    """Validate and upload avatar image directly to GCS, then update owner profile."""
    validate_avatar_file(filename, content_type, len(file_content))

    object_name = f"avatars/{str(owner.id)}/{filename}"
    avatar_url = upload_file(
        file_content=file_content,
        object_name=object_name,
        content_type=content_type or "image/png",
    )

    owner.avatar_url = avatar_url
    await owner.save()
    return await get_profile(owner)
