"""Issuer credential import service."""

import csv
import io
import logging
import re
import unicodedata
from datetime import UTC, date, datetime
from typing import Any

import openpyxl
from fastapi import UploadFile

from src.credential.constants import DEFAULT_DEGREE_TYPE
from src.credential.exceptions import NationalIdHashSecretNotConfiguredError
from src.credential.models import Credential
from src.credential.services.hashing import hash_imported_national_id
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
from src.models import utc_now
from src.organization.models import InstitutionAccount, Organization
from src.utils.gcs_storage import upload_file

MAX_IMPORT_ROWS = 5000

REQUIRED_CANONICAL_FIELDS = {
    "student_id",
    "dob",
}

HEADER_ALIASES = {
    # 1. stt
    "stt": "stt",
    "so thu tu": "stt",
    "no": "stt",

    # 2. student_id
    "student_id": "student_id",
    "studentid": "student_id",
    "student id": "student_id",
    "student": "student_id",
    "mssv": "student_id",
    "ma sv / mssv": "student_id",
    "ma sv/mssv": "student_id",
    "ma sinh vien": "student_id",
    "ma sv": "student_id",

    # 3. last_and_middle_name
    "last_and_middle_name": "last_and_middle_name",
    "ho & ten dem": "last_and_middle_name",
    "ho va ten dem": "last_and_middle_name",
    "ho ten dem": "last_and_middle_name",
    "ho & ten": "last_and_middle_name",
    "ho dem": "last_and_middle_name",
    "ho": "last_and_middle_name",
    "last name": "last_and_middle_name",
    "middle name": "last_and_middle_name",

    # 4. first_name
    "first_name": "first_name",
    "ten": "first_name",
    "firstname": "first_name",
    "first name": "first_name",

    # full_name
    "full_name": "full_name",
    "fullname": "full_name",
    "full name": "full_name",
    "ho va ten": "full_name",
    "ho ten": "full_name",
    "ten sinh vien": "full_name",

    # 5. dob
    "dob": "dob",
    "date of birth": "dob",
    "ngay sinh": "dob",

    # 6. place_of_birth
    "place_of_birth": "place_of_birth",
    "place of birth": "place_of_birth",
    "noi sinh": "place_of_birth",
    "pob": "place_of_birth",

    # 7. gender
    "gender": "gender",
    "gioi tinh": "gender",
    "sex": "gender",

    # 8. national_id_hash
    "national_id_hash": "national_id_hash",
    "national id (hashed)": "national_id_hash",
    "national id(hashed)": "national_id_hash",
    "national id": "national_id_hash",
    "national_id": "national_id_hash",
    "so cccd": "national_id_hash",
    "cccd": "national_id_hash",
    "cmnd": "national_id_hash",
    "so cccd/cmnd": "national_id_hash",

    # degree_type
    "degree_type": "degree_type",
    "degree type": "degree_type",
    "loai bang": "degree_type",
    "loai_bang": "degree_type",
    "loai bang / degree type": "degree_type",
    "loai bang/degree type": "degree_type",

    # 9. class_id
    "class_id": "class_id",
    "classid": "class_id",
    "class id": "class_id",
    "lop / khoa": "class_id",
    "lop/khoa": "class_id",
    "lop": "class_id",
    "ma lop": "class_id",

    # 10. faculty
    "faculty": "faculty",
    "khoa / vien": "faculty",
    "khoa/vien": "faculty",
    "khoa": "faculty",
    "vien": "faculty",
    "school": "faculty",
    "department": "faculty",

    # 11. major_vi
    "major_vi": "major_vi",
    "vi-major": "major_vi",
    "vi_major": "major_vi",
    "vi major": "major_vi",
    "major": "major_vi",
    "nganh hoc (vi)": "major_vi",
    "nganh hoc": "major_vi",
    "nganh": "major_vi",

    # major_en
    "major_en": "major_en",
    "en-major": "major_en",
    "en_major": "major_en",
    "en major": "major_en",

    # 12. specialization
    "specialization": "specialization",
    "chuyen nganh": "specialization",
    "chuyen_nganh": "specialization",
    "speciality": "specialization",
    "sub_major": "specialization",

    # 13. cpa
    "cpa": "cpa",
    "gpa": "cpa",
    "diem tbc (cpa)": "cpa",
    "diem tbc": "cpa",
    "diem trung binh chung": "cpa",
    "diem tb": "cpa",

    # 14. graduation_classification_vi
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

    # mode_of_study_vi
    "mode_of_study_vi": "mode_of_study_vi",
    "vi - mode of study": "mode_of_study_vi",
    "vi-mode of study": "mode_of_study_vi",
    "vi_mode_of_study": "mode_of_study_vi",
    "hinh thuc dao tao": "mode_of_study_vi",

    # mode_of_study_en
    "mode_of_study_en": "mode_of_study_en",
    "en - mode of study": "mode_of_study_en",

    # 15. degree_number
    "degree_number": "degree_number",
    "so hieu bang": "degree_number",
    "so hieu": "degree_number",
    "degree number": "degree_number",
    "degree serial": "degree_number",

    # 16. register_number
    "register_number": "register_number",
    "so vao so goc": "register_number",
    "so vao so": "register_number",
    "register number": "register_number",

    # 17. notes
    "notes": "notes",
    "ghi chu": "notes",
    "note": "notes",
    "remark": "notes",

    # graduation_year
    "graduation_year": "graduation_year",
    "graduationyear": "graduation_year",
    "graduation year": "graduation_year",
    "graduation": "graduation_year",
    "nam tot nghiep": "graduation_year",

    # university_email
    "university_email": "university_email",
    "universityemail": "university_email",
    "university email": "university_email",
    "email": "university_email",
}

