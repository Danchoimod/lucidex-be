import logging

from src.auth.constants import ActorType
from src.auth.exceptions import (
    AccountNotFoundError,
    GoogleAccountPasswordLoginNotAllowedError,
    InactiveAccountError,
    InvalidCredentialsError,
    InvalidOtpError,
)
from src.auth.models import DeviceInfo
from src.auth.services import (
    create_access_token,
    create_temp_login_token,
    decode_temp_login_token,
    session_service,
    verify_password,
)
from src.mailer import EmailTemplate, mailer_service
from src.organization.constants import AccountStatus
from src.organization.models import InstitutionAccount, Organization
from src.otp import OtpCodeMismatchError, OtpError, OtpExpiredError, OtpType, otp_service
from src.owner.constants import OwnerStatus
from src.owner.models import Owner
from src.owner.repository import owner_repository


class LoginService:
    async def login(
        self,
        email: str,
        password: str,
    ) -> str:
        """Authenticate credentials for either Owner or InstitutionAccount, issue OTP, and return temp token."""
        # 1. Fetch user (check Owner first, then InstitutionAccount)
        owner = await owner_repository.get_by_email(email)
        institution_account = None
        if not owner:
            institution_account = await InstitutionAccount.find_one({"email": email})

        if not owner and not institution_account:
            raise AccountNotFoundError()

        if owner and owner.oauth_provider == "google":
            raise GoogleAccountPasswordLoginNotAllowedError()

        # 2. Verify password
        password_hash = owner.password_hash if owner else institution_account.password_hash
        if not password_hash or not verify_password(password, password_hash):
            raise InvalidCredentialsError()

        # 3. Check status and generate/send OTP
        if owner:
            if owner.status != OwnerStatus.ACTIVE:
                if owner.status == OwnerStatus.PENDING:
                    raise InactiveAccountError("Account registration is pending OTP verification.")
                raise InactiveAccountError(f"Account is not active (status: {owner.status.value}).")

            # Generate login OTP
            otp_code = await otp_service.create_otp(
                user_id=str(owner.id),
                otp_type=OtpType.LOGIN,
            )

            # Send OTP via email using OWNER_LOGIN_OTP
            await mailer_service.send_otp_email(
                email=owner.email,
                otp_code=otp_code,
                template=EmailTemplate.OWNER_LOGIN_OTP,
            )

            # Generate temporary stateless token representing pending login
            otp_token = create_temp_login_token(str(owner.id))
            return otp_token
        else:
            if institution_account.status != AccountStatus.ACTIVE:
                raise InactiveAccountError(f"Account is not active (status: {institution_account.status.value}).")

            # Get organization contact email
            org = await Organization.get(institution_account.org_id)
            if not org or not org.contact_email:
                raise InactiveAccountError("Associated organization or contact email not found.")

            # Generate login OTP
            otp_code = await otp_service.create_otp(
                user_id=str(institution_account.id),
                otp_type=OtpType.LOGIN,
            )

            # Send OTP via organization contact email using ORGANIZATION_LOGIN_OTP
            await mailer_service.send_otp_email(
                email=org.contact_email,
                otp_code=otp_code,
                template=EmailTemplate.ORGANIZATION_LOGIN_OTP,
            )

            # Generate temporary stateless token representing pending login
            otp_token = create_temp_login_token(str(institution_account.id))
            return otp_token

    async def verify_otp_and_login(
        self,
        otp_token: str,
        otp_code: str,
        device_info: DeviceInfo | None = None,
    ) -> tuple[Owner | InstitutionAccount, str, str]:
        """Verify the login OTP and temporary token, then create the official session."""
        # 1. Decode temporary login token to retrieve user_id
        user_id = decode_temp_login_token(otp_token)

        # 2. Retrieve user
        owner = await Owner.get(user_id)
        institution_account = None
        if not owner:
            institution_account = await InstitutionAccount.get(user_id)

        if not owner and not institution_account:
            raise InvalidCredentialsError()

        # 3. Verify OTP code against DB
        try:
            await otp_service.verify_otp(
                user_id=user_id,
                otp_code=otp_code,
                otp_type=OtpType.LOGIN,
            )
        except OtpCodeMismatchError:
            raise InvalidOtpError("Invalid OTP code.")
        except OtpExpiredError:
            raise InvalidOtpError("OTP code has expired.")
        except OtpError as exc:
            raise InvalidOtpError(message=exc.message)

        # 4. Create active session and generate Access Token
        if owner:
            session, refresh_token = await session_service.create_session(
                actor_id=str(owner.id),
                actor_type=ActorType.OWNER,
                device_info=device_info,
            )

            access_token = create_access_token(
                subject=str(owner.id),
                actor_type=ActorType.OWNER,
                session_id=str(session.id),
            )
            return owner, access_token, refresh_token
        else:
            session, refresh_token = await session_service.create_session(
                actor_id=str(institution_account.id),
                actor_type=ActorType.INSTITUTION_ACCOUNT,
                org_id=str(institution_account.org_id),
                device_info=device_info,
            )

            access_token = create_access_token(
                subject=str(institution_account.id),
                actor_type=ActorType.INSTITUTION_ACCOUNT,
                session_id=str(session.id),
                org_id=str(institution_account.org_id),
            )
            return institution_account, access_token, refresh_token


login_service = LoginService()
