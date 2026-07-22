import logging

from src.auth.exceptions import AccountNotFoundError, InactiveAccountError
from src.mailer import EmailTemplate, mailer_service
from src.organization.constants import AccountStatus
from src.organization.models import InstitutionAccount, Organization
from src.otp import OtpType, otp_service
from src.owner.constants import OwnerStatus
from src.owner.repository import owner_repository

logger = logging.getLogger(__name__)


class ResendOtpService:
    async def resend_otp(self, email: str) -> None:
        """Resend OTP for either Owner or InstitutionAccount.

        - If account is pending: send VERIFY_EMAIL / INSTITUTION_INVITE OTP.
        - If account is active: send LOGIN OTP.
        - Invalidates any previous OTP for the user and type.
        """
        email_clean = email.strip().lower()
        owner = await owner_repository.get_by_email(email_clean)
        institution_account = None
        if not owner:
            institution_account = await InstitutionAccount.find_one({"email": email_clean})

        if not owner and not institution_account:
            raise AccountNotFoundError()

        if owner:
            print(f"👉 [RESEND-OTP] Step 1: Found Owner for email '{email_clean}'. Status: '{owner.status}' (type: {type(owner.status)})")
            logger.info(f"[RESEND-OTP] Found Owner account. Email: {email_clean}, Status: {owner.status}")

            if owner.status == OwnerStatus.PENDING:
                otp_type = OtpType.VERIFY_EMAIL
                email_template = EmailTemplate.OWNER_REGISTER_OTP
                send_email = owner.email
            elif owner.status == OwnerStatus.ACTIVE:
                otp_type = OtpType.LOGIN
                email_template = EmailTemplate.OWNER_LOGIN_OTP
                send_email = owner.email
            else:
                raise InactiveAccountError(f"Account status '{owner.status.value}' cannot resend OTP.")

            print(f"👉 [RESEND-OTP] Step 2: Creating OTP with type='{otp_type}' for Owner ID='{owner.id}'")
            otp_code = await otp_service.create_otp(
                user_id=str(owner.id),
                otp_type=otp_type,
            )
            await mailer_service.send_otp_email(
                email=send_email,
                otp_code=otp_code,
                template=email_template,
            )
        else:
            # InstitutionAccount
            print(f"👉 [RESEND-OTP] Step 1: Found InstitutionAccount for email '{email_clean}'. ID: '{institution_account.id}', Status: '{institution_account.status}' (type: {type(institution_account.status)})")
            logger.info(f"[RESEND-OTP] Found InstitutionAccount. Email: {email_clean}, Account ID: {institution_account.id}, Status: {institution_account.status}")

            if institution_account.status != AccountStatus.ACTIVE:
                print(f"👉 [RESEND-OTP] Status is NOT ACTIVE (Current status: '{institution_account.status}'). Selected OtpType: INSTITUTION_INVITE")
                otp_type = OtpType.INSTITUTION_INVITE
                email_template = EmailTemplate.ORGANIZATION_REGISTER_OTP
            else:
                print(f"👉 [RESEND-OTP] Status IS ACTIVE. Selected OtpType: LOGIN")
                otp_type = OtpType.LOGIN
                email_template = EmailTemplate.ORGANIZATION_LOGIN_OTP

            org = await Organization.get(institution_account.org_id)
            contact_email = org.contact_email if (org and org.contact_email) else institution_account.email
            print(f"👉 [RESEND-OTP] Step 2: Target Email: '{contact_email}'. Creating OTP with type='{otp_type}' for InstitutionAccount ID='{institution_account.id}'")

            otp_code = await otp_service.create_otp(
                user_id=str(institution_account.id),
                otp_type=otp_type,
            )
            await mailer_service.send_otp_email(
                email=contact_email,
                otp_code=otp_code,
                template=email_template,
            )


resend_otp_service = ResendOtpService()
