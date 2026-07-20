import asyncio

from src.admin.config import AdminSettings
from src.admin.models import PlatformAdmin
from src.database import connect_database, disconnect_database

SUPERADMIN_USERNAME_ENV = "FIRST_SUPERADMIN_USERNAME"
SUPERADMIN_PASSWORD_HASH_ENV = "FIRST_SUPERADMIN_PASSWORD_HASH"
SUPPORTED_PASSWORD_HASH_PREFIXES = ("$argon2", "$2a$", "$2b$", "$2y$")


class SuperAdminSeedError(RuntimeError):
    pass


async def _count_superadmins() -> int:
    return await PlatformAdmin.find({"role": "super_admin"}).count()


async def _get_superadmin() -> PlatformAdmin | None:
    return await PlatformAdmin.find_one({"role": "super_admin"})


async def _insert_superadmin(admin: PlatformAdmin) -> PlatformAdmin:
    return await admin.insert()


def _required_value(value: str | None, name: str) -> str:
    if not value or not value.strip():
        raise SuperAdminSeedError(f"{name} is not configured.")
    return value.strip()


def _load_seed_credentials() -> tuple[str, str]:
    settings = AdminSettings()
    username = _required_value(
        settings.FIRST_SUPERADMIN_USERNAME,
        SUPERADMIN_USERNAME_ENV,
    )
    password_hash = _required_value(
        settings.FIRST_SUPERADMIN_PASSWORD_HASH,
        SUPERADMIN_PASSWORD_HASH_ENV,
    )
    if not password_hash.startswith(SUPPORTED_PASSWORD_HASH_PREFIXES):
        raise SuperAdminSeedError(
            "FIRST_SUPERADMIN_PASSWORD_HASH must be a precomputed "
            "Argon2 or bcrypt hash."
        )
    return username, password_hash


async def seed_first_superadmin() -> PlatformAdmin:
    superadmin_count = await _count_superadmins()
    if superadmin_count > 1:
        raise SuperAdminSeedError(
            "Multiple Super Admin accounts exist; manual data repair is required."
        )

    if superadmin_count == 1:
        admin = await _get_superadmin()
        if admin is None:
            raise SuperAdminSeedError(
                "Super Admin data changed while the seed was running."
            )
        return admin

    username, password_hash = _load_seed_credentials()
    admin = PlatformAdmin(
        username=username,
        password_hash=password_hash,
        role="super_admin",
        twofa_method="totp",
        twofa_enabled=False,
        totp_secret=None,
        status="active",
    )
    return await _insert_superadmin(admin)


async def _run() -> None:
    await connect_database()
    try:
        await seed_first_superadmin()
    finally:
        await disconnect_database()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
