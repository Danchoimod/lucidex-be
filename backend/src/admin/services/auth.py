import logging

from src.admin.constants import AdminTokenPurpose
from src.admin.exceptions import (
    AdminAuthenticationStateError,
    InactiveAdminAccountError,
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

logger = logging.getLogger("lucidex.admin.auth")


class AdminAuthService:
    def __init__(self, repository: AdminRepository | None = None) -> None:
        self._repository = repository or admin_repository

    async def login(
        self,
        *,
        username: str,
        password: str,
        request_id: str | None = None,
    ) -> AdminLoginResponseData:
        admin = await self._repository.get_by_username(username)
        if not admin or not verify_password(password, admin.password_hash):
            context = {
                "auth_stage": "password",
                "failure_reason": "invalid_credentials",
            }
            if admin:
                context.update(self._actor_context(admin))
            raise InvalidAdminCredentialsError(log_context=context)
        if admin.status != "active":
            message = "Admin account is locked." if admin.status == "locked" else "Admin account is not active."
            raise InactiveAdminAccountError(
                message=message,
                log_context={
                    **self._actor_context(admin),
                    "auth_stage": "password",
                    "failure_reason": "account_locked" if admin.status == "locked" else "account_inactive",
                }
            )
        if not self._can_login(admin):
            raise InvalidAdminCredentialsError(
                log_context={
                    **self._actor_context(admin),
                    "auth_stage": "password",
                    "failure_reason": "account_not_eligible",
                }
            )

        if admin.twofa_enabled:
            if not admin.totp_secret:
                raise AdminAuthenticationStateError(
                    log_context={
                        **self._actor_context(admin),
                        "auth_stage": "password",
                        "failure_reason": "missing_totp_secret",
                    }
                )
            response = AdminLoginResponseData(
                requires_totp=True,
                challenge_token=create_admin_temp_token(
                    str(admin.id), AdminTokenPurpose.LOGIN_2FA
                )
            )
            self._log_success(
                "admin_login_challenge_issued",
                admin,
                request_id=request_id,
                auth_stage="totp_login_required",
            )
            return response

        if not admin.totp_secret:
            admin = await self._repository.set_totp_secret_if_missing(
                admin,
                generate_totp_secret(),
            )
        if not admin or not admin.totp_secret:
            raise AdminAuthenticationStateError(
                log_context={
                    **(self._actor_context(admin) if admin else {}),
                    "auth_stage": "totp_setup",
                    "failure_reason": "totp_setup_state_invalid",
                }
            )

        totp_uri = create_totp_uri(admin.totp_secret, admin.username)
        response = AdminLoginResponseData(
            requires_totp_setup=True,
            setup_token=create_admin_temp_token(
                str(admin.id), AdminTokenPurpose.TOTP_SETUP
            ),
            totp_uri=totp_uri,
            manual_entry_key=admin.totp_secret,
            qr_code=create_qr_data_url(totp_uri),
        )
        self._log_success(
            "admin_totp_setup_challenge_issued",
            admin,
            request_id=request_id,
            auth_stage="totp_setup_required",
        )
        return response

    async def verify_setup(
        self,
        *,
        setup_token: str,
        otp_code: str,
        device_info: DeviceInfo | None = None,
        request_id: str | None = None,
    ) -> AdminAccessTokenData:
        admin = await self._get_admin_from_token(
            setup_token,
            AdminTokenPurpose.TOTP_SETUP,
        )
        if admin.twofa_enabled or not admin.totp_secret:
            raise InvalidAdminTokenError(
                log_context=self._rejection_context(
                    admin, "totp_setup", "setup_state_invalid"
                )
            )
        if not verify_totp(admin.totp_secret, otp_code):
            raise InvalidAuthenticationCodeError(
                log_context=self._rejection_context(
                    admin, "totp_setup", "invalid_code"
                )
            )
        if not await self._repository.enable_twofa(admin):
            raise InvalidAdminTokenError(
                log_context=self._rejection_context(
                    admin, "totp_setup", "setup_state_changed"
                )
            )

        response = await self._create_authenticated_session(admin, device_info)
        self._log_success(
            "admin_totp_setup_verified",
            admin,
            request_id=request_id,
            auth_stage="totp_setup_verified",
        )
        return response

    async def verify_login(
        self,
        *,
        challenge_token: str,
        otp_code: str,
        device_info: DeviceInfo | None = None,
        request_id: str | None = None,
    ) -> AdminAccessTokenData:
        admin = await self._get_admin_from_token(
            challenge_token,
            AdminTokenPurpose.LOGIN_2FA,
        )
        if not admin.twofa_enabled or not admin.totp_secret:
            raise InvalidAdminTokenError(
                log_context=self._rejection_context(
                    admin, "totp_login", "login_state_invalid"
                )
            )
        if not verify_totp(admin.totp_secret, otp_code):
            raise InvalidAuthenticationCodeError(
                log_context=self._rejection_context(
                    admin, "totp_login", "invalid_code"
                ),
            )

        response = await self._create_authenticated_session(admin, device_info)
        self._log_success(
            "admin_totp_login_verified",
            admin,
            request_id=request_id,
            auth_stage="totp_login_verified",
        )
        return response

    async def _get_admin_from_token(
        self,
        token: str,
        purpose: AdminTokenPurpose,
    ) -> PlatformAdmin:
        try:
            admin_id = decode_admin_temp_token(token, purpose)
        except InvalidAdminTokenError:
            raise InvalidAdminTokenError(
                log_context={
                    "auth_stage": purpose.value,
                    "failure_reason": "invalid_or_expired_token",
                }
            ) from None
        admin = await self._repository.get_by_id(admin_id)
        if not admin:
            raise InvalidAdminTokenError(
                log_context={
                    "auth_stage": purpose.value,
                    "failure_reason": "account_not_found",
                }
            )
        if admin.status != "active":
            message = "Admin account is locked." if admin.status == "locked" else "Admin account is not active."
            raise InactiveAdminAccountError(
                message=message,
                log_context={
                    **self._actor_context(admin),
                    "auth_stage": purpose.value,
                    "failure_reason": "account_locked" if admin.status == "locked" else "account_inactive",
                }
            )
        if not self._can_login(admin):
            raise InvalidAdminTokenError(
                log_context={
                    **self._actor_context(admin),
                    "auth_stage": purpose.value,
                    "failure_reason": "account_not_eligible",
                }
            )
        return admin

    @staticmethod
    def _can_login(admin: PlatformAdmin) -> bool:
        return (
            admin.role in {"super_admin", "operations_admin"}
            and admin.twofa_method == "totp"
            and admin.status == "active"
        )

    @staticmethod
    def _actor_context(admin: PlatformAdmin) -> dict[str, str | None]:
        return {
            "actor_id": str(admin.id),
            "actor_role": admin.role,
        }

    @classmethod
    def _rejection_context(
        cls,
        admin: PlatformAdmin,
        auth_stage: str,
        failure_reason: str,
    ) -> dict[str, str | None]:
        return {
            **cls._actor_context(admin),
            "auth_stage": auth_stage,
            "failure_reason": failure_reason,
        }

    @staticmethod
    def _log_success(
        event: str,
        admin: PlatformAdmin,
        *,
        request_id: str | None,
        auth_stage: str,
    ) -> None:
        logger.info(
            event,
            extra={
                "request_id": request_id,
                "actor_type": ActorType.PLATFORM_ADMIN,
                "actor_id": str(admin.id),
                "actor_role": admin.role,
                "auth_stage": auth_stage,
            },
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

        session.twofa_verified = True
        await session.save()

        return AdminAccessTokenData(
            access_token=create_access_token(
                subject=str(admin.id),
                actor_type=ActorType.PLATFORM_ADMIN,
                session_id=str(session.id),
            ),
            refresh_token=raw_refresh_token,
            refresh_token_expires_at=session.expires_at,
        )


admin_auth_service = AdminAuthService()
