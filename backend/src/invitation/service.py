from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from src.invitation.constants import InviteStatus
from src.invitation.exceptions import InviteLinkCreationFailedError
from src.invitation.models import InviteLink
from src.invitation.repository import InviteLinkRepository
from src.models import utc_now


class InviteLinkService:
    """Create and persist invitation links for organizations."""

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


invite_link_service = InviteLinkService()