logger = logging.getLogger(__name__)


def _parse_dob(val: Any) -> date:
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val

    val_str = str(val).strip()
    if " " in val_str:
        val_str = val_str.split(" ")[0]
    if "T" in val_str:
        val_str = val_str.split("T")[0]

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
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            pass

    parts = [p for p in re.split(r"[-/\.\s]", val_str) if p]
    if len(parts) >= 3:
        try:
            if len(parts[0]) == 4:
                return date(int(parts[0]), int(parts[1]), int(parts[2]))
            elif len(parts[2]) == 4:
                return date(int(parts[2]), int(parts[1]), int(parts[0]))
        except (ValueError, TypeError):
            pass

    raise ValueError(
        f"Invalid date of birth format: '{val_str}'. Expected YYYY-MM-DD or DD/MM/YYYY."
    )


def _decode_csv_content(content: bytes) -> str:
    for enc in (
        "utf-8-sig",
        "utf-8",
        "utf-16",
        "utf-16-le",
        "utf-16-be",
        "cp1258",
        "cp1252",
        "latin-1",
    ):
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


def _normalize_header_str(text: str) -> str:
    s = text.strip().lstrip("\ufeff").strip().lower().replace("đ", "d").replace("Đ", "d")
    s = s.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])


def _is_header_candidate_row(row_cells: tuple | list) -> int:
    score = 0
    for cell in row_cells:
        if cell is None:
            continue
        norm = _normalize_header_str(str(cell))
        if not norm:
            continue
        if norm in HEADER_ALIASES:
            score += 1
        elif any(
            kw in norm
            for kw in (
                "mssv",
                "student",
                "ma sv",
                "ngay sinh",
                "birth",
                "ho",
                "ten",
                "stt",
                "lop",
                "cccd",
                "cmnd",
                "khoa",
                "nganh",
                "loai bang",
                "cpa",
                "so hieu",
                "so vao so",
            )
        ):
            score += 1
    return score


