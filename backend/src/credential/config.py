from src.config import settings


def get_national_id_hash_secret() -> str:
    secret = settings.NATIONAL_ID_HASH_SECRET
    if not secret:
        raise RuntimeError("NATIONAL_ID_HASH_SECRET is not configured")
    return secret
