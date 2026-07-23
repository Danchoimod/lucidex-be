import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from beanie import PydanticObjectId
from pymongo.errors import DuplicateKeyError

from src.exceptions import AppError
from src.invitation.constants import InviteStatus
from src.invitation.models import InviteLink
from src.invitation.repository import (
    find_by_token_hash,
    insert_invite,
    revoke_pending_for_organization,
)
from src.invitation.schemas import InviteContext, IssuedInvite

INVITE_TTL_HOURS = 72


def hash_invite_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


async def rotate_pending_invite(
    *,
    organization_id: PydanticObjectId,
    contact_email: str,
    created_by: PydanticObjectId,
) -> IssuedInvite:
    now = datetime.now(UTC)
    await revoke_pending_for_organization(
        organization_id=organization_id,
        revoked_at=now,
    )

    raw_token = secrets.token_urlsafe(32)
    invite = InviteLink(
        org_id=organization_id,
        contact_email=contact_email,
        token_hash=hash_invite_token(raw_token),
        status=InviteStatus.PENDING,
        expires_at=now + timedelta(hours=INVITE_TTL_HOURS),
        created_by=created_by,
        created_at=now,
        updated_at=now,
    )
    try:
        invite = await insert_invite(invite)
    except DuplicateKeyError as exc:
        raise _rotation_conflict() from exc
    if invite.id is None:
        raise RuntimeError("InviteLink was inserted without an id.")

    return IssuedInvite(
        invite_id=invite.id,
        raw_token=raw_token,
        expires_at=invite.expires_at,
    )


async def validate_pending_invite(
    *,
    raw_token: str,
    session=None,
) -> InviteContext:
    invite = await find_by_token_hash(
        token_hash=hash_invite_token(raw_token),
        session=session,
    )
    if invite is None:
        invite = await find_by_token_hash(
            token_hash=raw_token,
            session=session,
        )

    if invite is None or invite.status != InviteStatus.PENDING:
        raise _invalid_invite()

    expires_at = invite.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC) or invite.id is None:
        raise _invalid_invite()

    return InviteContext(
        invite_id=invite.id,
        org_id=invite.org_id,
        contact_email=str(invite.contact_email),
        expires_at=invite.expires_at,
    )


def _invalid_invite() -> AppError:
    return AppError(
        status_code=400,
        message="Invalid or expired invitation link.",
        error_code="INVALID_INVITE",
    )


def _rotation_conflict() -> AppError:
    return AppError(
        status_code=409,
        message="Invitation rotation conflicted with another request.",
        error_code="INVITATION_ROTATION_CONFLICT",
    )
