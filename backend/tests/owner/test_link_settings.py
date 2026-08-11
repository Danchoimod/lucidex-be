import pytest
from beanie import PydanticObjectId
from httpx import ASGITransport, AsyncClient

from src.auth.dependencies import require_current_actor
from src.main import app
from src.owner.models import Owner


def mock_auth_dependency(actor_obj, actor_type: str):
    async def override():
        class MockSession:
            id = PydanticObjectId()
        return actor_obj, MockSession(), actor_type
    return override


@pytest.mark.asyncio
async def test_get_link_settings_default_nulls():
    owner = Owner(id=PydanticObjectId(), email="owner_settings@example.com", status="active")
    await owner.insert()

    app.dependency_overrides[require_current_actor] = mock_auth_dependency(owner, "owner")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/owner/link-settings")
        assert response.status_code == 200
        res_json = response.json()
        assert res_json["success"] is True
        data = res_json["data"]
        assert data["default_consent_mode"] is None
        assert data["default_max_access_count"] is None
        assert data["default_expiry_hours"] is None
        assert data["default_allowed_org_ids"] == []

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_patch_link_settings_access_count():
    owner = Owner(id=PydanticObjectId(), email="owner_patch@example.com", status="active")
    await owner.insert()

    app.dependency_overrides[require_current_actor] = mock_auth_dependency(owner, "owner")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "default_consent_mode": "access_count",
            "default_max_access_count": 5,
        }
        response = await client.patch("/api/v1/owner/link-settings", json=payload)
        assert response.status_code == 200
        res_json = response.json()
        assert res_json["success"] is True
        data = res_json["data"]
        assert data["default_consent_mode"] == "access_count"
        assert data["default_max_access_count"] == 5

        # Verify GET returns updated settings
        get_res = await client.get("/api/v1/owner/link-settings")
        assert get_res.json()["data"]["default_max_access_count"] == 5

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_patch_link_settings_custom_mode_validation_fail():
    owner = Owner(id=PydanticObjectId(), email="owner_fail@example.com", status="active")
    await owner.insert()

    app.dependency_overrides[require_current_actor] = mock_auth_dependency(owner, "owner")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "default_consent_mode": "custom",
            "default_max_access_count": 5,
        }
        response = await client.patch("/api/v1/owner/link-settings", json=payload)
        assert response.status_code == 422
        res_json = response.json()
        assert res_json["error_code"] == "INVALID_DEFAULT_SETTINGS"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_patch_link_settings_custom_mode_success():
    owner = Owner(id=PydanticObjectId(), email="owner_success@example.com", status="active")
    await owner.insert()

    app.dependency_overrides[require_current_actor] = mock_auth_dependency(owner, "owner")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "default_consent_mode": "custom",
            "default_max_access_count": 5,
            "default_expiry_hours": 24,
        }
        response = await client.patch("/api/v1/owner/link-settings", json=payload)
        assert response.status_code == 200
        res_json = response.json()
        assert res_json["success"] is True
        data = res_json["data"]
        assert data["default_consent_mode"] == "custom"
        assert data["default_max_access_count"] == 5
        assert data["default_expiry_hours"] == 24

    app.dependency_overrides.clear()
