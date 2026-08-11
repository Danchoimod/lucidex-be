from beanie import PydanticObjectId

from src.organization.constants import AccountStatus
from src.organization.models import InstitutionAccount


async def find_institution_account_by_org_id(
    *,
    org_id: PydanticObjectId,
) -> InstitutionAccount | None:
    return await InstitutionAccount.find_one({"org_id": org_id})


async def create_institution_account(
    account: InstitutionAccount,
) -> InstitutionAccount:
    return await account.insert()


async def update_pending_password(
    *,
    org_id: PydanticObjectId,
    password_hash: str,
) -> InstitutionAccount | None:
    result = await InstitutionAccount.find_one(
        {
            "org_id": org_id,
            "status": AccountStatus.PENDING.value,
        }
    ).update({"$set": {"password_hash": password_hash}})
    if result.modified_count != 1:
        return None
    return await find_institution_account_by_org_id(org_id=org_id)
