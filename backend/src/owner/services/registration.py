import re
from pymongo.errors import DuplicateKeyError

from src.otp import otp_service, OtpType, OtpError
from src.owner.constants import PASSWORD_MIN_LENGTH, PASSWORD_REGEX_PATTERN, OwnerStatus
from src.owner.exceptions import (
    PasswordMismatchError,
    WeakPasswordError,
    EmailAlreadyRegisteredError,
    PhoneAlreadyRegisteredError,
    OwnerNotFoundError,
    OwnerAlreadyActiveError,
    InvalidOtpError,
    EmailSendingFailedError,
)
from src.owner.models import Owner
from src.owner.repository import owner_repository
from src.auth.services import get_password_hash


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
        full_name: str | None = None,
        phone: str | None = None,
    ) -> Owner:
        # 1. Check if passwords match
        if password != confirm_password:
            raise PasswordMismatchError()

        # 2. Validate password strength
        self.validate_password_strength(password)

        # 3. Check duplicate email and phone across Owner and Organization
        normalized_email = email.strip().lower()
        existing_owner_email = await owner_repository.get_by_email(normalized_email)
        if existing_owner_email:
            raise EmailAlreadyRegisteredError()

        from src.organization.models import LIVE_ORGANIZATION_STATUSES, Organization
        existing_org_email = await Organization.find_one(
            Organization.contact_email == normalized_email,
            {"status": {"$in": list(LIVE_ORGANIZATION_STATUSES)}},
        )
        if existing_org_email:
            raise EmailAlreadyRegisteredError()

        if phone and phone.strip():
            normalized_phone = phone.strip()
            existing_owner_phone = await owner_repository.get_by_phone(normalized_phone)
            if existing_owner_phone:
                raise PhoneAlreadyRegisteredError()

            existing_org_phone = await Organization.find_one(
                Organization.contact_phone == normalized_phone,
                {"status": {"$in": list(LIVE_ORGANIZATION_STATUSES)}},
            )
            if existing_org_phone:
                raise PhoneAlreadyRegisteredError()

        # 4. Create and insert the Owner directly
        password_hash = get_password_hash(password)
        new_owner = Owner(
            email=email.strip().lower(),
            password_hash=password_hash,
            full_name=full_name.strip() if full_name else None,
            phone=phone.strip() if phone and phone.strip() else None,
            status=OwnerStatus.PENDING,
        )

        try:
            await owner_repository.create(new_owner)
        except DuplicateKeyError as exc:
            raise EmailAlreadyRegisteredError() from exc

        # 5. Generate email verification OTP
        otp_code = await otp_service.create_otp(
            user_id=str(new_owner.id),
            otp_type=OtpType.VERIFY_EMAIL,
        )

        # 6. Send OTP via email
        from src.mailer import mailer_service, EmailTemplate
        try:
            await mailer_service.send_otp_email(
                email=new_owner.email,
                otp_code=otp_code,
                template=EmailTemplate.OWNER_REGISTER_OTP,
            )
        except Exception as exc:
            await new_owner.delete()
            raise EmailSendingFailedError() from exc

        return new_owner

    async def verify_and_activate(self, email: str, otp_code: str) -> tuple[Owner, str, str]:
        # 1. Find the owner by email
        owner = await owner_repository.get_by_email(email)
        if not owner:
            raise OwnerNotFoundError()

        # 2. Check if already active
        if owner.status == OwnerStatus.ACTIVE:
            raise OwnerAlreadyActiveError()

        # 3. Verify OTP
        try:
            await otp_service.verify_otp(
                user_id=str(owner.id),
                otp_code=otp_code,
                otp_type=OtpType.VERIFY_EMAIL,
            )
        except OtpError as exc:
            raise InvalidOtpError(message=exc.message) from exc

        # 4. Update status to active
        owner.status = OwnerStatus.ACTIVE
        await owner.save()

        # 5. Create login session & tokens directly after activation
        from src.auth.constants import ActorType
        from src.auth.services import create_access_token, session_service

        session, refresh_token = await session_service.create_session(
            actor_id=str(owner.id),
            actor_type=ActorType.OWNER,
        )

        access_token = create_access_token(
            subject=str(owner.id),
            actor_type=ActorType.OWNER,
            session_id=str(session.id),
        )

        return owner, access_token, refresh_token


owner_registration_service = OwnerRegistrationService()
