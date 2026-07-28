from datetime import UTC, datetime
from typing import Annotated, Any

from beanie import PydanticObjectId
from bson.errors import InvalidId
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.admin.models import PlatformAdmin
from src.auth.constants import ActorType, SessionStatus
from src.auth.models import Session
from src.auth.services import decode_access_token
from src.exceptions import AppError
from src.organization.models import InstitutionAccount
from src.owner.models import Owner

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="BearerAuth")
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]


def _unauthorized(message: str = "Invalid or expired access token.") -> AppError:
    return AppError(
        status_code=401,
        message=message,
        error_code="UNAUTHORIZED",
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


async def require_current_actor(
    credentials: BearerCredentials,
) -> tuple[PlatformAdmin | Owner | InstitutionAccount, Session, str]:
    """Decodes Bearer token, checks active session, and returns (user_model, session, actor_type)."""
    if credentials is None:
        raise _unauthorized()

    try:
        payload = decode_access_token(credentials.credentials)
    except HTTPException:
        raise _unauthorized() from None

    actor_type = payload.get("actor_type")
    actor_id_val = payload.get("sub")
    session_id_val = payload.get("session_id")

    if not actor_type or not actor_id_val or not session_id_val:
        raise _unauthorized()

    actor_id = _as_object_id(actor_id_val)
    session_id = _as_object_id(session_id_val)

    session = await Session.get(session_id)
    if (
        session is None
        or session.status != SessionStatus.ACTIVE
        or _is_expired(session.expires_at)
        or session.actor_id != actor_id
    ):
        raise _unauthorized()

    if actor_type in (ActorType.PLATFORM_ADMIN.value, "platform_admin"):
        if not session.twofa_verified:
            raise _unauthorized("Admin session requires TOTP verification.")
        admin = await PlatformAdmin.get(actor_id)
        if admin is None or admin.status != "active":
            raise _unauthorized()
        return admin, session, "platform_admin"

    elif actor_type in (ActorType.OWNER.value, "owner"):
        owner = await Owner.get(actor_id)
        if owner is None:
            raise _unauthorized()
        return owner, session, "owner"

    elif actor_type in (ActorType.INSTITUTION_ACCOUNT.value, "institution_account"):
        account = await InstitutionAccount.get(actor_id)
        if account is None:
            raise _unauthorized()
        return account, session, "institution_account"

    else:
        raise _unauthorized("Unknown actor type.")
