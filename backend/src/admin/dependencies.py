from datetime import UTC, datetime
from typing import Annotated, Any

from beanie import PydanticObjectId
from bson.errors import InvalidId
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.admin.models import PlatformAdmin
from src.auth.constants import ActorType, SessionStatus
from src.auth.models import Session
from src.auth.services import decode_access_token
from src.exceptions import AppError

admin_bearer_scheme = HTTPBearer(auto_error=False, scheme_name="BearerAuth")
AdminCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(admin_bearer_scheme),
]


def _unauthorized() -> AppError:
    return AppError(
        status_code=401,
        message="Invalid or expired admin access token.",
        error_code="INVALID_ADMIN_ACCESS_TOKEN",
    )


def _as_object_id(value: Any) -> PydanticObjectId:
    if not isinstance(value, str):
        raise _unauthorized()
    try:
        return PydanticObjectId(value)
    except (InvalidId, TypeError):
        raise _unauthorized() from None


def _is_expired(value: datetime) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value <= datetime.now(UTC)


async def require_admin(
    request: Request,
    credentials: AdminCredentials,
) -> PlatformAdmin:
    if credentials is None:
        raise _unauthorized()

    try:
        payload = decode_access_token(credentials.credentials)
    except HTTPException:
        raise _unauthorized() from None

    if (
        payload.get("actor_type") != ActorType.PLATFORM_ADMIN
        or "exp" not in payload
    ):
        raise _unauthorized()

    admin_id = _as_object_id(payload.get("sub"))
    session_id = _as_object_id(payload.get("session_id"))
    session = await Session.get(session_id)
    if (
        session is None
        or session.status != SessionStatus.ACTIVE
        or _is_expired(session.expires_at)
        or not session.twofa_verified
        or session.actor_type != ActorType.PLATFORM_ADMIN
        or session.actor_id != admin_id
    ):
        raise _unauthorized()

    admin = await PlatformAdmin.get(admin_id)
    if (
        admin is None
        or admin.status != "active"
        or admin.role not in {"super_admin", "operations_admin"}
    ):
        raise _unauthorized()

    request.state.actor_type = ActorType.PLATFORM_ADMIN
    return admin


async def require_super_admin(
    admin: Annotated[PlatformAdmin, Depends(require_admin)],
) -> PlatformAdmin:
    if admin.role != "super_admin":
        raise AppError(
            status_code=403,
            message="Super Admin access is required.",
            error_code="SUPER_ADMIN_REQUIRED",
        )
    return admin
