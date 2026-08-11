import hashlib
from datetime import UTC, datetime

from src.credential.constants import DENIAL_MESSAGES
from src.credential.models import Credential, VerifiedLink, VerifiedLinkAccessLog
from src.credential.schemas import VerifyCodeCredentialData, VerifyCodeResponse
from src.models import utc_now
from src.organization.models import InstitutionAccount, Organization
from src.schemas.common import ApiResponse


async def verify_code(
    plaintext_code: str,
    verifier_account: InstitutionAccount,
) -> ApiResponse[VerifyCodeResponse]:
    """Verify a code and return the credential details if valid, or a denial ApiResponse."""
    code_hash_val = hashlib.sha256(plaintext_code.strip().upper().encode("utf-8")).hexdigest()

    # Search for matching link by code_hash
    link = await VerifiedLink.find_one({"code_hash": code_hash_val, "deleted_at": None})
    if link is None:
        return ApiResponse(
            success=False,
            data=None,
            message=DENIAL_MESSAGES["INVALID_VERIFICATION_CODE"],
            error_code="INVALID_VERIFICATION_CODE",
        )

    # 1. Revoked check
    if link.status == "revoked":
        return ApiResponse(
            success=False,
            data=None,
            message=DENIAL_MESSAGES["LINK_REVOKED"],
            error_code="LINK_REVOKED",
        )

    # 2. Expiration check
    now = datetime.now(UTC)
    if link.expires_at is not None:
        exp = link.expires_at.replace(tzinfo=UTC) if link.expires_at.tzinfo is None else link.expires_at
        if exp <= now:
            return ApiResponse(
                success=False,
                data=None,
                message=DENIAL_MESSAGES["LINK_EXPIRED"],
                error_code="LINK_EXPIRED",
            )

    # 3. Access count check
    if link.max_access_count is not None and link.remaining_access_count is not None:
        if link.remaining_access_count <= 0:
            return ApiResponse(
                success=False,
                data=None,
                message=DENIAL_MESSAGES["LINK_EXPIRED"],
                error_code="LINK_EXPIRED",
            )

    # 4. Allowed organization check
    if link.allowed_org_ids:
        if verifier_account.org_id not in link.allowed_org_ids:
            return ApiResponse(
                success=False,
                data=None,
                message=DENIAL_MESSAGES["UNAUTHORIZED_VERIFIER"],
                error_code="UNAUTHORIZED_VERIFIER",
            )

    # 5. Credential status check
    credential = await Credential.get(link.credential_id)
    if credential is None or credential.status == "revoked":
        return ApiResponse(
            success=False,
            data=None,
            message=DENIAL_MESSAGES["CREDENTIAL_REVOKED"],
            error_code="CREDENTIAL_REVOKED",
        )

    # 6. Atomic decrement remaining access count if set
    if link.max_access_count is not None and link.remaining_access_count is not None:
        updated = await VerifiedLink.find_one(
            {
                "_id": link.id,
                "remaining_access_count": {"$gt": 0},
            }
        ).update({"$inc": {"remaining_access_count": -1}})
        if updated is None or updated.modified_count == 0:
            return ApiResponse(
                success=False,
                data=None,
                message=DENIAL_MESSAGES["LINK_EXPIRED"],
                error_code="LINK_EXPIRED",
            )

    # 7. Write access log
    verified_time = utc_now()
    access_log = VerifiedLinkAccessLog(
        link_id=link.id,
        owner_id=link.owner_id,
        credential_id=link.credential_id,
        verifier_org_id=verifier_account.org_id,
        verifier_account_id=verifier_account.id,
        verified_at=verified_time,
    )
    await access_log.insert()

    # Fetch issuer organization for issuer_name
    issuer_org = await Organization.get(credential.issuer_org_id)
    issuer_name = issuer_org.name if issuer_org else ""

    major_val = credential.major_vi or credential.major
    classification_val = credential.graduation_classification_vi or credential.classification
    mode_val = credential.mode_of_study or credential.mode_of_study_vi

    credential_data = VerifyCodeCredentialData(
        id=str(credential.id),
        issuer_org_id=str(credential.issuer_org_id),
        issuer_name=issuer_name,
        student_id=credential.student_id,
        full_name=credential.full_name,
        dob=credential.dob,
        pob=credential.place_of_birth,
        gender=credential.gender,
        national_id=None,
        degree_type=credential.degree_type,
        class_id=credential.class_id,
        faculty=credential.faculty,
        major=major_val,
        specialization=credential.specialization,
        gpa=float(credential.cpa) if credential.cpa else None,
        classification=classification_val,
        mode_of_study=mode_val,
        degree_number=credential.degree_number,
        registration_number=credential.register_number,
        graduation_year=credential.graduation_year,
        status=credential.status,
    )

    return ApiResponse(
        success=True,
        data=VerifyCodeResponse(
            credential=credential_data,
            verified_at=verified_time,
        ),
        message="Credential verified successfully.",
        error_code=None,
    )