def _parse_file_rows(filename: str, content: bytes) -> tuple[list[str], list[dict[str, Any]]]:
    fn_lower = filename.lower()
    is_excel = fn_lower.endswith((".xlsx", ".xls")) or content.startswith(b"PK\x03\x04")

    if is_excel:
        try:
            wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
            ws = wb.active
            if ws is None:
                raise InvalidFileFormatError("Excel file has no active worksheet.")

            all_rows = list(ws.iter_rows(values_only=True))
            non_empty_rows = [
                r for r in all_rows if r and any(cell is not None and str(cell).strip() != "" for cell in r)
            ]
            if not non_empty_rows:
                raise InvalidFileFormatError("Excel file header is missing or empty.")

            best_header_idx = 0
            max_score = 0
            for idx, r in enumerate(non_empty_rows[:15]):
                score = _is_header_candidate_row(r)
                if score > max_score:
                    max_score = score
                    best_header_idx = idx

            raw_headers = [str(cell).strip() if cell is not None else "" for cell in non_empty_rows[best_header_idx]]
            rows: list[dict[str, Any]] = []

            for row_cells in non_empty_rows[best_header_idx + 1:]:
                row_dict: dict[str, Any] = {}
                for idx, val in enumerate(row_cells):
                    if idx < len(raw_headers) and raw_headers[idx]:
                        row_dict[raw_headers[idx]] = val
                rows.append(row_dict)

            return raw_headers, rows
        except InvalidFileFormatError:
            raise
        except Exception as exc:
            raise InvalidFileFormatError(f"Failed to parse Excel file: {exc}") from exc
    else:
        text_content = _decode_csv_content(content)
        non_empty_lines = [line.strip() for line in text_content.splitlines() if line.strip()]
        if not non_empty_lines:
            raise InvalidFileFormatError("CSV file header is missing or empty.")

        best_header_idx = 0
        max_score = 0
        delimiter = ","

        for idx, line in enumerate(non_empty_lines[:15]):
            cur_delim = ","
            if ";" in line and line.count(";") > line.count(","):
                cur_delim = ";"
            elif "\t" in line and line.count("\t") > line.count(","):
                cur_delim = "\t"

            cells = line.split(cur_delim)
            score = _is_header_candidate_row(cells)
            if score > max_score:
                max_score = score
                best_header_idx = idx
                delimiter = cur_delim

        data_lines = non_empty_lines[best_header_idx:]
        stream = io.StringIO("\n".join(data_lines))
        reader = csv.DictReader(stream, delimiter=delimiter)
        if not reader.fieldnames:
            raise InvalidFileFormatError("CSV file header is missing or empty.")

        fieldnames = [str(fn) for fn in reader.fieldnames]
        rows = list(reader)
        return fieldnames, rows


