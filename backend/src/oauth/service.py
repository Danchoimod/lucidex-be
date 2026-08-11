from typing import Protocol

from src.config import settings
from src.oauth.exceptions import UnsupportedOAuthProviderError
from src.oauth.providers.google import GoogleOAuthProvider
from src.oauth.schemas import OAuthIdentity


class OAuthProvider(Protocol):
    async def verify(self, credential: str) -> OAuthIdentity: ...


class OAuthService:
    def __init__(self, providers: dict[str, OAuthProvider]) -> None:
        self._providers = providers

    async def verify(self, provider: str, credential: str) -> OAuthIdentity:
        verifier = self._providers.get(provider)
        if verifier is None:
            raise UnsupportedOAuthProviderError()
        return await verifier.verify(credential)

    async def verify_google(self, credential: str) -> OAuthIdentity:
        return await self.verify("google", credential)


oauth_service = OAuthService(
    providers={
        "google": GoogleOAuthProvider(client_id=settings.GOOGLE_CLIENT_ID),
    }
)
