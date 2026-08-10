import hashlib
import secrets
import string
from datetime import UTC, datetime

from beanie import PydanticObjectId
from bson.errors import InvalidId

from src.credential.exceptions import (
    CredentialNotClaimedError,
    CredentialNotFoundError,
    InvalidAccessCountError,
    InvalidExpirationError,
    LinkAlreadyRevokedError,
    LinkExhaustedError,
    LinkExpiredError,
    VerifiedLinkNotFoundError,
)
from src.credential.models import Credential, VerifiedLink
from src.credential.schemas import (
    CreateVerifiedLinkRequest,
    EditVerifiedLinkRequest,
    VerifiedLinkListResponse,
    VerifiedLinkResponse,
)
from src.models import utc_now

CODE_CHARSET = string.ascii_uppercase + string.digits
# Remove ambiguous characters: O, 0, I, 1, L
SAFE_CODE_CHARSET = "".join(c for c in CODE_CHARSET if c not in "O0I1L")


def generate_code() -> str:
    """Generate a random 12-character uppercase alphanumeric code."""
    return "".join(secrets.choice(SAFE_CODE_CHARSET) for _ in range(12))


def hash_code(plaintext: str) -> str:
    """Hash a plaintext verification code using SHA-256 for deterministic lookup."""
    return hashlib.sha256(plaintext.strip().upper().encode("utf-8")).hexdigest()


def verify_code_hash(plaintext: str, stored_hash: str) -> bool:
    """Verify a plaintext code against a stored SHA-256 hash."""
    return hash_code(plaintext) == stored_hash



def derive_display_status(link: VerifiedLink) -> str:
    """Derive the user-facing display status for a VerifiedLink."""
    if link.status == "revoked":
        return "revoked"
    if link.expires_at is not None:
        exp = link.expires_at.replace(tzinfo=UTC) if link.expires_at.tzinfo is None else link.expires_at
        if exp <= datetime.now(UTC):
            return "expired"
    if link.max_access_count is not None and link.remaining_access_count is not None:
        if link.remaining_access_count <= 0:
            return "exhausted"
    return "active"


async def create_verified_link(
    owner_id: PydanticObjectId,
    payload: CreateVerifiedLinkRequest,
) -> tuple[VerifiedLink, str]:
    """Create a new VerifiedLink tied to a claimed credential owned by owner_id."""
    try:
        cred_obj_id = PydanticObjectId(payload.credential_id)
    except (InvalidId, TypeError):
        raise CredentialNotFoundError() from None

    credential = await Credential.get(cred_obj_id)
    if credential is None or credential.owner_id != owner_id:
        raise CredentialNotFoundError()

    if credential.status != "claimed":
        raise CredentialNotClaimedError()

    now = datetime.now(UTC)
    if payload.expires_at is not None:
        exp = payload.expires_at.replace(tzinfo=UTC) if payload.expires_at.tzinfo is None else payload.expires_at
        if exp <= now:
            raise InvalidExpirationError()

    if payload.max_access_count is not None and payload.max_access_count < 1:
        raise InvalidAccessCountError()

    allowed_org_ids: list[PydanticObjectId] = []
    for org_str in payload.allowed_org_ids:
        try:
            allowed_org_ids.append(PydanticObjectId(org_str))
        except (InvalidId, TypeError):
            pass

    plaintext_code = generate_code()
    code_hash_val = hash_code(plaintext_code)

    link = VerifiedLink(
        owner_id=owner_id,
        credential_id=credential.id,
        code_hash=code_hash_val,
        expires_at=payload.expires_at,
        allowed_org_ids=allowed_org_ids,
        max_access_count=payload.max_access_count,
        remaining_access_count=payload.max_access_count,
        status="active",
        created_at=utc_now(),
    )
    await link.insert()
    return link, plaintext_code


async def list_verified_links(
    owner_id: PydanticObjectId,
    credential_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> VerifiedLinkListResponse:
    """List all verification links created by owner_id with pagination."""
    query: dict = {"owner_id": owner_id, "deleted_at": None}
    if credential_id:
        try:
            query["credential_id"] = PydanticObjectId(credential_id)
        except (InvalidId, TypeError):
            pass

    skip = (page - 1) * page_size
    total = await VerifiedLink.find(query).count()
    links = await VerifiedLink.find(query).sort("-created_at").skip(skip).limit(page_size).to_list()

    items = [
        VerifiedLinkResponse(
            id=str(link.id),
            credential_id=str(link.credential_id),
            expires_at=link.expires_at,
            allowed_org_ids=[str(org_id) for org_id in link.allowed_org_ids],
            max_access_count=link.max_access_count,
            remaining_access_count=link.remaining_access_count,
            display_status=derive_display_status(link),
            created_at=link.created_at,
            revoked_at=link.revoked_at,
        )
        for link in links
    ]

    return VerifiedLinkListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


async def revoke_verified_link(
    owner_id: PydanticObjectId,
    link_id: str,
) -> VerifiedLink:
    """Revoke an active verification link."""
    try:
        obj_id = PydanticObjectId(link_id)
    except (InvalidId, TypeError):
        raise VerifiedLinkNotFoundError() from None

    link = await VerifiedLink.get(obj_id)
    if link is None or link.owner_id != owner_id or link.deleted_at is not None:
        raise VerifiedLinkNotFoundError()

    if link.status == "revoked":
        raise LinkAlreadyRevokedError()

    display_status = derive_display_status(link)
    if display_status == "expired":
        raise LinkExpiredError()
    if display_status == "exhausted":
        raise LinkExhaustedError()

    link.status = "revoked"
    link.revoked_at = utc_now()
    await link.save()
    return link


async def edit_verified_link(
    owner_id: PydanticObjectId,
    link_id: str,
    payload: EditVerifiedLinkRequest,
) -> VerifiedLink:
    """Edit settings of an active verification link."""
    try:
        obj_id = PydanticObjectId(link_id)
    except (InvalidId, TypeError):
        raise VerifiedLinkNotFoundError() from None

    link = await VerifiedLink.get(obj_id)
    if link is None or link.owner_id != owner_id or link.deleted_at is not None:
        raise VerifiedLinkNotFoundError()

    display_status = derive_display_status(link)
    if display_status == "revoked":
        raise LinkAlreadyRevokedError()
    if display_status == "expired":
        raise LinkExpiredError()
    if display_status == "exhausted":
        raise LinkExhaustedError()

    now = datetime.now(UTC)

    if payload.expires_at is not None:
        exp = payload.expires_at.replace(tzinfo=UTC) if payload.expires_at.tzinfo is None else payload.expires_at
        if exp <= now:
            raise InvalidExpirationError()
        link.expires_at = payload.expires_at

    if payload.allowed_org_ids is not None:
        new_allowed: list[PydanticObjectId] = []
        for org_str in payload.allowed_org_ids:
            try:
                new_allowed.append(PydanticObjectId(org_str))
            except (InvalidId, TypeError):
                pass
        link.allowed_org_ids = new_allowed

    if payload.max_access_count is not None:
        if payload.max_access_count < 1:
            raise InvalidAccessCountError()

        if link.max_access_count is not None and link.remaining_access_count is not None:
            used = link.max_access_count - link.remaining_access_count
            new_remaining = payload.max_access_count - used
            link.remaining_access_count = max(0, new_remaining)
        else:
            link.remaining_access_count = payload.max_access_count
        link.max_access_count = payload.max_access_count

    await link.save()
    return link
