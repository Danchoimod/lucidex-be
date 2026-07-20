from src.admin.constants import AdminTokenPurpose
from src.admin.exceptions import (
    AdminAuthenticationStateError,
    InvalidAdminCredentialsError,
    InvalidAdminTokenError,
    InvalidAuthenticationCodeError,
)
from src.admin.models import PlatformAdmin
from src.admin.repository import AdminRepository, admin_repository
from src.admin.schemas import AdminAccessTokenData, AdminLoginResponseData
from src.admin.utils import (
    create_admin_temp_token,
    create_qr_data_url,
    create_totp_uri,
    decode_admin_temp_token,
    generate_totp_secret,
    verify_totp,
)
from src.auth.constants import ActorType
from src.auth.models import DeviceInfo
from src.auth.services import create_access_token, session_service, verify_password


class AdminAuthService:
    def __init__(self, repository: AdminRepository | None = None) -> None:
        self._repository = repository or admin_repository

    async def login(
        self,
        *,
        username: str,
        password: str,
    ) -> AdminLoginResponseData:
        admin = await self._repository.get_by_username(username)
        if not admin or not verify_password(password, admin.password_hash):
            raise InvalidAdminCredentialsError()
        if not self._can_login(admin):
            raise InvalidAdminCredentialsError()

        if admin.twofa_enabled:
            if not admin.totp_secret:
                raise AdminAuthenticationStateError()
            return AdminLoginResponseData(
                requires_totp=True,
                challenge_token=create_admin_temp_token(
                    str(admin.id), AdminTokenPurpose.LOGIN_2FA
                )
            )

        if not admin.totp_secret:
            admin = await self._repository.set_totp_secret_if_missing(
                admin,
                generate_totp_secret(),
            )
        if not admin or not admin.totp_secret:
            raise AdminAuthenticationStateError()

        totp_uri = create_totp_uri(admin.totp_secret, admin.username)
        return AdminLoginResponseData(
            requires_totp_setup=True,
            setup_token=create_admin_temp_token(
                str(admin.id), AdminTokenPurpose.TOTP_SETUP
            ),
            totp_uri=totp_uri,
            manual_entry_key=admin.totp_secret,
            qr_code=create_qr_data_url(totp_uri),
        )

    async def verify_setup(
        self,
        *,
        setup_token: str,
        otp_code: str,
        device_info: DeviceInfo | None = None,
    ) -> AdminAccessTokenData:
        admin = await self._get_admin_from_token(
            setup_token,
            AdminTokenPurpose.TOTP_SETUP,
        )
        if admin.twofa_enabled or not admin.totp_secret:
            raise InvalidAdminTokenError()
        if not verify_totp(admin.totp_secret, otp_code):
            raise InvalidAuthenticationCodeError()
        if not await self._repository.enable_twofa(admin):
            raise InvalidAdminTokenError()

        return await self._create_authenticated_session(admin, device_info)

    async def verify_login(
        self,
        *,
        challenge_token: str,
        otp_code: str,
        device_info: DeviceInfo | None = None,
    ) -> AdminAccessTokenData:
        admin = await self._get_admin_from_token(
            challenge_token,
            AdminTokenPurpose.LOGIN_2FA,
        )
        if not admin.twofa_enabled or not admin.totp_secret:
            raise InvalidAdminTokenError()
        if not verify_totp(admin.totp_secret, otp_code):
            raise InvalidAuthenticationCodeError()

        return await self._create_authenticated_session(admin, device_info)

    async def _get_admin_from_token(
        self,
        token: str,
        purpose: AdminTokenPurpose,
    ) -> PlatformAdmin:
        admin_id = decode_admin_temp_token(token, purpose)
        admin = await self._repository.get_by_id(admin_id)
        if not admin or not self._can_login(admin):
            raise InvalidAdminTokenError()
        return admin

    @staticmethod
    def _can_login(admin: PlatformAdmin) -> bool:
        return (
            admin.role == "super_admin"
            and admin.twofa_method == "totp"
            and admin.status == "active"
        )

    @staticmethod
    async def _create_authenticated_session(
        admin: PlatformAdmin,
        device_info: DeviceInfo | None,
    ) -> AdminAccessTokenData:
        session, raw_refresh_token = await session_service.create_session(
            actor_id=str(admin.id),
            actor_type=ActorType.PLATFORM_ADMIN,
            device_info=device_info,
        )
        del raw_refresh_token

        session.twofa_verified = True
        await session.save()

        return AdminAccessTokenData(
            access_token=create_access_token(
                subject=str(admin.id),
                actor_type=ActorType.PLATFORM_ADMIN,
                session_id=str(session.id),
            )
        )


admin_auth_service = AdminAuthService()
