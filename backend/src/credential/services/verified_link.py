import hashlib
import secrets
import string
from datetime import UTC, datetime, timedelta

from beanie import PydanticObjectId
from bson.errors import InvalidId

from src.credential.exceptions import (
    CredentialNotFoundError,
    InvalidAccessCountError,
    InvalidExpirationError,
    InvalidOrgIdError,
    LinkAlreadyRevokedError,
    VerifiedLinkNotFoundError,
)
from src.credential.models import Credential, VerifiedLink
from src.credential.schemas import (
    CreateVerifiedLinkRequest,
    UpdateVerifiedLinkRequest,
    VerifiedLinkListResponse,
    VerifiedLinkResponse,
)
from src.models import utc_now
from src.organization.models import Organization
from src.owner.models import Owner

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
    """Derive the user-facing display status for a VerifiedLink (active, expired, revoked)."""
    if link.status == "revoked":
        return "revoked"
    if link.remaining_access_count is not None and link.remaining_access_count <= 0:
        return "expired"
    if link.expires_at is not None:
        exp = link.expires_at.replace(tzinfo=UTC) if link.expires_at.tzinfo is None else link.expires_at
        if exp <= datetime.now(UTC):
            return "expired"
    return "active"



async def create_verified_link(
    owner_id: PydanticObjectId,
    payload: CreateVerifiedLinkRequest,
    owner: Owner | None = None,
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
        raise CredentialNotFoundError()

    now = datetime.now(UTC)

    # Fetch owner if not provided but needed
    if owner is None:
        owner = await Owner.get(owner_id)

    defaults = owner.default_link_settings if owner else None

    # Resolve fields from payload or owner defaults
    fields_set = payload.model_fields_set

    has_explicit_options = bool(
        fields_set.intersection({"expires_at", "max_access_count", "allowed_org_ids"})
    )

    # expires_at
    if "expires_at" in fields_set:
        expires_at = payload.expires_at
    elif defaults and defaults.default_expiry_hours is not None:
        expires_at = now + timedelta(hours=defaults.default_expiry_hours)
    else:
        expires_at = None

    if expires_at is not None:
        exp = expires_at.replace(tzinfo=UTC) if expires_at.tzinfo is None else expires_at
        if exp <= now:
            raise InvalidExpirationError()

    # max_access_count
    if "max_access_count" in fields_set:
        max_access_count = payload.max_access_count
    elif defaults and defaults.default_max_access_count is not None:
        max_access_count = defaults.default_max_access_count
    else:
        max_access_count = None

    if max_access_count is not None and max_access_count < 1:
        raise InvalidAccessCountError()

    # allowed_org_ids
    if "allowed_org_ids" in fields_set:
        allowed_org_ids_input = payload.allowed_org_ids
    elif defaults and defaults.default_allowed_org_ids:
        allowed_org_ids_input = [str(org_id) for org_id in defaults.default_allowed_org_ids]
    else:
        allowed_org_ids_input = []

    allowed_org_ids: list[PydanticObjectId] = []
    for org_str in allowed_org_ids_input:
        try:
            allowed_org_ids.append(PydanticObjectId(org_str))
        except (InvalidId, TypeError):
            raise InvalidOrgIdError() from None

    if allowed_org_ids:
        count = await Organization.find({"_id": {"$in": allowed_org_ids}}).count()
        if count != len(allowed_org_ids):
            raise InvalidOrgIdError()

    modes_count = sum([
        max_access_count is not None,
        expires_at is not None,
        bool(allowed_org_ids),
    ])
    if not has_explicit_options and defaults and defaults.default_consent_mode:
        consent_mode = defaults.default_consent_mode
    elif modes_count == 0:
        consent_mode = None
    elif modes_count > 1:
        consent_mode = "custom"
    elif max_access_count is not None:
        consent_mode = "access_count"
    elif expires_at is not None:
        consent_mode = "time_bound"
    else:
        consent_mode = "trusted_orgs"

    plaintext_code = generate_code()
    code_hash_val = hash_code(plaintext_code)

    link = VerifiedLink(
        owner_id=owner_id,
        credential_id=credential.id,
        code=plaintext_code,
        code_hash=code_hash_val,
        consent_mode=consent_mode,
        expires_at=expires_at,
        allowed_org_ids=allowed_org_ids,
        max_access_count=max_access_count,
        remaining_access_count=max_access_count,
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

    # Batch fetch credentials and issuer organizations
    cred_ids = [link.credential_id for link in links]
    credentials = await Credential.find({"_id": {"$in": cred_ids}}).to_list()
    cred_map = {cred.id: cred for cred in credentials}

    issuer_org_ids = list({cred.issuer_org_id for cred in credentials if cred.issuer_org_id})
    orgs = await Organization.find({"_id": {"$in": issuer_org_ids}}).to_list()
    org_map = {org.id: org.name for org in orgs}

    items = []
    for link in links:
        cred = cred_map.get(link.credential_id)
        issuer_name = org_map.get(cred.issuer_org_id, "") if cred and cred.issuer_org_id else None
        degree_type = cred.degree_type if cred else None
        graduation_year = cred.graduation_year if cred else None

        items.append(
            VerifiedLinkResponse(
                id=str(link.id),
                code=link.code,
                credential_id=str(link.credential_id),
                consent_mode=link.consent_mode,
                expires_at=link.expires_at,
                allowed_org_ids=[str(org_id) for org_id in link.allowed_org_ids],
                max_access_count=link.max_access_count,
                remaining_access_count=link.remaining_access_count,
                display_status=derive_display_status(link),
                created_at=link.created_at,
                revoked_at=link.revoked_at,
                issuer_name=issuer_name,
                degree_type=degree_type,
                graduation_year=graduation_year,
            )
        )

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
    """Revoke a verification link."""
    try:
        obj_id = PydanticObjectId(link_id)
    except (InvalidId, TypeError):
        raise VerifiedLinkNotFoundError() from None

    link = await VerifiedLink.get(obj_id)
    if link is None or link.owner_id != owner_id or link.deleted_at is not None:
        raise VerifiedLinkNotFoundError()

    if link.status == "revoked":
        raise LinkAlreadyRevokedError()

    link.status = "revoked"
    link.revoked_at = utc_now()
    await link.save()
    return link


async def update_verified_link(
    owner_id: PydanticObjectId,
    link_id: str,
    payload: UpdateVerifiedLinkRequest,
) -> VerifiedLink:
    """Update consent settings on an existing active verification link."""
    try:
        obj_id = PydanticObjectId(link_id)
    except (InvalidId, TypeError):
        raise VerifiedLinkNotFoundError() from None

    link = await VerifiedLink.get(obj_id)
    if link is None or link.owner_id != owner_id or link.deleted_at is not None:
        raise VerifiedLinkNotFoundError()

    if link.status == "revoked":
        raise LinkAlreadyRevokedError()

    now = datetime.now(UTC)
    fields_set = payload.model_fields_set

    # 1. Update expires_at
    if "expires_at" in fields_set:
        if payload.expires_at is not None:
            exp = payload.expires_at.replace(tzinfo=UTC) if payload.expires_at.tzinfo is None else payload.expires_at
            if exp <= now:
                raise InvalidExpirationError()
        link.expires_at = payload.expires_at

    # 2. Update max_access_count
    if "max_access_count" in fields_set:
        if payload.max_access_count is not None and payload.max_access_count < 1:
            raise InvalidAccessCountError()
        link.max_access_count = payload.max_access_count
        link.remaining_access_count = payload.max_access_count

    # 3. Update allowed_org_ids
    if "allowed_org_ids" in fields_set:
        if payload.allowed_org_ids is None:
            link.allowed_org_ids = []
        else:
            allowed_org_ids: list[PydanticObjectId] = []
            for org_str in payload.allowed_org_ids:
                try:
                    allowed_org_ids.append(PydanticObjectId(org_str))
                except (InvalidId, TypeError):
                    raise InvalidOrgIdError() from None

            if allowed_org_ids:
                count = await Organization.find({"_id": {"$in": allowed_org_ids}}).count()
                if count != len(allowed_org_ids):
                    raise InvalidOrgIdError()
            link.allowed_org_ids = allowed_org_ids

    # Recalculate consent_mode
    modes_count = sum([
        link.max_access_count is not None,
        link.expires_at is not None,
        bool(link.allowed_org_ids),
    ])
    if modes_count == 0:
        link.consent_mode = None
    elif modes_count > 1:
        link.consent_mode = "custom"
    elif link.max_access_count is not None:
        link.consent_mode = "access_count"
    elif link.expires_at is not None:
        link.consent_mode = "time_bound"
    else:
        link.consent_mode = "trusted_orgs"

    await link.save()
    return link

