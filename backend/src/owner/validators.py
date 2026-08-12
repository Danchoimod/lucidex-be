import re

from src.owner.exceptions import (
    InvalidAvatarFileError,
    InvalidNameError,
    InvalidPhoneNumberError,
)

PHONE_REGEX = re.compile(r"^\+?[0-9]{9,15}$")
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_AVATAR_MIMETYPES = {"image/jpeg", "image/jpg", "image/png", "application/octet-stream"}


def validate_full_name(full_name: str | None) -> str:
    """Validate full name: non-empty and must contain at least one letter."""
    if full_name is None:
        raise InvalidNameError()

    val = full_name.strip()
    if not val or not any(c.isalpha() for c in val):
        raise InvalidNameError()
    return val


def validate_phone_number(phone: str | None) -> str | None:
    """Validate phone number format (9 to 15 digits, optional leading +)."""
    if phone is None or phone.strip() == "":
        return None

    cleaned = phone.strip().replace(" ", "").replace("-", "")
    if not PHONE_REGEX.match(cleaned):
        raise InvalidPhoneNumberError()
    return cleaned


def validate_avatar_file(filename: str | None, content_type: str | None, file_size: int) -> None:
    """Validate avatar image file: format must be JPG/PNG and size <= 5MB."""
    if file_size <= 0 or file_size > MAX_AVATAR_SIZE:
        raise InvalidAvatarFileError()

    if not filename:
        raise InvalidAvatarFileError()

    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_AVATAR_EXTENSIONS:
        raise InvalidAvatarFileError()

    if content_type and content_type.lower() not in ALLOWED_AVATAR_MIMETYPES:
        raise InvalidAvatarFileError()
