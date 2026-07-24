import logging
from collections.abc import Callable

from pymongo.errors import DuplicateKeyError

from src.auth.constants import ActorType
from src.auth.exceptions import InactiveAccountError
from src.auth.models import DeviceInfo
from src.auth.services.session import SessionService, session_service
from src.auth.services.token import create_access_token
from src.oauth import OAuthIdentity, OAuthService, oauth_service
from src.oauth.exceptions import (
    OAuthConfigurationError,
    OAuthEmailNotVerifiedError,
    OAuthVerificationError,
    UnsupportedOAuthProviderError,
)
from src.owner.constants import OwnerStatus
from src.owner.exceptions import (
    GoogleAccountMismatchError,
    GoogleEmailNotVerifiedError,
    GoogleOAuthUnavailableError,
    InvalidGoogleTokenError,
    PasswordAccountOAuthLoginError,
)
from src.owner.models import Owner
from src.owner.repository import OwnerRepository, owner_repository

logger = logging.getLogger("lucidex.owner.oauth")


class OwnerOAuthAuthService:
    def __init__(
        self,
        *,
        repository: OwnerRepository = owner_repository,
        oauth: OAuthService = oauth_service,
        sessions: SessionService = session_service,
    ) -> None:
        self._repository = repository
        self._oauth = oauth
        self._sessions = sessions

    async def login_with_google(
        self,
        credential: str,
        device_info: DeviceInfo | None = None,
        request_id: str | None = None,
        on_owner_created: Callable[[Owner], None] | None = None,
    ) -> tuple[Owner, str, str]:
        identity = await self._verify_google(credential)
        owner = await self._repository.get_by_email(str(identity.email))
        created = False
        if owner is None:
            owner, created = await self._create_google_owner(identity)

        self._validate_google_owner(owner, identity)
        if owner.status != OwnerStatus.ACTIVE:
            raise InactiveAccountError()

        session, refresh_token = await self._sessions.create_session(
            actor_id=str(owner.id),
            actor_type=ActorType.OWNER,
            device_info=device_info,
        )
        access_token = create_access_token(
            subject=str(owner.id),
            actor_type=ActorType.OWNER,
            session_id=str(session.id),
        )
        if created and on_owner_created is not None:
            on_owner_created(owner)
        logger.info(
            "owner_google_signup_succeeded"
            if created
            else "owner_google_login_succeeded",
            extra={
                "request_id": request_id,
                "actor_id": str(owner.id),
                "actor_type": ActorType.OWNER,
                "auth_stage": "google_signup" if created else "google_login",
            },
        )
        return owner, access_token, refresh_token

    async def _verify_google(self, credential: str) -> OAuthIdentity:
        try:
            return await self._oauth.verify_google(credential)
        except OAuthConfigurationError:
            raise GoogleOAuthUnavailableError() from None
        except OAuthEmailNotVerifiedError:
            raise GoogleEmailNotVerifiedError() from None
        except (OAuthVerificationError, UnsupportedOAuthProviderError):
            raise InvalidGoogleTokenError() from None

    async def _create_google_owner(
        self,
        identity: OAuthIdentity,
    ) -> tuple[Owner, bool]:
        owner_by_identity = await self._repository.get_by_oauth_identity(
            "google",
            identity.provider_subject,
        )
        if owner_by_identity is not None:
            return owner_by_identity, False

        try:
            owner = await self._repository.create_google_owner(
                email=str(identity.email),
                provider_subject=identity.provider_subject,
                full_name=identity.display_name,
                avatar_url=identity.avatar_url,
            )
            return owner, True
        except DuplicateKeyError:
            owner_by_email = await self._repository.get_by_email(str(identity.email))
            owner_by_identity = await self._repository.get_by_oauth_identity(
                "google",
                identity.provider_subject,
            )
            if (
                owner_by_email is None
                or owner_by_identity is None
                or str(owner_by_email.id) != str(owner_by_identity.id)
            ):
                raise GoogleAccountMismatchError() from None
            return owner_by_email, False

    @staticmethod
    def _validate_google_owner(
        owner: Owner,
        identity: OAuthIdentity,
    ) -> None:
        if str(owner.email).strip().lower() != str(identity.email):
            raise GoogleAccountMismatchError()
        if owner.password_hash and owner.oauth_provider in {None, "password"}:
            raise PasswordAccountOAuthLoginError()
        if (
            identity.provider != "google"
            or owner.oauth_provider != "google"
            or owner.oauth_subject_id != identity.provider_subject
        ):
            raise GoogleAccountMismatchError()


owner_oauth_auth_service = OwnerOAuthAuthService()
