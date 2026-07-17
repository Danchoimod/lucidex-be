from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import HTTPException, status
from jwt.exceptions import InvalidTokenError

from src.config import settings

ALGORITHM = "HS256"


def create_access_token(
    subject: str,
    actor_type: str,
    session_id: str,
    org_id: str | None = None,
    permissions: list[str] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a short-lived API access token for any Lucidex actor."""
    expires_at = datetime.now(UTC) + (
        expires_delta
        or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "actor_type": actor_type,
        "org_id": org_id,
        "session_id": session_id,
        "permissions": permissions or [],
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Validate an API access token without exposing validation details."""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
        ) from None


def create_temp_login_token(owner_id: str) -> str:
    """Create a short-lived (5 min) token representing a pending login state."""
    expires_at = datetime.now(UTC) + timedelta(minutes=5)
    payload = {
        "sub": owner_id,
        "purpose": "login_2fa",
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_temp_login_token(token: str) -> str:
    """Decode and validate a temporary login token, returning the owner ID."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("purpose") != "login_2fa":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token purpose.",
            )
        return payload["sub"]
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired login verification token.",
        ) from None

