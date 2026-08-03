import hashlib
import hmac
import re

_NATIONAL_ID_LENGTH = 12
_NATIONAL_ID_SEPARATORS = re.compile(r"[\s-]+")


def normalize_national_id(value: str) -> str:
    """Normalize a Vietnamese national ID without retaining the raw value."""
    normalized = _NATIONAL_ID_SEPARATORS.sub("", value.strip())

    # Handle float / scientific notation from Excel e.g. "79203001234.0" or "7.9203E+10"
    if "e" in normalized.lower() or "." in normalized:
        try:
            val_float = float(normalized)
            normalized = str(int(val_float))
        except (ValueError, OverflowError):
            pass

    if not normalized.isascii() or not normalized.isdigit():
        raise ValueError("National ID must contain only digits and separators.")

    # Auto-pad leading '0' if Excel stripped the leading zero from a 12-digit National ID (making it 11 digits)
    if len(normalized) == 11:
        normalized = normalized.zfill(12)

    if len(normalized) != _NATIONAL_ID_LENGTH:
        raise ValueError("National ID must contain 11 or 12 digits.")
    return normalized


def hash_national_id(value: str, secret: str) -> str:
    """Return the approved HMAC-SHA256 digest for a national ID."""
    if not secret:
        raise ValueError("National ID hash secret must not be empty.")
    normalized = normalize_national_id(value)
    return hmac.new(
        secret.encode("utf-8"),
        normalized.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
