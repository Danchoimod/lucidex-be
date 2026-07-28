import time
from typing import Any

from anyio import to_thread
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2 import id_token as google_id_token

from src.oauth.exceptions import (
    OAuthConfigurationError,
    OAuthEmailNotVerifiedError,
    OAuthVerificationError,
)
from src.oauth.schemas import OAuthIdentity

GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class GoogleOAuthProvider:
    def __init__(self, client_id: str | None) -> None:
        self._client_id = client_id

    async def verify(self, credential: str) -> OAuthIdentity:
        if not self._client_id:
            raise OAuthConfigurationError()
        if not credential.strip():
            raise OAuthVerificationError()
        return await to_thread.run_sync(self._verify_sync, credential)

    def _verify_sync(self, credential: str) -> OAuthIdentity:
        try:
            claims: dict[str, Any] = google_id_token.verify_oauth2_token(
                credential,
                Request(),
            )
        except (GoogleAuthError, ValueError):
            raise OAuthVerificationError() from None

        provider_subject = claims.get("sub")
        email = claims.get("email")
        expires_at = claims.get("exp")
        if (
            claims.get("iss") not in GOOGLE_ISSUERS
            or not isinstance(expires_at, (int, float))
            or isinstance(expires_at, bool)
            or expires_at <= time.time()
            or not isinstance(provider_subject, str)
            or not provider_subject
            or not isinstance(email, str)
            or not email
        ):
            raise OAuthVerificationError()
        if claims.get("email_verified") is not True:
            raise OAuthEmailNotVerifiedError()

        try:
            return OAuthIdentity(
                provider="google",
                provider_subject=provider_subject,
                email=email.strip().lower(),
                display_name=claims.get("name"),
                avatar_url=claims.get("picture"),
            )
        except ValueError:
            raise OAuthVerificationError() from None
