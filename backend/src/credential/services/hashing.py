from src.credential.config import get_national_id_hash_secret
from src.utils.hashing import hash_national_id


def hash_imported_national_id(
    national_id: str,
    *,
    secret: str | None = None,
) -> str:
    """Create the canonical hash persisted by credential import."""
    return hash_national_id(
        national_id,
        secret or get_national_id_hash_secret(),
    )
