from __future__ import annotations

from src.invitation.constants import InviteStatus
from src.invitation.models import InviteLink
from src.models import utc_now


class InviteLinkRepository:
    """Persistence helpers for invitation links."""

    async def find_pending_by_org(self, org_id) -> InviteLink | None:
        """Return the currently pending invitation for an organization, if any."""
        return await InviteLink.find_one(
            InviteLink.org_id == org_id,
            InviteLink.status == InviteStatus.PENDING,
        )

    async def revoke(self, invite_link: InviteLink) -> None:
        """Revoke an existing invite link in place."""
        now = utc_now()
        invite_link.status = InviteStatus.REVOKED
        invite_link.revoked_at = now
        invite_link.updated_at = now
        await invite_link.save()

    async def insert(self, invite_link: InviteLink) -> InviteLink:
        """Persist a new invite link document."""
        return await invite_link.insert()
