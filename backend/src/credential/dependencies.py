from typing import Annotated

from fastapi import Depends, HTTPException, status

from src.admin.models import PlatformAdmin
from src.auth.dependencies import require_current_actor
from src.auth.models import Session
from src.organization.models import InstitutionAccount
from src.owner.constants import OwnerStatus
from src.owner.models import Owner


async def require_current_active_owner(
    actor_info: Annotated[
        tuple[PlatformAdmin | Owner | InstitutionAccount, Session, str],
        Depends(require_current_actor),
    ],
) -> Owner:
    actor, _, actor_type = actor_info
    if actor_type != "owner" or not isinstance(actor, Owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner access is required.",
        )
    if actor.status != OwnerStatus.ACTIVE or actor.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active owner account is required.",
        )
    return actor


CurrentOwner = Annotated[Owner, Depends(require_current_active_owner)]