class CredentialImportService:
    """Service handling bulk CSV & XLSX import of graduate credentials."""

    async def import_credentials(
        self,
        *,
        file: UploadFile | None,
        overwrite_all_raw: Any,
        organization: Organization,
        actor: InstitutionAccount,
    ) -> CredentialImportData:
        # 1. Validate file presence & format
        if file is None or not file.filename:
            raise FileRequiredError()

        fn_lower = file.filename.lower()
        if not (fn_lower.endswith(".csv") or fn_lower.endswith(".xlsx") or fn_lower.endswith(".xls")):
            raise InvalidFileFormatError("Uploaded file must be a .csv or .xlsx file.")

        overwrite_all = _parse_overwrite_all(overwrite_all_raw)

        # 2. Read file content
        content = await file.read()
        if len(content) == 0:
            raise FileRequiredError("Uploaded file is empty.")

        # 3. Parse headers & rows
        raw_headers, rows = _parse_file_rows(file.filename, content)

        # Map raw column names to canonical field names
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

        logger.info(f"Import parsed headers: raw={raw_headers}, mapped={column_map}")

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

        # 4. Re-check duplicate credentials against DB
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

        existing_map = {(getattr(c, "student_id", None), getattr(c, "class_id", None) or ""): c for c in existing_credentials}

        total_received = len(rows)
        created_count = 0
        updated_count = 0
        skipped_count = 0

        # 5. Process DB inserts and overwrites
        try:
            for idx, row in enumerate(rows):
                student_id = get_val(row, "student_id")
                if not student_id:
                    continue

                row_num = idx + 2
                try:
                    validate_student_id(student_id)

                    full_name = get_val(row, "full_name")
                    if not full_name:
                        ho_dem = get_val(row, "last_and_middle_name") or ""
                        ten = get_val(row, "first_name") or ""
                        full_name = f"{ho_dem} {ten}".strip()
                    validate_fullname(full_name)

                    dob_raw = get_val(row, "dob") or ""
                    dob_val = _parse_dob(dob_raw)

                    class_id = get_val(row, "class_id")
                    if class_id:
                        validate_class_id(class_id)

                    grad_year_raw = get_val(row, "graduation_year")
                    graduation_year = None
                    if grad_year_raw:
                        try:
                            graduation_year = validate_graduation_year(int(float(grad_year_raw)))
                        except ValueError:
                            pass
                    if not graduation_year:
                        years = re.findall(r"\b(20\d{2})\b", class_id or "")
                        if years:
                            graduation_year = int(years[-1])
                        else:
                            graduation_year = datetime.now().year

                    university_email = get_val(row, "university_email")
                    if university_email:
                        validate_university_email(university_email)

                    major_vi = get_val(row, "major_vi")
                    if major_vi:
                        validate_major(major_vi, "major_vi")

                    major_en = get_val(row, "major_en")
                    if major_en:
                        validate_major(major_en, "major_en")
                    major_summary = major_vi or major_en or ""

                    grad_class_vi = get_val(row, "graduation_classification_vi")
                    if grad_class_vi:
                        validate_classification(grad_class_vi, "graduation_classification_vi")

                    grad_class_en = get_val(row, "graduation_classification_en")
                    if grad_class_en:
                        validate_classification(grad_class_en, "graduation_classification_en")
                    class_summary = grad_class_vi or grad_class_en or ""

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
                    national_id_hash = (
                        hash_imported_national_id(raw_national_id)
                        if raw_national_id
                        else None
                    )
                except ValueError as exc:
                    raise InvalidFileFormatError(f"Row {row_num}: {exc}") from exc

                cred_key = (student_id, class_id or "")
                if cred_key in existing_map:
                    existing_cred = existing_map[cred_key]
                    if getattr(existing_cred, "deleted_at", None) is not None:
                        existing_cred.deleted_at = None
                        existing_cred.restored_at = utc_now()
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
                        existing_cred.place_of_birth = place_of_birth
                        existing_cred.gender = gender
                        existing_cred.degree_type = degree_type_val
                        existing_cred.faculty = faculty
                        existing_cred.specialization = specialization
                        existing_cred.cpa = cpa
                        existing_cred.degree_number = degree_number
                        existing_cred.register_number = register_number
                        existing_cred.notes = notes
                        existing_cred.national_id_hash = national_id_hash

                        await existing_cred.save()
                        created_count += 1
                    elif overwrite_all:
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
                        existing_cred.place_of_birth = place_of_birth
                        existing_cred.gender = gender
                        existing_cred.degree_type = degree_type_val
                        existing_cred.faculty = faculty
                        existing_cred.specialization = specialization
                        existing_cred.cpa = cpa
                        existing_cred.degree_number = degree_number
                        existing_cred.register_number = register_number
                        existing_cred.notes = notes
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
                        place_of_birth=place_of_birth,
                        gender=gender,
                        degree_type=degree_type_val,
                        faculty=faculty,
                        specialization=specialization,
                        cpa=cpa,
                        degree_number=degree_number,
                        register_number=register_number,
                        notes=notes,
                        national_id_hash=national_id_hash,
                        status="unclaimed",
                        unclaimed_reason_code="AWAITING_CLAIM",
                        created_at=utc_now(),
                        created_by=actor.id,
                    )
                    await new_cred.insert()
                    existing_map[cred_key] = new_cred
                    created_count += 1
        except (
            InvalidFileFormatError,
            CsvNoRecordsError,
            NationalIdHashSecretNotConfiguredError,
        ):
            raise
        except Exception as exc:
            logger.error(f"Credential import inner error: {exc}", exc_info=True)
            raise CredentialImportFailedError() from exc

        # 6. Skip uploading file to storage
        storage_path = None

        # 7. Save file checksum on organization for duplicate check v2
        try:
            import hashlib
            pairs = [
                (get_val(row, "student_id") or "", get_val(row, "class_id") or "")
                for row in rows
            ]
            normalized_pairs = sorted(
                [f"{sid.strip().upper()}:{cc.strip().upper()}" for sid, cc in pairs]
            )
            checksum = hashlib.sha256("|".join(normalized_pairs).encode("utf-8")).hexdigest()
            organization.last_import_checksum = checksum
            await organization.save()
        except Exception:
            pass

        # 8. Return statistics
        return CredentialImportData(
            total_received=total_received,
            created_count=created_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
            storage_path=storage_path,
        )


credential_import_service = CredentialImportService()
