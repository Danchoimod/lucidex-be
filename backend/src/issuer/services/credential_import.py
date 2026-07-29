"""Issuer credential import service."""

import csv
import io
from datetime import UTC, date, datetime
from typing import Any

from fastapi import UploadFile

from src.credential.models import Credential
from src.issuer.exceptions import (
    CredentialFileUploadFailedError,
    CredentialImportFailedError,
    CsvNoRecordsError,
    FileRequiredError,
    InvalidFileFormatError,
    InvalidOverwriteValueError,
    ItemsLimitExceededError,
)
from src.issuer.schemas import CredentialImportData
from src.models import utc_now
from src.organization.models import InstitutionAccount, Organization
from src.utils.gcs_storage import upload_file

MAX_IMPORT_ROWS = 5000

# Canonical field names required in parsed payload
REQUIRED_CANONICAL_FIELDS = {
    "student_id",
    "full_name",
    "dob",
    "graduation_year",
    "university_email",
}

# Alias dictionary mapping flexible CSV column headers to canonical field names
HEADER_ALIASES = {
    # student_id
    "student_id": "student_id",
    "studentid": "student_id",
    "student id": "student_id",
    "student": "student_id",
    "mssv": "student_id",
    "ma sinh vien": "student_id",
    "ma sv": "student_id",
    # full_name
    "full_name": "full_name",
    "fullname": "full_name",
    "full name": "full_name",
    "ho va ten": "full_name",
    "ho ten": "full_name",
    "ten sinh vien": "full_name",
    # dob
    "dob": "dob",
    "date of birth": "dob",
    "ngay sinh": "dob",
    # major_vi
    "major_vi": "major_vi",
    "vi-major": "major_vi",
    "vi_major": "major_vi",
    "vi major": "major_vi",
    "major": "major_vi",
    "nganh hoc (vi)": "major_vi",
    "nganh hoc": "major_vi",
    # major_en
    "major_en": "major_en",
    "en-major": "major_en",
    "en_major": "major_en",
    "en major": "major_en",
    # graduation_year
    "graduation_year": "graduation_year",
    "graduationyear": "graduation_year",
    "graduation year": "graduation_year",
    "graduation": "graduation_year",
    "nam tot nghiep": "graduation_year",
    "nam tn": "graduation_year",
    # graduation_classification_vi
    "graduation_classification_vi": "graduation_classification_vi",
    "vi - graduation classification": "graduation_classification_vi",
    "vi-graduation classification": "graduation_classification_vi",
    "vi_graduation_classification": "graduation_classification_vi",
    "vi - graduation": "graduation_classification_vi",
    "vi - gradua": "graduation_classification_vi",
    "classification": "graduation_classification_vi",
    "xep loai tot nghiep": "graduation_classification_vi",
    "xep loai": "graduation_classification_vi",
    # graduation_classification_en
    "graduation_classification_en": "graduation_classification_en",
    "en - graduation classification": "graduation_classification_en",
    "en-graduation classification": "graduation_classification_en",
    "en_graduation_classification": "graduation_classification_en",
    "en - graduation": "graduation_classification_en",
    "en - gradua": "graduation_classification_en",
    # mode_of_study_vi
    "mode_of_study_vi": "mode_of_study_vi",
    "vi - mode of study": "mode_of_study_vi",
    "vi-mode of study": "mode_of_study_vi",
    "vi_mode_of_study": "mode_of_study_vi",
    "vi - mode o": "mode_of_study_vi",
    "vi - mode": "mode_of_study_vi",
    "hinh thuc dao tao": "mode_of_study_vi",
    # mode_of_study_en
    "mode_of_study_en": "mode_of_study_en",
    "en - mode of study": "mode_of_study_en",
    "en-mode of study": "mode_of_study_en",
    "en_mode_of_study": "mode_of_study_en",
    "en - mode o": "mode_of_study_en",
    "en - mode": "mode_of_study_en",
    # university_email
    "university_email": "university_email",
    "universityemail": "university_email",
    "university email": "university_email",
    "university e": "university_email",
    "email": "university_email",
    "email truong": "university_email",
    # national_id_hash
    "national_id_hash": "national_id_hash",
    "national id (hashed)": "national_id_hash",
    "national id(hashed)": "national_id_hash",
    "national id": "national_id_hash",
    "national_id": "national_id_hash",
    "cccd": "national_id_hash",
    "cmnd": "national_id_hash",
    # class_id
    "class_id": "class_id",
    "classid": "class_id",
    "class id": "class_id",
    "lop": "class_id",
    "ma lop": "class_id",
}


