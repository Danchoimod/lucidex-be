"""Service for checking credential CSV & XLSX duplicates (Check Duplicate v2)."""

import hashlib
import re
from datetime import date, datetime
from typing import Any

from fastapi import UploadFile

from src.credential.constants import DEFAULT_DEGREE_TYPE
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
    _normalize_header_str,
    _parse_dob,
    _parse_file_rows,
)
from src.issuer.validators import (
    validate_class_id,
    validate_classification,
    validate_fullname,
    validate_graduation_year,
    validate_major,
    validate_mode_of_study,
    validate_student_id,
    validate_university_email,
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
    """Service handling bulk CSV & XLSX duplicate checking."""

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

        fn_lower = file.filename.lower()
        if not (fn_lower.endswith(".csv") or fn_lower.endswith(".xlsx") or fn_lower.endswith(".xls")):
            raise InvalidFileFormatError("Uploaded file must be a .csv or .xlsx file.")

        content = await file.read()
        if len(content) == 0:
            raise FileRequiredError("Uploaded file is empty.")

        if len(content) > MAX_FILE_SIZE_BYTES:
            raise FileSizeExceededError()

        # 2. Parse headers & rows
        raw_headers, rows = _parse_file_rows(file.filename, content)

        # 3. Map column names
        column_map: dict[str, str] = {}
        found_canonical: set[str] = set()

        for raw_field in raw_headers:
            if not raw_field:
                continue
            normalized_raw = _normalize_header_str(raw_field)
            canonical = HEADER_ALIASES.get(normalized_raw)
            if not canonical:
                if "ho" in normalized_raw and "dem" in normalized_raw:
                    canonical = "last_and_middle_name"
                elif "mssv" in normalized_raw or "student" in normalized_raw:
                    canonical = "student_id"
                elif "ho & ten" in normalized_raw or "ho va ten" in normalized_raw or "full" in normalized_raw:
                    canonical = "full_name"
                elif "ngay sinh" in normalized_raw or "birth" in normalized_raw:
                    canonical = "dob"
                elif "lop" in normalized_raw:
                    canonical = "class_id"
                elif "khoa" in normalized_raw and "vien" in normalized_raw:
                    canonical = "faculty"
                elif "chuyen nganh" in normalized_raw:
                    canonical = "specialization"
                elif "nganh" in normalized_raw:
                    canonical = "major_vi"
                elif "cpa" in normalized_raw or "tbc" in normalized_raw:
                    canonical = "cpa"
                elif "so hieu" in normalized_raw:
                    canonical = "degree_number"
                elif "so vao so" in normalized_raw:
                    canonical = "register_number"
                elif "ghi chu" in normalized_raw:
                    canonical = "notes"
                elif "cccd" in normalized_raw or "cmnd" in normalized_raw:
                    canonical = "national_id_hash"
                elif "loai bang" in normalized_raw or "degree" in normalized_raw:
                    canonical = "degree_type"

            if canonical:
                column_map[canonical] = raw_field
                found_canonical.add(canonical)

        has_name = (
            "full_name" in found_canonical
            or "first_name" in found_canonical
            or "last_and_middle_name" in found_canonical
        )
        if "student_id" not in found_canonical or "dob" not in found_canonical or not has_name:
            missing_fields = set()
            if "student_id" not in found_canonical:
                missing_fields.add("student_id")
            if "dob" not in found_canonical:
                missing_fields.add("dob")
            if not has_name:
                missing_fields.add("full_name")
            raise InvalidFileFormatError(
                f"File header template is missing required columns: {', '.join(sorted(missing_fields))}."
            )

        if len(rows) == 0:
            raise CsvNoRecordsError()

        if len(rows) > MAX_IMPORT_ROWS:
            raise ItemsLimitExceededError(
                f"Row count ({len(rows)}) exceeds the maximum allowed limit of {MAX_IMPORT_ROWS} rows."
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

        student_ids = [
            get_val(row, "student_id")
            for row in rows
            if get_val(row, "student_id")
        ]

        if organization.last_import_checksum and organization.last_import_checksum == checksum:
            active_count = await Credential.find(
                {
                    "issuer_org_id": organization.id,
                    "deleted_at": None,
                    "student_id": {"$in": student_ids},
                }
            ).count()
            if active_count == len(student_ids) and active_count > 0:
                raise FileAlreadyImportedError(
                    message="This file appears identical to a previously imported file.",
                    data={
                        "total_rows": total_rows,
                        "has_duplicates": True,
                        "duplicate_count": total_rows,
                        "duplicates": [],
                    },
                )

        existing_credentials = await Credential.find(
            {
                "issuer_org_id": organization.id,
                "deleted_at": None,
                "student_id": {"$in": student_ids},
            }
        ).to_list()

        existing_map = {c.student_id: c for c in existing_credentials}

        # 5. Build duplicate items
        duplicates: list[DuplicateCredentialItemData] = []

        for idx, row in enumerate(rows):
            row_number = idx + 2  # Row number starting from 2 (after header)
            student_id = get_val(row, "student_id")
            if not student_id:
                continue

            try:
                validate_student_id(student_id)

                full_name = get_val(row, "full_name")
                if not full_name:
                    ho_dem = get_val(row, "last_and_middle_name") or ""
                    ten = get_val(row, "first_name") or ""
                    full_name = f"{ho_dem} {ten}".strip()
                validate_fullname(full_name)

                dob_raw = get_val(row, "dob") or ""
                parsed_dob = _parse_dob(dob_raw)

                class_code = get_val(row, "class_id") or ""
                if class_code:
                    validate_class_id(class_code)

                grad_year_raw = get_val(row, "graduation_year")
                grad_year_val = None
                if grad_year_raw:
                    try:
                        grad_year_val = validate_graduation_year(int(float(grad_year_raw)))
                    except ValueError:
                        pass
                if not grad_year_val:
                    years = re.findall(r"\b(20\d{2})\b", class_code)
                    if years:
                        grad_year_val = int(years[-1])
                    else:
                        grad_year_val = datetime.now().year

                university_email = get_val(row, "university_email")
                if university_email:
                    validate_university_email(university_email)

                major_vi = get_val(row, "major_vi")
                if major_vi:
                    validate_major(major_vi, "major_vi")

                major_en = get_val(row, "major_en")
                if major_en:
                    validate_major(major_en, "major_en")

                grad_class_vi = get_val(row, "graduation_classification_vi")
                if grad_class_vi:
                    validate_classification(grad_class_vi, "graduation_classification_vi")

                grad_class_en = get_val(row, "graduation_classification_en")
                if grad_class_en:
                    validate_classification(grad_class_en, "graduation_classification_en")

                mode_of_study_vi = get_val(row, "mode_of_study_vi")
                if mode_of_study_vi:
                    validate_mode_of_study(mode_of_study_vi, "mode_of_study_vi")

                mode_of_study_en = get_val(row, "mode_of_study_en")
                if mode_of_study_en:
                    validate_mode_of_study(mode_of_study_en, "mode_of_study_en")

                place_of_birth = get_val(row, "place_of_birth")
                gender = get_val(row, "gender")
                degree_type_val = get_val(row, "degree_type") or DEFAULT_DEGREE_TYPE
                faculty = get_val(row, "faculty")
                specialization = get_val(row, "specialization")
                cpa = get_val(row, "cpa")
                degree_number = get_val(row, "degree_number")
                register_number = get_val(row, "register_number")
                notes = get_val(row, "notes")

                raw_national_id = get_val(row, "national_id_hash")
                incoming_nid_hash = (
                    hash_imported_national_id(raw_national_id)
                    if raw_national_id
                    else None
                )
            except ValueError as exc:
                raise InvalidFileFormatError(f"Row {row_number}: {exc}") from exc

            if student_id in existing_map:
                existing_cred = existing_map[student_id]

                existing_dob_str = (
                    existing_cred.dob.strftime("%Y-%m-%d")
                    if isinstance(existing_cred.dob, date)
                    else str(existing_cred.dob)
                )

                existing_data = ExistingCredentialData(
                    full_name=existing_cred.full_name,
                    dob=existing_dob_str,
                    major=getattr(existing_cred, "major", None) or getattr(existing_cred, "major_vi", None),
                    major_vi=getattr(existing_cred, "major_vi", None),
                    major_en=getattr(existing_cred, "major_en", None),
                    graduation_year=existing_cred.graduation_year,
                    classification=getattr(existing_cred, "classification", None) or getattr(existing_cred, "graduation_classification_vi", None),
                    graduation_classification_vi=getattr(existing_cred, "graduation_classification_vi", None),
                    graduation_classification_en=getattr(existing_cred, "graduation_classification_en", None),
                    mode_of_study=getattr(existing_cred, "mode_of_study_vi", None),
                    mode_of_study_vi=getattr(existing_cred, "mode_of_study_vi", None),
                    mode_of_study_en=getattr(existing_cred, "mode_of_study_en", None),
                    university_email=getattr(existing_cred, "university_email", None),
                    place_of_birth=getattr(existing_cred, "place_of_birth", None),
                    gender=getattr(existing_cred, "gender", None),
                    degree_type=getattr(existing_cred, "degree_type", None) or DEFAULT_DEGREE_TYPE,
                    faculty=getattr(existing_cred, "faculty", None),
                    specialization=getattr(existing_cred, "specialization", None),
                    cpa=getattr(existing_cred, "cpa", None),
                    degree_number=getattr(existing_cred, "degree_number", None),
                    register_number=getattr(existing_cred, "register_number", None),
                    notes=getattr(existing_cred, "notes", None),
                    national_id_hash=getattr(existing_cred, "national_id_hash", None),
                )

                incoming_dob_str = parsed_dob.strftime("%Y-%m-%d")

                incoming_data = IncomingCredentialData(
                    full_name=full_name,
                    dob=incoming_dob_str,
                    major=major_vi or major_en,
                    major_vi=major_vi,
                    major_en=major_en,
                    graduation_year=grad_year_val,
                    classification=grad_class_vi or grad_class_en,
                    graduation_classification_vi=grad_class_vi,
                    graduation_classification_en=grad_class_en,
                    mode_of_study=mode_of_study_vi or mode_of_study_en,
                    mode_of_study_vi=mode_of_study_vi,
                    mode_of_study_en=mode_of_study_en,
                    university_email=university_email,
                    place_of_birth=place_of_birth,
                    gender=gender,
                    degree_type=degree_type_val,
                    faculty=faculty,
                    specialization=specialization,
                    cpa=cpa,
                    degree_number=degree_number,
                    register_number=register_number,
                    notes=notes,
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

        # 6. Apply Threshold Rule (total_rows >= 50 and duplicate_count / total_rows >= 90%)
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

        # 7. Return detailed check result
        has_duplicates = duplicate_count > 0

        return CheckDuplicatesData(
            total_rows=total_rows,
            has_duplicates=has_duplicates,
            duplicate_count=duplicate_count,
            duplicate_ratio=None,
            duplicates=duplicates,
        )


credential_check_duplicates_service = CredentialCheckDuplicatesService()
