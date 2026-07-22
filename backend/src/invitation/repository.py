from datetime import datetime

from beanie import PydanticObjectId

from src.invitation.constants import InviteStatus
from src.invitation.models import InviteLink


async def find_by_token_hash(
    *,
    token_hash: str,
    session=None,
) -> InviteLink | None:
    return await InviteLink.find_one(
        {"token_hash": token_hash},
        session=session,
    )


async def find_pending_by_id(
    *,
    invite_id: PydanticObjectId,
    session=None,
) -> InviteLink | None:
    return await InviteLink.find_one(
        {
            "_id": invite_id,
            "status": InviteStatus.PENDING.value,
        },
        session=session,
    )


async def revoke_pending_for_organization(
    *,
    organization_id: PydanticObjectId,
    revoked_at: datetime,
    session=None,
) -> int:
    result = await InviteLink.find(
        {
            "org_id": organization_id,
            "status": InviteStatus.PENDING.value,
        },
        session=session,
    ).update(
        {
            "$set": {
                "status": InviteStatus.REVOKED.value,
                "revoked_at": revoked_at,
                "updated_at": revoked_at,
            }
        },
        session=session,
    )
    return result.modified_count


async def insert_invite(
    invite: InviteLink,
    *,
    session=None,
) -> InviteLink:
    return await invite.insert(session=session)


async def revoke_if_pending(
    *,
    invite_id: PydanticObjectId,
    revoked_at: datetime,
    session=None,
) -> bool:
    result = await InviteLink.find_one(
        {
            "_id": invite_id,
            "status": InviteStatus.PENDING.value,
        },
        session=session,
    ).update(
        {
            "$set": {
                "status": InviteStatus.REVOKED.value,
                "revoked_at": revoked_at,
                "updated_at": revoked_at,
            }
        },
        session=session,
    )
    return result.modified_count == 1
