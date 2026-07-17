from src.auth.constants import ActorType
from src.auth.exceptions import InactiveAccountError, InvalidCredentialsError
from src.auth.models import DeviceInfo
from src.auth.services import create_access_token, session_service, verify_password
from src.owner.constants import OwnerStatus
from src.owner.models import Owner
from src.owner.repository import owner_repository


class OwnerLoginService:
    async def login(
        self,
        email: str,
        password: str,
        device_info: DeviceInfo | None = None,
    ) -> tuple[Owner, str, str]:
        """Authenticate an owner, create a session, and generate tokens."""
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

        # 4. Create database Session
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
