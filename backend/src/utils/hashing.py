import hashlib
import hmac
import re

_NATIONAL_ID_LENGTH = 12
_NATIONAL_ID_SEPARATORS = re.compile(r"[\s-]+")


def normalize_national_id(value: str) -> str:
    """Normalize a Vietnamese national ID without retaining the raw value."""
    normalized = _NATIONAL_ID_SEPARATORS.sub("", value.strip())
    if not normalized.isascii() or not normalized.isdigit():
        raise ValueError("National ID must contain only digits and separators.")
    if len(normalized) != _NATIONAL_ID_LENGTH:
        raise ValueError("National ID must contain exactly 12 digits.")
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
