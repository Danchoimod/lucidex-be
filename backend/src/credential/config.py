from src.config import settings
from src.credential.exceptions import NationalIdHashSecretNotConfiguredError


def get_national_id_hash_secret() -> str:
    secret = settings.NATIONAL_ID_HASH_SECRET
    if not secret:
        raise NationalIdHashSecretNotConfiguredError()
    return secret