import logging
import re

logger = logging.getLogger(__name__)


def _parse_dob(val: str) -> date:
    val = val.strip()
    # Remove time component if present e.g. "2001-05-15 00:00:00" or "2001-05-15T00:00:00"
    if " " in val:
        val = val.split(" ")[0]
    if "T" in val:
        val = val.split("T")[0]

    for fmt in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%d.%m.%Y",
        "%Y.%m.%d",
    ):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            pass

    parts = [p for p in re.split(r"[-/\.\s]", val) if p]
    if len(parts) >= 3:
        try:
            if len(parts[0]) == 4:
                return date(int(parts[0]), int(parts[1]), int(parts[2]))
            elif len(parts[2]) == 4:
                return date(int(parts[2]), int(parts[1]), int(parts[0]))
        except (ValueError, TypeError):
            pass

    raise ValueError(
        f"Invalid date of birth format: '{val}'. Expected YYYY-MM-DD or DD/MM/YYYY."
    )


def _decode_csv_content(content: bytes) -> str:
    if content.startswith(b"PK\x03\x04"):
        raise InvalidFileFormatError(
            "File uploaded is an Excel (.xlsx) file. Please save or export your file as CSV (.csv) before uploading."
        )

    for enc in ("utf-8-sig", "utf-8", "utf-16", "utf-16-le", "utf-16-be", "cp1258", "cp1252", "latin-1"):
        try:
            text = content.decode(enc)
            if "\x00" in text:
                continue
            return text
        except (UnicodeDecodeError, UnicodeError):
            continue

    return content.decode("utf-8", errors="replace").replace("\x00", "")


