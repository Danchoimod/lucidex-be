import logging

from src.admin.models import PlatformAdmin
from src.auth.models import Session
from src.auth.schemas import MeResponseData
from src.organization.models import InstitutionAccount, Organization
from src.owner.models import Owner

logger = logging.getLogger(__name__)


class MeService:
    async def get_me(
        self,
        actor_info: tuple[PlatformAdmin | Owner | InstitutionAccount, Session, str],
    ) -> MeResponseData:
        """Constructs MeResponseData profile for PlatformAdmin, Owner, or InstitutionAccount."""
        user, session, actor_type = actor_info

        if actor_type == "platform_admin":
            admin: PlatformAdmin = user
            return MeResponseData(
                actor_type="platform_admin",
                actor_id=str(admin.id),
                username=admin.username,
                role=admin.role,
                status=admin.status,
                twofa_enabled=admin.twofa_enabled,
                totp_reset_requested=admin.totp_reset_requested,
                totp_reset_requested_at=admin.totp_reset_requested_at,
                password_reset_requested=admin.password_reset_requested,
                password_reset_requested_at=admin.password_reset_requested_at,
                details={
                    "twofa_method": admin.twofa_method,
                },
            )
        elif actor_type == "owner":
            owner: Owner = user
            status_val = (
                owner.status.value
                if hasattr(owner.status, "value")
                else str(owner.status)
            )
            return MeResponseData(
                actor_type="owner",
                actor_id=str(owner.id),
                email=str(owner.email),
                full_name=owner.full_name,
                status=status_val,
                details={
                    "phone": owner.phone,
                    "avatar_url": owner.avatar_url,
                    "dob": str(owner.dob) if owner.dob else None,
                    "oauth_provider": owner.oauth_provider,
                },
            )
        else:
            account: InstitutionAccount = user
            role_val = (
                account.role.value
                if hasattr(account.role, "value")
                else str(account.role)
            )
            status_val = (
                account.status.value
                if hasattr(account.status, "value")
                else str(account.status)
            )

            org_name = None
            org_type = None
            org_status = None
            if account.org_id:
                org = await Organization.get(account.org_id)
                if org:
                    org_name = org.name
                    org_type = (
                        org.type.value
                        if hasattr(org.type, "value")
                        else str(org.type)
                    )
                    org_status = (
                        org.status.value
                        if hasattr(org.status, "value")
                        else str(org.status)
                    )

            return MeResponseData(
                actor_type="institution_account",
                actor_id=str(account.id),
                email=str(account.email),
                org_id=str(account.org_id) if account.org_id else None,
                organization_name=org_name,
                role=role_val,
                status=status_val,
                twofa_enabled=account.twofa_enabled,
                details={
                    "organization_type": org_type,
                    "organization_status": org_status,
                    "twofa_method": account.twofa_method,
                },
            )


me_service = MeService()
