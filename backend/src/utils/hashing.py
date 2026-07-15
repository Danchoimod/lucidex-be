import hashlib


def hash_national_id(national_id: str) -> str:
    """Hash a national ID immediately so the raw value is never persisted."""
    return hashlib.sha256(national_id.encode("utf-8")).hexdigest()
