from src.credential.repository import CredentialRepository, credential_repository


class EkycRepository:
    def __init__(self, credentials: CredentialRepository) -> None:
        self._credentials = credentials

    async def has_matching_credential(self, national_id_hash: str) -> bool:
        return await self._credentials.has_unclaimed_national_id_hash(national_id_hash)


ekyc_repository = EkycRepository(credential_repository)
