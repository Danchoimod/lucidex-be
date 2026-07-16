from src.owner.models import Owner


class OwnerRepository:
    async def get_by_email(self, email: str) -> Owner | None:
        """Find an owner by email address."""
        normalized_email = email.strip().lower()
        return await Owner.find_one(Owner.email == normalized_email)

    async def create(self, owner: Owner) -> Owner:
        """Insert a new owner into the database."""
        return await owner.insert()


owner_repository = OwnerRepository()
