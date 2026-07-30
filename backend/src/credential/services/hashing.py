"""National ID (CCCD) hashing helper service."""

import hashlib
import hmac
import re

from src.config import settings


def hash_imported_national_id(raw_cccd: str | None) -> str | None:
    """Hashes raw CCCD/National ID using HMAC-SHA256 with NATIONAL_ID_HASH_SECRET.

    Normalization steps:
    1. If raw_cccd is None or empty/whitespace: returns None.
    2. Strip leading/trailing whitespace.
    3. Remove spaces (' ') and dashes ('-').
    4. Validate result is exactly 12 digits (^\d{12}$).
       If invalid, raises ValueError.
    5. Compute HMAC-SHA256 with settings.NATIONAL_ID_HASH_SECRET.
    6. Return 64 lowercase hex characters.
    """
    if raw_cccd is None:
        return None

    cleaned = str(raw_cccd).strip()
    if not cleaned:
        return None

    # Handle scientific notation e.g. "1.23457E+11" or float format "123456789012.0" from Excel
    if "e" in cleaned.lower() or "." in cleaned:
        try:
            val_float = float(cleaned)
            cleaned = str(int(val_float))
        except (ValueError, OverflowError):
            pass

    # Remove spaces, dashes, and dots
    cleaned = cleaned.replace(" ", "").replace("-", "").replace(".", "")

    # Auto-pad leading '0' if Excel stripped the leading zero from a 12-digit CCCD (making it 11 digits)
    if len(cleaned) == 11 and cleaned.isdigit():
        cleaned = cleaned.zfill(12)

    # Validate exactly 12 digits
    if not re.match(r"^\d{12}$", cleaned):
        raise ValueError(
            f"Invalid CCCD/National ID '{raw_cccd}'. National ID must contain exactly 12 digits."
        )

    secret_key = settings.NATIONAL_ID_HASH_SECRET.encode("utf-8")
    hashed = hmac.new(
        secret_key,
        cleaned.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest().lower()

    return hashed
