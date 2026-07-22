import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from beanie import PydanticObjectId
from pydantic import BaseModel

from src.admin.models import PlatformAdmin
from src.config import settings
from src.exceptions import AppError
from src.invitation.constants import InviteStatus
from src.invitation.repository import find_pending_by_id, revoke_if_pending
from src.invitation.service import INVITE_TTL_HOURS, rotate_pending_invite
from src.mailer import (
    EmailDeliveryError,
    EmailTemplate,
    EmailTemplateError,
    mailer_service,
)
from src.organization.constants import OrganizationStatus, OrganizationType
from src.organization.models import Organization
from src.organization.schemas import OrganizationResponse


async def list_organizations(
    *,
    status: OrganizationStatus | None = OrganizationStatus.PENDING_REVIEW,
    org_type: OrganizationType | None = None,
) -> list[OrganizationResponse]:
    query: dict[str, Any] = {}
    if status is not None:
        query["status"] = status.value if hasattr(status, "value") else status
    if org_type is not None:
        query["type"] = org_type.value if hasattr(org_type, "value") else org_type

    orgs = await Organization.find(query).sort("created_at").to_list()
    return [
        OrganizationResponse(
            id=str(org.id),
            type=org.type,
            status=org.status,
            name=org.name,
            tax_code=org.tax_code,
            address=org.address,
            legal_rep_name=org.legal_rep_name,
            contact_email=str(org.contact_email),
            contact_phone=org.contact_phone,
            registrant_name=org.registrant_name,
            registrant_title=org.registrant_title,
            documents=org.documents,
            rejection_reason=org.rejection_reason,
            reviewed_by=str(org.reviewed_by) if org.reviewed_by else None,
            reviewed_at=org.reviewed_at,
            created_at=org.created_at,
        )
        for org in orgs
    ]

logger = logging.getLogger("lucidex.admin.organizations")


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
    request_id: str | None = None,
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
        f"{base_url}/invite/setup-password?"
        f"{urlencode({'token': issued_invite.raw_token})}"
    )

    # This narrows the rotation race window; email delivery cannot be made
    # atomic with the MongoDB state check.
    if await find_pending_by_id(invite_id=issued_invite.invite_id) is None:
        raise AppError(
            status_code=409,
            message="Invitation conflict.",
            error_code="INVITATION_ROTATION_CONFLICT",
            log_context={
                "actor_id": str(admin.id),
                "actor_role": admin.role,
                "organization_id": str(organization.id),
                "invite_id": str(issued_invite.invite_id),
            },
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
            message="Invitation email failed.",
            error_code="INVITATION_EMAIL_FAILED",
            log_context={
                "actor_id": str(admin.id),
                "actor_role": admin.role,
                "organization_id": str(organization.id),
                "invite_id": str(issued_invite.invite_id),
                "failure_reason": type(exc).__name__,
            },
        ) from exc

    logger.info(
        "organization_approved_and_invited",
        extra={
            "request_id": request_id,
            "actor_id": str(admin.id),
            "actor_role": admin.role,
            "organization_id": str(organization.id),
            "invite_id": str(issued_invite.invite_id),
        },
    )
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
            log_context={
                "actor_id": str(admin.id),
                "actor_role": admin.role,
                "organization_id": str(organization_id),
            },
        )
    if organization.status == OrganizationStatus.APPROVED:
        return organization
    if organization.status != OrganizationStatus.PENDING_REVIEW or admin.id is None:
        raise AppError(
            status_code=409,
            message="Organization is not approvable.",
            error_code="ORGANIZATION_NOT_APPROVABLE",
            log_context={
                "actor_id": str(admin.id),
                "actor_role": admin.role,
                "organization_id": str(organization_id),
            },
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
            log_context={
                "actor_id": str(admin.id),
                "actor_role": admin.role,
                "organization_id": str(organization_id),
            },
        )
    if organization.status != OrganizationStatus.APPROVED:
        raise AppError(
            status_code=409,
            message="Organization approval conflict.",
            error_code="ORGANIZATION_APPROVAL_CONFLICT",
            log_context={
                "actor_id": str(admin.id),
                "actor_role": admin.role,
                "organization_id": str(organization_id),
            },
        )
    return organization
