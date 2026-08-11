import csv
import hashlib
import io
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import UploadFile

from src.credential.models import Credential, VerifiedLink, VerifiedLinkAccessLog
from src.models import utc_now
from src.organization.models import InstitutionAccount
from src.verifier.exceptions import BulkVerifyRowLimitExceededError, InvalidCsvFileError
from src.verifier.schemas import (
    BulkVerifyResponse,
    BulkVerifyRowResult,
    BulkVerifySummary,
)

MAX_BULK_VERIFY_ROWS = 500


@dataclass
class BulkRowOutcome:
    row_number: int
    code: str
    status: str  # "active" | "expired" | "revoked" | "not_found"
    is_restricted: bool = False
    credential_id: str | None = None
    owner_name: str | None = None
    credential_type: str | None = None


async def _verify_one_code(
    row_number: int,
    plaintext_code: str,
    verifier_account: InstitutionAccount,
) -> BulkRowOutcome:
    """Verify a single code, applying checks sequentially."""
    clean_code = plaintext_code.strip()
    code_hash_val = hashlib.sha256(clean_code.upper().encode("utf-8")).hexdigest()

    # 1. Search for matching link by code_hash
    link = await VerifiedLink.find_one({"code_hash": code_hash_val, "deleted_at": None})
    if link is None:
        return BulkRowOutcome(
            row_number=row_number,
            code=clean_code,
            status="not_found",
        )

    # 2. Revoked check
    if link.status == "revoked":
        return BulkRowOutcome(
            row_number=row_number,
            code=clean_code,
            status="revoked",
        )

    # 3. Expiration check
    now = datetime.now(UTC)
    if link.expires_at is not None:
        exp = (
            link.expires_at.replace(tzinfo=UTC)
            if link.expires_at.tzinfo is None
            else link.expires_at
        )
        if exp <= now:
            return BulkRowOutcome(
                row_number=row_number,
                code=clean_code,
                status="expired",
            )

    # 4. Access count check
    if link.max_access_count is not None and link.remaining_access_count is not None:
        if link.remaining_access_count <= 0:
            return BulkRowOutcome(
                row_number=row_number,
                code=clean_code,
                status="expired",
            )

    # 5. Credential status check
    credential = await Credential.get(link.credential_id)
    if credential is None or credential.status == "revoked":
        return BulkRowOutcome(
            row_number=row_number,
            code=clean_code,
            status="revoked",
        )

    # 6. Trusted Organizations check (allowed_org_ids)
    if link.allowed_org_ids:
        if verifier_account.org_id not in link.allowed_org_ids:
            return BulkRowOutcome(
                row_number=row_number,
                code=clean_code,
                status="active",
                is_restricted=True,
            )

    # 7. Atomic decrement remaining access count if max_access_count is set
    if link.max_access_count is not None and link.remaining_access_count is not None:
        updated = await VerifiedLink.find_one(
            {
                "_id": link.id,
                "remaining_access_count": {"$gt": 0},
            }
        ).update({"$inc": {"remaining_access_count": -1}})
        if updated is None or updated.modified_count == 0:
            return BulkRowOutcome(
                row_number=row_number,
                code=clean_code,
                status="expired",
            )

    # 8. Write access log
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

    return BulkRowOutcome(
        row_number=row_number,
        code=clean_code,
        status="active",
        is_restricted=False,
        credential_id=str(credential.id),
        owner_name=credential.full_name,
        credential_type=credential.degree_type,
    )


async def bulk_verify_codes(
    file: UploadFile,
    verifier_account: InstitutionAccount,
) -> BulkVerifyResponse:
    """Synchronously verify multiple verification codes submitted via CSV file."""
    try:
        raw_bytes = await file.read()
        content_str = raw_bytes.decode("utf-8-sig")
    except Exception as exc:
        raise InvalidCsvFileError("Invalid file encoding or unreadable file.") from exc

    # Parse CSV lines
    codes: list[str] = []
    reader = csv.reader(io.StringIO(content_str))
    try:
        for row in reader:
            if not row:
                continue
            code_val = row[0].strip()
            if code_val:
                codes.append(code_val)
    except Exception as exc:
        raise InvalidCsvFileError("Failed to parse CSV file.") from exc

    if not codes:
        raise InvalidCsvFileError("Invalid or empty CSV file.")

    if len(codes) > MAX_BULK_VERIFY_ROWS:
        raise BulkVerifyRowLimitExceededError(MAX_BULK_VERIFY_ROWS)

    batch_id = str(uuid.uuid4())
    results: list[BulkVerifyRowResult] = []
    summary_counts = {"active": 0, "expired": 0, "revoked": 0, "not_found": 0}

    for idx, code in enumerate(codes, start=1):
        outcome = await _verify_one_code(idx, code, verifier_account)
        if outcome.status in summary_counts:
            summary_counts[outcome.status] += 1

        results.append(
            BulkVerifyRowResult(
                row_number=outcome.row_number,
                code=outcome.code,
                status=outcome.status,
                is_restricted=outcome.is_restricted,
                credential_id=outcome.credential_id,
                owner_name=outcome.owner_name,
                credential_type=outcome.credential_type,
            )
        )

    return BulkVerifyResponse(
        batch_id=batch_id,
        total=len(codes),
        summary=BulkVerifySummary(**summary_counts),
        results=results,
    )
