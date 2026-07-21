from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from fastapi import HTTPException, status

from src.invitation.constants import InviteStatus
from src.invitation.exceptions import InviteLinkCreationFailedError
from src.invitation.models import InviteLink
from src.invitation.repository import InviteLinkRepository
from src.models import utc_now


class InviteLinkService:
    """Create, validate, and persist invitation links for organizations."""

    def __init__(self, repository: InviteLinkRepository | None = None) -> None:
        self._repository = repository or InviteLinkRepository()

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        """Hash the raw token with SHA-256 for persistent storage."""
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    async def create_invite_link(
        self,
        *,
        org_id,
        contact_email: str,
        created_by,
    ) -> str:
        """Generate a new invite link, revoke any prior pending one, and save it."""
        pending_invite = await self._repository.find_pending_by_org(org_id)
        if pending_invite is not None:
            await self._repository.revoke(pending_invite)

        raw_token = secrets.token_urlsafe(24)
        now = utc_now()
        invite_link = InviteLink(
            org_id=org_id,
            contact_email=contact_email,
            token_hash=self._hash_token(raw_token),
            status=InviteStatus.PENDING,
            expires_at=now + timedelta(days=30),
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )

        try:
            await self._repository.insert(invite_link)
        except Exception as exc:
            raise InviteLinkCreationFailedError() from exc

        return raw_token

    async def validate_pending_invite(self, raw_token: str) -> InviteLink:
        """Validate a raw invite token: hash it, find in DB, check expiration & status."""
        hashed_token = self._hash_token(raw_token)

        # Find token in database via token_hash field
        invite = await InviteLink.find_one(InviteLink.token_hash == hashed_token)
        if not invite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invite token is invalid or does not exist.",
            )

        # Check invitation status
        if invite.status != InviteStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation has already been used or revoked.",
            )

        # Check expiration date
        if invite.expires_at < utc_now():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation has expired.",
            )

        return invite


invite_link_service = InviteLinkService()


async def validate_pending_invite(raw_token: str) -> InviteLink:
    """Helper function to validate pending invite without importing the class instance directly."""
    return await invite_link_service.validate_pending_invite(raw_token)