from beanie import PydanticObjectId
from bson.errors import InvalidId

from src.admin.models import PlatformAdmin


class AdminRepository:
    async def get_by_username(self, username: str) -> PlatformAdmin | None:
        return await PlatformAdmin.find_one(
            PlatformAdmin.username == username.strip()
        )

    async def get_by_id(self, admin_id: str) -> PlatformAdmin | None:
        try:
            object_id = PydanticObjectId(admin_id)
        except (InvalidId, TypeError):
            return None
        return await PlatformAdmin.get(object_id)

    async def set_totp_secret_if_missing(
        self,
        admin: PlatformAdmin,
        secret: str,
    ) -> PlatformAdmin | None:
        if admin.totp_secret:
            return admin

        await PlatformAdmin.find_one(
            {"_id": admin.id, "totp_secret": None}
        ).update({"$set": {"totp_secret": secret}})
        return await PlatformAdmin.get(admin.id)

    async def enable_twofa(self, admin: PlatformAdmin) -> bool:
        result = await PlatformAdmin.find_one(
            {"_id": admin.id, "twofa_enabled": False}
        ).update({"$set": {"twofa_enabled": True}})
        return result.modified_count == 1


admin_repository = AdminRepository()
