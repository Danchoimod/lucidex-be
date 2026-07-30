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

    async def get_legacy_national_id_hash(
        self,
        owner_id: PydanticObjectId,
    ) -> str | None:
        document = await Owner.get_motor_collection().find_one(
            {"_id": owner_id},
            {"verified_national_id_hash": 1},
        )
        if document is None:
            return None
        value = document.get("verified_national_id_hash")
        return str(value) if value else None

    async def clear_legacy_ekyc_fields(
        self,
        owner_id: PydanticObjectId,
    ) -> bool:
        result = await Owner.get_motor_collection().update_one(
            {
                "_id": owner_id,
                "status": OwnerStatus.ACTIVE.value,
                "deleted_at": None,
            },
            {
                "$unset": {
                    "ekyc_verified": "",
                    "ekyc_verified_at": "",
                    "verified_national_id_hash": "",
                }
            },
        )
        return result.matched_count == 1


owner_repository = OwnerRepository()
