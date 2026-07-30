"""Service for checking credential CSV duplicates (Check Duplicate v2)."""

import csv
from datetime import date, datetime
import hashlib
import io
from typing import Any

from fastapi import UploadFile

from src.credential.models import Credential
from src.credential.services.hashing import hash_imported_national_id
from src.issuer.exceptions import (
    CsvNoRecordsError,
    DuplicateThresholdExceededError,
    FileAlreadyImportedError,
    FileRequiredError,
    FileSizeExceededError,
    InvalidFileFormatError,
    ItemsLimitExceededError,
)
from src.issuer.schemas import (
    CheckDuplicatesData,
    DuplicateCredentialItemData,
    ExistingCredentialData,
    IncomingCredentialData,
)
from src.issuer.services.credential_import import (
    HEADER_ALIASES,
    MAX_IMPORT_ROWS,
    REQUIRED_CANONICAL_FIELDS,
    _decode_csv_content,
    _parse_dob,
)
from src.organization.models import InstitutionAccount, Organization

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def compute_file_checksum(items: list[tuple[str, str]]) -> str:
    """Computes SHA-256 checksum for normalized (student_id, class_code) tuples."""
    normalized_pairs = sorted(
        [f"{sid.strip().upper()}:{cc.strip().upper()}" for sid, cc in items]
    )
    raw_str = "|".join(normalized_pairs)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


