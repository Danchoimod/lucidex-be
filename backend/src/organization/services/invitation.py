from pymongo.errors import DuplicateKeyError

from src.auth.services import get_password_hash
from src.exceptions import AppError
from src.invitation import validate_pending_invite
from src.organization.constants import AccountStatus
from src.organization.models import InstitutionAccount
from src.organization.repository import (
    create_institution_account,
    find_institution_account_by_org_id,
    update_pending_password,
)


async def submit_invite_password(
    *,
    invite_token: str,
    password: str,
) -> InstitutionAccount:
    context = await validate_pending_invite(raw_token=invite_token)
    password_hash = get_password_hash(password)
    account = await find_institution_account_by_org_id(org_id=context.org_id)

    if account is None:
        account = InstitutionAccount(
            org_id=context.org_id,
            email=context.contact_email,
            password_hash=password_hash,
            status=AccountStatus.PENDING,
        )
        try:
            return await create_institution_account(account)
        except DuplicateKeyError as exc:
            raise _account_conflict() from exc

    if account.status == AccountStatus.ACTIVE:
        raise AppError(
            status_code=409,
            message="Institution account is already active.",
            error_code="INSTITUTION_ACCOUNT_ALREADY_ACTIVE",
        )
    if account.status != AccountStatus.PENDING:
        raise _account_conflict()

    updated = await update_pending_password(
        org_id=context.org_id,
        password_hash=password_hash,
    )
    if updated is None:
        raise _account_conflict()
    return updated


def _account_conflict() -> AppError:
    return AppError(
        status_code=409,
        message="Institution account cannot be updated in its current state.",
        error_code="INSTITUTION_ACCOUNT_CONFLICT",
    )
