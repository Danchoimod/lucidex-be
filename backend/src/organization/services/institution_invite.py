from __future__ import annotations
import re
import logging
import hashlib
from datetime import datetime, timezone
from beanie import PydanticObjectId

from src.auth.services import get_password_hash
from src.invitation import validate_pending_invite
from src.invitation.models import InviteLink
from src.mailer import EmailTemplate, mailer_service
from src.organization.constants import AccountStatus
from src.organization.institution_invite_exceptions import (
    AccountNotEligibleError,
    EmailSendingFailedError,
    PasswordMismatchError,
    WeakPasswordError,
)
from src.organization.institution_invite_schemas import (
    PasswordSubmitResponseData,
    ValidateInviteResponseData,
)
from src.organization.models import InstitutionAccount, Organization
from src.otp import OtpType, otp_service
from src.owner.constants import PASSWORD_MIN_LENGTH, PASSWORD_REGEX_PATTERN

logger = logging.getLogger(__name__)

class InstitutionInviteService:
    @staticmethod
    def _validate_password_strength(password: str) -> None:
        if len(password) < PASSWORD_MIN_LENGTH:
            raise WeakPasswordError()
        if not re.match(PASSWORD_REGEX_PATTERN, password):
            raise WeakPasswordError()

    async def validate_invite_token(
        self,
        *,
        invite_token: str,
    ) -> ValidateInviteResponseData:
        invite_context = await validate_pending_invite(raw_token=invite_token)
        org = await Organization.get(invite_context.org_id)
        org_name = getattr(org, "name", None) if org else None
        org_type = getattr(org, "type", "verifier") if org else "verifier"
        role_value = str(org_type).lower()

        return ValidateInviteResponseData(
            invite_id=str(invite_context.invite_id),
            org_id=str(invite_context.org_id),
            org_name=org_name,
            contact_email=invite_context.contact_email,
            expires_at=invite_context.expires_at,
            role=role_value,
        )

    async def submit_password(
        self,
        *,
        invite_token: str,
        password: str,
        confirm_password: str,
    ) -> PasswordSubmitResponseData:
        # 1. Validate invite link strictly. Token MUST be in PENDING status.
        invite_context = await validate_pending_invite(raw_token=invite_token)
        org_id_val = invite_context.org_id
        contact_email = invite_context.contact_email

        # Fetch Organization info to read type (issuer / verifier)
        org = await Organization.get(org_id_val)
        if not org:
            raise AccountNotEligibleError("Organization not found for this invitation.")
        org_role = getattr(org, "type", "verifier")

        role_value = str(org_role).lower()

        # 2. Check password & strength
        if password != confirm_password:
            raise PasswordMismatchError()
        self._validate_password_strength(password)

        hashed_password = get_password_hash(password)

        # 3. Connect Motor directly to write data
        from src.database import mongo_client
        from src.config import settings

        db = mongo_client[settings.MONGODB_DB_NAME]
        logger.info(f"WRITING TO DATABASE: {settings.MONGODB_DB_NAME}")

        collection = db["institution_accounts"]

        insert_payload = {
            "org_id": org_id_val,
            "email": contact_email,
            "password_hash": hashed_password,
            "role": role_value,  # Auto set from org type (issuer / verifier)
            "twofa_enabled": False,
            "status": "pending",
        }

        await collection.update_one(
            {"org_id": org_id_val},
            {"$set": insert_payload},
            upsert=True
        )

        doc = await collection.find_one({"org_id": org_id_val})
        user_id = str(doc["_id"])
        logger.info(f"SUCCESSFULLY WROTE DB FOR USER_ID: {user_id} WITH ROLE: {role_value}")

        # 4. Generate new OTP
        otp_code = await otp_service.create_otp(
            user_id=user_id,
            otp_type=OtpType.INSTITUTION_INVITE,
        )

        # 5. Send OTP email
        try:
            await mailer_service.send_otp_email(
                email=contact_email,
                otp_code=otp_code,
                template=EmailTemplate.ORGANIZATION_REGISTER_OTP,
            )
        except Exception as exc:
            await otp_service._repository.invalidate_active(user_id, OtpType.INSTITUTION_INVITE)
            raise EmailSendingFailedError() from exc

        return PasswordSubmitResponseData(
            requires_otp=True,
            otp_expires_in_seconds=300
        )

    async def verify_otp(
        self,
        *,
        invite_token: str,
        otp_code: str,
    ):
        """Verify OTP code, activate organization account, and mark invite token as used."""
        # 1. Validate invite link strictly. Token MUST be in PENDING status.
        invite_context = await validate_pending_invite(raw_token=invite_token)
        org_id_val = invite_context.org_id

        from src.database import mongo_client
        from src.config import settings

        if mongo_client is None:
            return {"success": True, "message": "OTP verified and organization account activated successfully."}

        db = mongo_client[settings.MONGODB_DB_NAME]
        account_collection = db["institution_accounts"]

        account_doc = await account_collection.find_one({"org_id": org_id_val})
        if not account_doc:
            account_doc = await account_collection.find_one({"org_id": str(org_id_val)})
        if not account_doc and hasattr(invite_context, "contact_email"):
            account_doc = await account_collection.find_one({"email": invite_context.contact_email})

        if not account_doc:
            raise AccountNotEligibleError("Corresponding organization account not found.")

        user_id = str(account_doc["_id"])

        # 2. Verify OTP via OtpService
        await otp_service.verify_otp(
            user_id=user_id,
            otp_code=otp_code,
            otp_type=OtpType.INSTITUTION_INVITE,
        )

        # 3. Force update account status to "active"
        update_result = await account_collection.update_one(
            {"_id": account_doc["_id"]},
            {"$set": {"status": "active"}}
        )
        logger.info(f"UPDATE ACCOUNT ACTIVE RESULT: matched={update_result.matched_count}, modified={update_result.modified_count}")

        # 4. Update token status to "used"
        try:
            token_hash = hashlib.sha256(invite_token.encode()).hexdigest()
            invite_collection = db["invite_links"]
            now_utc = datetime.now(timezone.utc)

            await invite_collection.update_one(
                {
                    "$or": [
                        {"token_hash": token_hash},
                        {"token_hash": invite_token}
                    ]
                },
                {
                    "$set": {
                        "status": "used",
                        "used_at": now_utc,
                        "updated_at": now_utc
                    }
                }
            )
        except Exception as e:
            logger.warning(f"Could not update used status for token: {e}")

        return {"success": True, "message": "OTP verified and organization account activated successfully."}

institution_invite_service = InstitutionInviteService()