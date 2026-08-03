"""Validation utilities for credential fields."""

from datetime import date, datetime
import re

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
STUDENT_ID_REGEX = re.compile(r"^[a-zA-Z0-9]{2,15}$")
CLASS_ID_REGEX = re.compile(r"^[a-zA-Z0-9]{2,15}$")
DOB_REGEX = re.compile(r"^\d{2}/\d{2}/\d{4}$")
NATIONAL_ID_REGEX = re.compile(r"^\d{12}$")


def validate_student_id(val: str) -> str:
    val = val.strip()
    if not STUDENT_ID_REGEX.match(val):
        raise ValueError(
            f"Invalid StudentID '{val}'. Must be 2-15 alphanumeric characters without special characters."
        )
    return val


def validate_fullname(val: str) -> str:
    val = val.strip()
    if not (2 <= len(val) <= 200) or not all(c.isalpha() or c.isspace() for c in val):
        raise ValueError(
            f"Invalid Fullname '{val}'. Must be 2-200 characters without numbers or special characters."
        )
    return val


def parse_and_validate_dob(val: str) -> date:
    val = val.strip()
    if not DOB_REGEX.match(val):
        raise ValueError(
            f"Invalid Date of Birth format '{val}'. Expected format dd/mm/yyyy (e.g. 15/05/2003)."
        )
    try:
        return datetime.strptime(val, "%d/%m/%Y").date()
    except ValueError as exc:
        raise ValueError(
            f"Invalid Date of Birth '{val}'. Please provide a valid calendar date."
        ) from exc


def validate_dob_str(val: str) -> str:
    parse_and_validate_dob(val)
    return val.strip()


def validate_major(val: str, field_name: str = "Major") -> str:
    val = val.strip()
    if not (2 <= len(val) <= 200) or not all(c.isalpha() or c.isspace() for c in val):
        raise ValueError(
            f"Invalid {field_name} '{val}'. Must be 2-200 characters without numbers or special characters."
        )
    return val


def validate_graduation_year(val: int) -> int:
    if not isinstance(val, int) or val < 1970:
        raise ValueError(
            f"Invalid GraduationYear '{val}'. Must be an integer from 1970 onwards."
        )
    return val


def validate_classification(val: str, field_name: str = "Graduation Classification") -> str:
    val = val.strip()
    if not (2 <= len(val) <= 200) or not all(c.isalpha() or c.isspace() for c in val):
        raise ValueError(
            f"Invalid {field_name} '{val}'. Must be 2-200 characters without numbers or special characters."
        )
    return val


def validate_mode_of_study(val: str, field_name: str = "Mode of Study") -> str:
    val = val.strip()
    if not (2 <= len(val) <= 200) or not all(
        c.isalpha() or c.isspace() or c == "-" for c in val
    ):
        raise ValueError(
            f"Invalid {field_name} '{val}'. Must be 2-200 characters without numbers or special characters (hyphens allowed)."
        )
    return val


def validate_university_email(val: str) -> str:
    val = val.strip()
    if not EMAIL_REGEX.match(val):
        raise ValueError(
            f"Invalid UniversityEmail '{val}'. Must be a valid email format (e.g. name@example.com)."
        )
    return val


def validate_national_id(val: str) -> str:
    val = str(val).strip()
    if "e" in val.lower() or "." in val:
        try:
            val_float = float(val)
            val = str(int(val_float))
        except (ValueError, OverflowError):
            pass
    val = val.replace(" ", "").replace("-", "").replace(".", "")
    if len(val) == 11 and val.isdigit():
        val = val.zfill(12)
    if not NATIONAL_ID_REGEX.match(val):
        raise ValueError(
            f"Invalid NationalID '{val}'. National ID must contain 11 or 12 digits (11-digit numbers with missing leading zero will be auto-padded)."
        )
    return val


def validate_class_id(val: str) -> str:
    val = val.strip()
    if not CLASS_ID_REGEX.match(val):
        raise ValueError(
            f"Invalid ClassID '{val}'. Must be 2-15 alphanumeric characters without special characters."
        )
    return val
