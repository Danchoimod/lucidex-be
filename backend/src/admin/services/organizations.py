from datetime import UTC, datetime
from urllib.parse import urlencode

from beanie import PydanticObjectId
from pydantic import BaseModel

from src.admin.models import PlatformAdmin
from src.config import settings
from src.exceptions import AppError
from src.invitation.constants import InviteStatus
from src.invitation.repository import revoke_if_pending
from src.invitation.service import INVITE_TTL_HOURS, rotate_pending_invite
from src.mailer import (
    EmailDeliveryError,
    EmailTemplate,
    EmailTemplateError,
    mailer_service,
)
from src.organization.constants import OrganizationStatus
from src.organization.models import Organization


class ApproveOrganizationData(BaseModel):
    organization_id: str
    organization_status: OrganizationStatus
    invite_status: InviteStatus
    invite_expires_at: datetime
    email_sent: bool


async def approve_organization(
    *,
    organization_id: PydanticObjectId,
    admin: PlatformAdmin,
) -> ApproveOrganizationData:
    organization = await _approve_if_needed(
        organization_id=organization_id,
        admin=admin,
    )
    if organization.id is None or admin.id is None:
        raise RuntimeError("Persisted admin or organization has no id.")

    issued_invite = await rotate_pending_invite(
        organization_id=organization.id,
        contact_email=str(organization.contact_email),
        created_by=admin.id,
    )
    base_url = settings.FRONTEND_BASE_URL.rstrip("/")
    invite_url = (
        f"{base_url}/institution/invite?"
        f"{urlencode({'token': issued_invite.raw_token})}"
    )

    try:
        await mailer_service.send_email(
            email=str(organization.contact_email),
            template=EmailTemplate.INSTITUTION_INVITE,
            context={
                "organization_name": organization.name,
                "contact_email": organization.contact_email,
                "invite_url": invite_url,
                "expires_in_hours": INVITE_TTL_HOURS,
            },
        )
    except (EmailDeliveryError, EmailTemplateError) as exc:
        await revoke_if_pending(
            invite_id=issued_invite.invite_id,
            revoked_at=datetime.now(UTC),
        )
        raise AppError(
            status_code=502,
            message="Organization was approved, but the invitation email failed.",
            error_code="INVITATION_EMAIL_FAILED",
        ) from exc

    return ApproveOrganizationData(
        organization_id=str(organization.id),
        organization_status=OrganizationStatus.APPROVED,
        invite_status=InviteStatus.PENDING,
        invite_expires_at=issued_invite.expires_at,
        email_sent=True,
    )


async def _approve_if_needed(
    *,
    organization_id: PydanticObjectId,
    admin: PlatformAdmin,
) -> Organization:
    organization = await Organization.get(organization_id)
    if organization is None:
        raise AppError(
            status_code=404,
            message="Organization not found.",
            error_code="ORGANIZATION_NOT_FOUND",
        )
    if organization.status == OrganizationStatus.APPROVED:
        return organization
    if organization.status != OrganizationStatus.PENDING_REVIEW or admin.id is None:
        raise AppError(
            status_code=409,
            message="Organization cannot be approved in its current state.",
            error_code="ORGANIZATION_NOT_APPROVABLE",
        )

    reviewed_at = datetime.now(UTC)
    await Organization.find_one(
        {
            "_id": organization_id,
            "status": OrganizationStatus.PENDING_REVIEW.value,
        }
    ).update(
        {
            "$set": {
                "status": OrganizationStatus.APPROVED.value,
                "reviewed_by": admin.id,
                "reviewed_at": reviewed_at,
            }
        }
    )
    organization = await Organization.get(organization_id)
    if organization is None:
        raise AppError(
            status_code=404,
            message="Organization not found.",
            error_code="ORGANIZATION_NOT_FOUND",
        )
    if organization.status != OrganizationStatus.APPROVED:
        raise AppError(
            status_code=409,
            message="Organization approval conflicted with another update.",
            error_code="ORGANIZATION_APPROVAL_CONFLICT",
        )
    return organization