class CredentialCheckDuplicatesService:
    """Service handling bulk CSV duplicate checking."""

    async def check_duplicates(
        self,
        *,
        file: UploadFile | None,
        organization: Organization,
        actor: InstitutionAccount,
    ) -> CheckDuplicatesData:
        # 1. Validate file presence & size (< 10MB)
        if file is None or not file.filename:
            raise FileRequiredError()

        if not file.filename.lower().endswith(".csv"):
            raise InvalidFileFormatError("Uploaded file must be a .csv file.")

        content = await file.read()
        if len(content) == 0:
            raise FileRequiredError("Uploaded CSV file is empty.")

        if len(content) > MAX_FILE_SIZE_BYTES:
            raise FileSizeExceededError()

        # 2. Decode CSV content & detect delimiter
        text_content = _decode_csv_content(content)

        non_empty_lines = [line.strip() for line in text_content.splitlines() if line.strip()]
        first_line = non_empty_lines[0] if non_empty_lines else ""
        delimiter = ","
        if ";" in first_line and first_line.count(";") > first_line.count(","):
            delimiter = ";"
        elif "\t" in first_line and first_line.count("\t") > first_line.count(","):
            delimiter = "\t"

        stream = io.StringIO(text_content)
        reader = csv.DictReader(stream, delimiter=delimiter)

        if not reader.fieldnames:
            raise InvalidFileFormatError("CSV file header is missing or empty.")

        # 3. Map column names
        column_map: dict[str, str] = {}
        found_canonical: set[str] = set()

        for raw_field in reader.fieldnames:
            if not raw_field:
                continue
            normalized_raw = raw_field.strip().lstrip("\ufeff").strip().lower()
            canonical = HEADER_ALIASES.get(normalized_raw)
            if not canonical:
                if normalized_raw.startswith("university") or "email" in normalized_raw:
                    canonical = "university_email"
                elif normalized_raw.startswith("student") or "mssv" in normalized_raw:
                    canonical = "student_id"
                elif normalized_raw.startswith("full") or "ho ten" in normalized_raw or "ho va ten" in normalized_raw:
                    canonical = "full_name"
                elif normalized_raw == "dob" or "birth" in normalized_raw or "ngay sinh" in normalized_raw:
                    canonical = "dob"
                elif normalized_raw.startswith("graduation"):
                    canonical = "graduation_year"
                elif normalized_raw.startswith("vi") and "grad" in normalized_raw:
                    canonical = "graduation_classification_vi"
                elif normalized_raw.startswith("en") and "grad" in normalized_raw:
                    canonical = "graduation_classification_en"
                elif normalized_raw.startswith("vi") and "mode" in normalized_raw:
                    canonical = "mode_of_study_vi"
                elif normalized_raw.startswith("en") and "mode" in normalized_raw:
                    canonical = "mode_of_study_en"
                elif "national" in normalized_raw or "cccd" in normalized_raw:
                    canonical = "national_id_hash"
                elif "class" in normalized_raw or "lop" in normalized_raw:
                    canonical = "class_id"

            if canonical:
                column_map[canonical] = raw_field
                found_canonical.add(canonical)

        missing_fields = REQUIRED_CANONICAL_FIELDS - found_canonical
        if missing_fields:
            raise InvalidFileFormatError(
                f"CSV header template is missing required columns: {', '.join(sorted(missing_fields))}."
            )

        rows = list(reader)
        if len(rows) == 0:
            raise CsvNoRecordsError()

        if len(rows) > MAX_IMPORT_ROWS:
            raise ItemsLimitExceededError(
                f"CSV row count ({len(rows)}) exceeds the maximum allowed limit of {MAX_IMPORT_ROWS} rows."
            )

        def get_val(row_dict: dict, canonical_key: str) -> str | None:
            raw_col = column_map.get(canonical_key)
            if raw_col and row_dict.get(raw_col) is not None:
                val = str(row_dict[raw_col]).strip()
                return val if val else None
            return None

        total_rows = len(rows)

        # 4. Check checksum of normalized (student_id, class_code) against last successful import
        pairs = [
            (get_val(row, "student_id") or "", get_val(row, "class_id") or "")
            for row in rows
        ]
        checksum = compute_file_checksum(pairs)

        if organization.last_import_checksum and organization.last_import_checksum == checksum:
            raise FileAlreadyImportedError(
                message="This file appears identical to a previously imported file.",
                data={
                    "total_rows": total_rows,
                    "has_duplicates": True,
                    "duplicate_count": total_rows,
                    "duplicates": [],
                },
            )

        # 5. Query DB using 1 $in query excluding soft-deleted records (deleted_at == None)
        student_ids = [
            get_val(row, "student_id")
            for row in rows
            if get_val(row, "student_id")
        ]

        existing_credentials = await Credential.find(
            {
                "issuer_org_id": organization.id,
                "deleted_at": None,
                "student_id": {"$in": student_ids},
            }
        ).to_list()

        existing_map = {c.student_id: c for c in existing_credentials}

        # 6. Build duplicate items
        duplicates: list[DuplicateCredentialItemData] = []

        for idx, row in enumerate(rows):
            row_number = idx + 2  # Row number starting from 2 (after header)
            student_id = get_val(row, "student_id")
            if not student_id:
                continue

            class_code = get_val(row, "class_id") or ""

            if student_id in existing_map:
                existing_cred = existing_map[student_id]

                # DOB to string YYYY-MM-DD
                existing_dob_str = (
                    existing_cred.dob.strftime("%Y-%m-%d")
                    if isinstance(existing_cred.dob, date)
                    else str(existing_cred.dob)
                )

                existing_data = ExistingCredentialData(
                    full_name=existing_cred.full_name,
                    dob=existing_dob_str,
                    major_vi=existing_cred.major_vi,
                    major_en=existing_cred.major_en,
                    graduation_year=existing_cred.graduation_year,
                    graduation_classification_vi=existing_cred.graduation_classification_vi,
                    graduation_classification_en=existing_cred.graduation_classification_en,
                    mode_of_study_vi=existing_cred.mode_of_study_vi,
                    mode_of_study_en=existing_cred.mode_of_study_en,
                    university_email=existing_cred.university_email,
                    national_id_hash=existing_cred.national_id_hash,
                )

                dob_raw = get_val(row, "dob") or ""
                try:
                    parsed_dob = _parse_dob(dob_raw)
                    incoming_dob_str = parsed_dob.strftime("%Y-%m-%d")
                except ValueError:
                    incoming_dob_str = dob_raw

                grad_year_raw = get_val(row, "graduation_year") or "0"
                try:
                    grad_year_val = int(grad_year_raw)
                except ValueError:
                    grad_year_val = 0

                raw_national_id = get_val(row, "national_id_hash")
                try:
                    incoming_nid_hash = hash_imported_national_id(raw_national_id)
                except ValueError:
                    incoming_nid_hash = raw_national_id

                incoming_data = IncomingCredentialData(
                    full_name=get_val(row, "full_name") or "",
                    dob=incoming_dob_str,
                    major_vi=get_val(row, "major_vi"),
                    major_en=get_val(row, "major_en"),
                    graduation_year=grad_year_val,
                    graduation_classification_vi=get_val(row, "graduation_classification_vi"),
                    graduation_classification_en=get_val(row, "graduation_classification_en"),
                    mode_of_study_vi=get_val(row, "mode_of_study_vi"),
                    mode_of_study_en=get_val(row, "mode_of_study_en"),
                    university_email=get_val(row, "university_email") or "",
                    national_id_hash=incoming_nid_hash,
                )

                duplicates.append(
                    DuplicateCredentialItemData(
                        row_number=row_number,
                        student_id=student_id,
                        class_code=class_code,
                        existing=existing_data,
                        incoming=incoming_data,
                    )
                )

        duplicate_count = len(duplicates)

        # 7. Apply Threshold Rule (total_rows >= 50 and duplicate_count / total_rows >= 90%)
        if total_rows >= 50 and (duplicate_count / total_rows) >= 0.9:
            duplicate_ratio = round(duplicate_count / total_rows, 2)
            ratio_pct = int(duplicate_ratio * 100)
            raise DuplicateThresholdExceededError(
                message=f"{duplicate_count}/{total_rows} rows ({ratio_pct}%) already exist. Showing summary instead of full detail.",
                data={
                    "total_rows": total_rows,
                    "has_duplicates": True,
                    "duplicate_count": duplicate_count,
                    "duplicate_ratio": duplicate_ratio,
                    "duplicates": [],
                },
            )

        # 8. Return detailed check result
        has_duplicates = duplicate_count > 0
        message = (
            "Duplicate check completed."
            if has_duplicates
            else "No duplicate credentials found."
        )

        return CheckDuplicatesData(
            total_rows=total_rows,
            has_duplicates=has_duplicates,
            duplicate_count=duplicate_count,
            duplicate_ratio=None,
            duplicates=duplicates,
        )


credential_check_duplicates_service = CredentialCheckDuplicatesService()
