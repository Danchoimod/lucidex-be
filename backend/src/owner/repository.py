from datetime import datetime

from beanie import PydanticObjectId

from src.owner.constants import OwnerStatus
from src.owner.models import Owner
from src.utils.check_format import normalize_email


class OwnerRepository:
    async def get_by_email(self, email: str) -> Owner | None:
        """Find an owner by email address."""
        normalized = normalize_email(email)
        raw = email.strip().lower()
        if normalized != raw:
            return await Owner.find_one({"email": {"$in": [normalized, raw]}})
        return await Owner.find_one(Owner.email == normalized)

    async def get_by_oauth_identity(
        self,
        provider: str,
        provider_subject: str,
    ) -> Owner | None:
        return await Owner.find_one(
            Owner.oauth_provider == provider,
            Owner.oauth_subject_id == provider_subject,
        )

    async def get_by_phone(self, phone: str) -> Owner | None:
        """Find an owner by phone number."""
        normalized_phone = phone.strip()
        return await Owner.find_one(Owner.phone == normalized_phone)

    async def create(self, owner: Owner) -> Owner:
        """Insert a new owner into the database."""
        return await owner.insert()

    async def create_google_owner(
        self,
        *,
        email: str,
        provider_subject: str,
        full_name: str | None = None,
        avatar_url: str | None = None,
    ) -> Owner:
        owner = Owner(
            email=email.strip().lower(),
            password_hash=None,
            oauth_provider="google",
            oauth_subject_id=provider_subject,
            full_name=full_name,
            avatar_url=avatar_url,
            status=OwnerStatus.ACTIVE,
        )
        return await self.create(owner)

    async def mark_ekyc_verified(
        self,
        *,
        owner_id: PydanticObjectId,
        national_id_hash: str,
        verified_at: datetime,
    ) -> Owner | None:
        result = await Owner.find_one(
            {
                "_id": owner_id,
                "status": OwnerStatus.ACTIVE.value,
                "deleted_at": None,
                "$or": [
                    {"verified_national_id_hash": None},
                    {"verified_national_id_hash": national_id_hash},
                ],
            }
        ).update(
            {
                "$set": {
                    "ekyc_verified": True,
                    "verified_national_id_hash": national_id_hash,
                    "ekyc_verified_at": verified_at,
                }
            }
        )
        if result.matched_count != 1:
            return None
        return await Owner.get(owner_id)


owner_repository = OwnerRepository()
