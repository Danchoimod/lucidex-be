import pytest

from src.admin.models import PlatformAdmin


@pytest.fixture
def platform_admin_model(monkeypatch):
    """Allow model validation without connecting to a MongoDB collection."""
    monkeypatch.setattr(
        PlatformAdmin,
        "get_motor_collection",
        classmethod(lambda cls: None),
    )
    return PlatformAdmin


def test_platform_admin_missing_role_is_not_superadmin(platform_admin_model):
    admin = platform_admin_model.model_validate(
        {
            "username": "legacy-admin",
            "password_hash": "masked-hash",
            "twofa_method": "totp",
            "status": "active",
        }
    )

    assert admin.role is None
    assert admin.role != "super_admin"


@pytest.mark.parametrize("twofa_method", ["email", "sms"])
def test_platform_admin_parses_legacy_twofa_methods(
    platform_admin_model,
    twofa_method,
):
    admin = platform_admin_model.model_validate(
        {
            "username": "legacy-admin",
            "password_hash": "masked-hash",
            "role": None,
            "twofa_method": twofa_method,
            "status": "active",
        }
    )

    assert admin.twofa_method == twofa_method
