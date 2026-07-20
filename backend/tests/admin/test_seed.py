from dataclasses import dataclass

import pytest

import src.admin.seed as seed_module
from src.admin.config import AdminSettings
from src.admin.seed import SuperAdminSeedError, seed_first_superadmin

VALID_PASSWORD_HASH = "$argon2id$v=19$m=65536,t=3,p=4$seed$safe-hash"


@dataclass
class FakePlatformAdmin:
    username: str
    password_hash: str
    role: str | None = "super_admin"
    twofa_method: str = "totp"
    twofa_enabled: bool = False
    totp_secret: str | None = None
    status: str = "active"


@dataclass
class FakeAdminSettings:
    FIRST_SUPERADMIN_USERNAME: str | None = None
    FIRST_SUPERADMIN_PASSWORD_HASH: str | None = None


@pytest.fixture(autouse=True)
async def otp_test_database():
    """Override the root MongoDB fixture; seed tests use an in-memory store."""
    yield


@pytest.fixture(scope="session", autouse=True)
def _drop_test_database_at_session_end():
    """Prevent the root test fixture from dropping an external database."""
    yield


@pytest.fixture
def seed_store(monkeypatch):
    admins: list[FakePlatformAdmin] = []
    insert_count = 0

    async def count_superadmins() -> int:
        return sum(admin.role == "super_admin" for admin in admins)

    async def get_superadmin() -> FakePlatformAdmin | None:
        return next(
            (admin for admin in admins if admin.role == "super_admin"),
            None,
        )

    async def insert_superadmin(
        admin: FakePlatformAdmin,
    ) -> FakePlatformAdmin:
        nonlocal insert_count
        insert_count += 1
        admins.append(admin)
        return admin

    monkeypatch.setattr(seed_module, "PlatformAdmin", FakePlatformAdmin)
    monkeypatch.setattr(seed_module, "_count_superadmins", count_superadmins)
    monkeypatch.setattr(seed_module, "_get_superadmin", get_superadmin)
    monkeypatch.setattr(seed_module, "_insert_superadmin", insert_superadmin)

    def inserts() -> int:
        return insert_count

    return admins, inserts


def configure_seed_settings(
    monkeypatch,
    *,
    username: str | None = "root-admin",
    password_hash: str | None = VALID_PASSWORD_HASH,
) -> None:
    monkeypatch.setattr(
        seed_module,
        "AdminSettings",
        lambda: FakeAdminSettings(
            FIRST_SUPERADMIN_USERNAME=username,
            FIRST_SUPERADMIN_PASSWORD_HASH=password_hash,
        ),
    )


def test_admin_settings_loads_seed_credentials_from_dotenv(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "FIRST_SUPERADMIN_USERNAME=root-admin\n"
        f"FIRST_SUPERADMIN_PASSWORD_HASH='{VALID_PASSWORD_HASH}'\n",
        encoding="utf-8",
    )

    settings = AdminSettings(_env_file=env_file)

    assert settings.FIRST_SUPERADMIN_USERNAME == "root-admin"
    assert settings.FIRST_SUPERADMIN_PASSWORD_HASH == VALID_PASSWORD_HASH


@pytest.mark.asyncio
async def test_seed_creates_first_superadmin_when_database_is_empty(
    seed_store, monkeypatch
):
    admins, inserts = seed_store
    configure_seed_settings(monkeypatch)

    admin = await seed_first_superadmin()

    assert admins == [admin]
    assert inserts() == 1
    assert admin.username == "root-admin"
    assert admin.password_hash == VALID_PASSWORD_HASH
    assert admin.role == "super_admin"
    assert admin.status == "active"
    assert admin.twofa_method == "totp"
    assert admin.twofa_enabled is False
    assert admin.totp_secret is None


@pytest.mark.asyncio
async def test_seed_does_not_overwrite_existing_superadmin_from_env(
    seed_store, monkeypatch
):
    admins, inserts = seed_store
    existing = FakePlatformAdmin(
        username="existing-admin",
        password_hash="$2b$existing-hash",
    )
    admins.append(existing)
    monkeypatch.setattr(
        seed_module,
        "_load_seed_credentials",
        lambda: pytest.fail("Seed credentials must not be read."),
    )

    result = await seed_first_superadmin()

    assert result is existing
    assert existing.username == "existing-admin"
    assert existing.password_hash == "$2b$existing-hash"
    assert inserts() == 0


