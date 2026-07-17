from src.auth.constants import ActorType
from src.auth.exceptions import InactiveAccountError, InvalidCredentialsError
from src.auth.models import DeviceInfo
from src.auth.services import (
    create_access_token,
    create_temp_login_token,
    decode_temp_login_token,
    session_service,
    verify_password,
)
from src.owner.constants import OwnerStatus
from src.owner.models import Owner
from src.owner.repository import owner_repository
from src.otp import otp_service, OtpType
from src.mailer import mailer_service, EmailTemplate


class OwnerLoginService:
    async def login(
        self,
        email: str,
        password: str,
    ) -> str:
        """Authenticate credentials, issue an OTP via email, and return a temporary token."""
        # 1. Fetch owner
        owner = await owner_repository.get_by_email(email)
        if not owner or not owner.password_hash:
            raise InvalidCredentialsError()

        # 2. Verify password
        if not verify_password(password, owner.password_hash):
            raise InvalidCredentialsError()

        # 3. Check status
        if owner.status != OwnerStatus.ACTIVE:
            if owner.status == OwnerStatus.PENDING:
                raise InactiveAccountError("Account registration is pending OTP verification.")
            raise InactiveAccountError(f"Account is not active (status: {owner.status.value}).")

        # 4. Generate login OTP
        otp_code = await otp_service.create_otp(
            user_id=str(owner.id),
            otp_type=OtpType.LOGIN,
        )

        # 5. Send OTP via email using the REGISTER_OTP template layout temporarily
        await mailer_service.send_otp_email(
            email=owner.email,
            otp_code=otp_code,
            template=EmailTemplate.REGISTER_OTP,
        )

        # 6. Generate temporary stateless token representing pending login
        otp_token = create_temp_login_token(str(owner.id))
        return otp_token

    async def verify_otp_and_login(
        self,
        otp_token: str,
        otp_code: str,
        device_info: DeviceInfo | None = None,
    ) -> tuple[Owner, str, str]:
        """Verify the login OTP and temporary token, then create the official session."""
        # 1. Decode temporary login token to retrieve owner_id
        owner_id = decode_temp_login_token(otp_token)

        # 2. Retrieve owner
        owner = await Owner.get(owner_id)
        if not owner:
            raise InvalidCredentialsError()

        # 3. Verify OTP code against DB
        await otp_service.verify_otp(
            user_id=owner_id,
            otp_code=otp_code,
            otp_type=OtpType.LOGIN,
        )

        # 4. Create active database Session
        session, refresh_token = await session_service.create_session(
            actor_id=str(owner.id),
            actor_type=ActorType.OWNER,
            device_info=device_info,
        )

        # 5. Generate Access Token
        access_token = create_access_token(
            subject=str(owner.id),
            actor_type=ActorType.OWNER,
            session_id=str(session.id),
        )

        return owner, access_token, refresh_token


owner_login_service = OwnerLoginService()
