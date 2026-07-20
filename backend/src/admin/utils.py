import base64
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Any

import jwt
import pyotp
import qrcode
from jwt.exceptions import InvalidTokenError

from src.admin.constants import (
    ADMIN_TOKEN_TTL_MINUTES,
    TOTP_ISSUER_NAME,
    AdminTokenPurpose,
)
from src.admin.exceptions import InvalidAdminTokenError
from src.auth.constants import ActorType
from src.config import settings

JWT_ALGORITHM = "HS256"


def create_admin_temp_token(
    admin_id: str,
    purpose: AdminTokenPurpose,
    *,
    expires_delta: timedelta | None = None,
) -> str:
    payload = {
        "sub": admin_id,
        "actor_type": ActorType.PLATFORM_ADMIN,
        "purpose": purpose,
        "exp": datetime.now(UTC)
        + (expires_delta or timedelta(minutes=ADMIN_TOKEN_TTL_MINUTES)),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_admin_temp_token(
    token: str,
    expected_purpose: AdminTokenPurpose,
) -> str:
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={
                "require": ["exp", "sub", "actor_type", "purpose"],
            },
        )
    except InvalidTokenError:
        raise InvalidAdminTokenError() from None

    admin_id = payload.get("sub")
    if (
        not isinstance(admin_id, str)
        or payload.get("actor_type") != ActorType.PLATFORM_ADMIN
        or payload.get("purpose") != expected_purpose
    ):
        raise InvalidAdminTokenError()
    return admin_id


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def create_totp_uri(secret: str, username: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name=TOTP_ISSUER_NAME,
    )


def create_qr_data_url(totp_uri: str) -> str:
    image = qrcode.make(totp_uri)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def verify_totp(secret: str, otp_code: str) -> bool:
    return pyotp.TOTP(secret).verify(otp_code)