@pytest.mark.asyncio
async def test_running_seed_twice_does_not_create_second_account(
    seed_store, monkeypatch
):
    admins, inserts = seed_store
    configure_seed_settings(monkeypatch)

    first = await seed_first_superadmin()
    second = await seed_first_superadmin()

    assert second is first
    assert len(admins) == 1
    assert inserts() == 1


@pytest.mark.asyncio
async def test_seed_does_not_reset_existing_totp_setup(seed_store, monkeypatch):
    admins, inserts = seed_store
    existing = FakePlatformAdmin(
        username="existing-admin",
        password_hash="$2b$existing-hash",
        twofa_enabled=True,
        totp_secret="existing-secret",
    )
    admins.append(existing)
    configure_seed_settings(monkeypatch)

    result = await seed_first_superadmin()

    assert result is existing
    assert existing.twofa_enabled is True
    assert existing.totp_secret == "existing-secret"
    assert inserts() == 0


@pytest.mark.asyncio
async def test_seed_does_not_promote_legacy_admin_without_role(
    seed_store, monkeypatch
):
    admins, inserts = seed_store
    legacy_admin = FakePlatformAdmin(
        username="legacy-admin",
        password_hash="$2b$legacy-hash",
        role=None,
    )
    admins.append(legacy_admin)
    configure_seed_settings(monkeypatch)

    seeded_admin = await seed_first_superadmin()

    assert legacy_admin.role is None
    assert seeded_admin is not legacy_admin
    assert seeded_admin.role == "super_admin"
    assert len(admins) == 2
    assert inserts() == 1


@pytest.mark.asyncio
async def test_seed_rejects_multiple_superadmins(seed_store, monkeypatch):
    admins, inserts = seed_store
    admins.extend(
        [
            FakePlatformAdmin(username="admin-one", password_hash="$2b$hash-one"),
            FakePlatformAdmin(username="admin-two", password_hash="$2b$hash-two"),
        ]
    )
    monkeypatch.setattr(
        seed_module,
        "_load_seed_credentials",
        lambda: pytest.fail("Seed credentials must not be read."),
    )

    with pytest.raises(SuperAdminSeedError, match="Multiple Super Admin"):
        await seed_first_superadmin()

    assert inserts() == 0
    assert len(admins) == 2


@pytest.mark.asyncio
async def test_seed_requires_username_when_database_is_empty(
    seed_store, monkeypatch
):
    _, inserts = seed_store
    configure_seed_settings(monkeypatch, username=None)

    with pytest.raises(
        SuperAdminSeedError,
        match="FIRST_SUPERADMIN_USERNAME is not configured",
    ):
        await seed_first_superadmin()

    assert inserts() == 0


@pytest.mark.asyncio
async def test_seed_requires_password_hash_when_database_is_empty(
    seed_store, monkeypatch
):
    _, inserts = seed_store
    configure_seed_settings(monkeypatch, password_hash=None)

    with pytest.raises(
        SuperAdminSeedError,
        match="FIRST_SUPERADMIN_PASSWORD_HASH is not configured",
    ):
        await seed_first_superadmin()

    assert inserts() == 0


@pytest.mark.asyncio
async def test_seed_cli_connects_before_seed_and_disconnects_after(monkeypatch):
    calls = []

    async def connect_database() -> None:
        calls.append("connect")

    async def seed() -> None:
        calls.append("seed")

    async def disconnect_database() -> None:
        calls.append("disconnect")

    monkeypatch.setattr(seed_module, "connect_database", connect_database)
    monkeypatch.setattr(seed_module, "seed_first_superadmin", seed)
    monkeypatch.setattr(seed_module, "disconnect_database", disconnect_database)

    await seed_module._run()

    assert calls == ["connect", "seed", "disconnect"]
