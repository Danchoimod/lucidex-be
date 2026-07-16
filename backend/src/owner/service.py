import re
from pymongo.errors import DuplicateKeyError

from src.otp import otp_service, OtpType
from src.owner.constants import PASSWORD_MIN_LENGTH, PASSWORD_REGEX_PATTERN, OwnerStatus
from src.owner.exceptions import (
    PasswordMismatchError,
    WeakPasswordError,
    EmailAlreadyRegisteredError,
)
from src.owner.models import Owner
from src.owner.repository import owner_repository
from src.security import get_password_hash



class OwnerRegistrationService:
    @staticmethod
    def validate_password_strength(password: str) -> None:
        """Validate password meets all security requirements."""
        if len(password) < PASSWORD_MIN_LENGTH:
            raise WeakPasswordError()
        
        # Regex check for 1 uppercase, 1 lowercase, 1 number, 1 special character
        if not re.match(PASSWORD_REGEX_PATTERN, password):
            raise WeakPasswordError()

    async def register(
        self,
        email: str,
        password: str,
        confirm_password: str,
    ) -> Owner:
        # 1. Check if passwords match
        if password != confirm_password:
            raise PasswordMismatchError()

        # 2. Validate password strength
        self.validate_password_strength(password)

        # 3. Check duplicate email
        existing_owner = await owner_repository.get_by_email(email)
        if existing_owner:
            raise EmailAlreadyRegisteredError()

        # 4. Create and insert the Owner directly
        password_hash = get_password_hash(password)
        new_owner = Owner(
            email=email.strip().lower(),
            password_hash=password_hash,
            status=OwnerStatus.PENDING,
        )

        try:
            await owner_repository.create(new_owner)
        except DuplicateKeyError as exc:
            raise EmailAlreadyRegisteredError() from exc

        # 5. Generate email verification OTP
        await otp_service.create_otp(
            user_id=str(new_owner.id),
            otp_type=OtpType.VERIFY_EMAIL,
        )

        return new_owner


owner_registration_service = OwnerRegistrationService()