def _parse_overwrite_all(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        val_lower = value.strip().lower()
        if val_lower == "true":
            return True
        if val_lower == "false":
            return False
    raise InvalidOverwriteValueError()


class CredentialImportService:
    """Service handling bulk CSV import of graduate credentials."""

    async def import_credentials(
        self,
        *,
        file: UploadFile | None,
        overwrite_all_raw: Any,
        organization: Organization,
        actor: InstitutionAccount,
    ) -> CredentialImportData:
        # 1. Validate file presence
        if file is None or not file.filename:
            raise FileRequiredError()

        if not file.filename.lower().endswith(".csv"):
            raise InvalidFileFormatError("Uploaded file must be a .csv file.")

        overwrite_all = _parse_overwrite_all(overwrite_all_raw)

        # 2. Read and decode file content
        content = await file.read()
        if len(content) == 0:
            raise FileRequiredError("Uploaded CSV file is empty.")

        text_content = _decode_csv_content(content)

        # 3. Parse CSV rows & validate header (auto detect delimiter: comma, semicolon, tab)
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

        # Map raw column names from CSV to canonical field names
        column_map: dict[str, str] = {}
        found_canonical: set[str] = set()

        for raw_field in reader.fieldnames:
            if not raw_field:
                continue
            normalized_raw = raw_field.strip().lstrip("\ufeff").strip().lower()
            # Prefix partial matching for truncated headers e.g. "University e" -> "university_email", "Graduation" -> "graduation_year"
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

        logger.info(f"CSV import parsed headers: raw={reader.fieldnames}, mapped={column_map}")

        missing_fields = REQUIRED_CANONICAL_FIELDS - found_canonical
        if missing_fields:
            logger.warning(f"CSV import missing required fields: {missing_fields}, raw headers was: {reader.fieldnames}")
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

        # Helper to get field value by canonical key
        def get_val(row_dict: dict, canonical_key: str) -> str | None:
            raw_col = column_map.get(canonical_key)
            if raw_col and row_dict.get(raw_col) is not None:
                val = str(row_dict[raw_col]).strip()
                return val if val else None
            return None

        # 4. Re-check duplicate credentials against DB (anti-race condition)
        student_ids = [
            get_val(row, "student_id")
            for row in rows
            if get_val(row, "student_id")
        ]

        try:
            existing_credentials = await Credential.find(
                {
                    "issuer_org_id": organization.id,
                    "student_id": {"$in": student_ids},
                }
            ).to_list()
        except Exception as exc:
            raise CredentialImportFailedError() from exc

        existing_map = {c.student_id: c for c in existing_credentials}

        total_received = len(rows)
        created_count = 0
        updated_count = 0
        skipped_count = 0

        # 5. Process DB inserts and overwrites
        try:
            for row in rows:
                student_id = get_val(row, "student_id")
                if not student_id:
                    continue

                full_name = get_val(row, "full_name") or ""
                dob_raw = get_val(row, "dob") or ""
                try:
                    dob_val = _parse_dob(dob_raw)
                except ValueError as exc:
                    raise InvalidFileFormatError(str(exc)) from exc

                grad_year_raw = get_val(row, "graduation_year") or "0"
                try:
                    graduation_year = int(grad_year_raw)
                except ValueError as exc:
                    raise InvalidFileFormatError(
                        f"Invalid graduation_year '{grad_year_raw}' for student_id '{student_id}'."
                    ) from exc

                university_email = get_val(row, "university_email") or ""
                major_vi = get_val(row, "major_vi")
                major_en = get_val(row, "major_en")
                major_summary = major_vi or major_en or ""

                grad_class_vi = get_val(row, "graduation_classification_vi")
                grad_class_en = get_val(row, "graduation_classification_en")
                class_summary = grad_class_vi or grad_class_en or ""

                mode_of_study_vi = get_val(row, "mode_of_study_vi")
                mode_of_study_en = get_val(row, "mode_of_study_en")
                class_id = get_val(row, "class_id")

                national_id_hash = get_val(row, "national_id_hash")

                if student_id in existing_map:
                    if overwrite_all:
                        existing_cred = existing_map[student_id]
                        # Only update business fields
                        existing_cred.full_name = full_name
                        existing_cred.dob = dob_val
                        existing_cred.graduation_year = graduation_year
                        existing_cred.university_email = university_email
                        existing_cred.major = major_summary
                        existing_cred.major_vi = major_vi
                        existing_cred.major_en = major_en
                        existing_cred.classification = class_summary
                        existing_cred.graduation_classification_vi = grad_class_vi
                        existing_cred.graduation_classification_en = grad_class_en
                        existing_cred.mode_of_study_vi = mode_of_study_vi
                        existing_cred.mode_of_study_en = mode_of_study_en
                        existing_cred.class_id = class_id
                        existing_cred.national_id_hash = national_id_hash

                        await existing_cred.save()
                        updated_count += 1
                    else:
                        skipped_count += 1
                else:
                    new_cred = Credential(
                        issuer_org_id=organization.id,
                        student_id=student_id,
                        full_name=full_name,
                        dob=dob_val,
                        graduation_year=graduation_year,
                        university_email=university_email,
                        major=major_summary,
                        major_vi=major_vi,
                        major_en=major_en,
                        classification=class_summary,
                        graduation_classification_vi=grad_class_vi,
                        graduation_classification_en=grad_class_en,
                        mode_of_study_vi=mode_of_study_vi,
                        mode_of_study_en=mode_of_study_en,
                        class_id=class_id,
                        national_id_hash=national_id_hash,
                        status="unclaimed",
                        unclaimed_reason_code="AWAITING_CLAIM",
                        created_at=utc_now(),
                        created_by=actor.id,
                    )
                    await new_cred.insert()
                    created_count += 1
        except (InvalidFileFormatError, CsvNoRecordsError):
            raise
        except Exception as exc:
            raise CredentialImportFailedError() from exc

        # 6. Upload CSV file to storage
        timestamp_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        object_name = f"issuer-imports/{organization.id}/{timestamp_str}_{file.filename}"

        try:
            storage_path = upload_file(
                file_content=content,
                object_name=object_name,
                content_type="text/csv",
            )
        except Exception as exc:
            raise CredentialFileUploadFailedError() from exc

        # 7. Return statistics
        return CredentialImportData(
            total_received=total_received,
            created_count=created_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
            storage_path=storage_path,
        )


credential_import_service = CredentialImportService()
