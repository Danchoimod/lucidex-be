from src.owner.constants import OwnerStatus
from src.owner.models import Owner
from src.utils.check_format import normalize_email


class OwnerRepository:
    async def get_by_email(self, email: str) -> Owner | None:
        """Find an owner by email address."""
        normalized_email = normalize_email(email)
        return await Owner.find_one(Owner.email == normalized_email)

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


owner_repository = OwnerRepository()
