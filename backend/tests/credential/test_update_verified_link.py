from datetime import UTC, date, datetime, timedelta

import pytest
from beanie import PydanticObjectId
from httpx import ASGITransport, AsyncClient

from src.auth.dependencies import require_current_actor
from src.credential.models import Credential
from src.credential.schemas import CreateVerifiedLinkRequest, UpdateVerifiedLinkRequest
from src.credential.services import verified_link as verified_link_service
from src.main import app
from src.owner.models import Owner

OWNER_ID = PydanticObjectId("507f1f77bcf86cd799439011")
ISSUER_ORG_ID = PydanticObjectId("507f1f77bcf86cd799439013")


def mock_auth_dependency(actor_obj, actor_type: str):
    async def override():
        class MockSession:
            id = PydanticObjectId()
        return actor_obj, MockSession(), actor_type
    return override


@pytest.mark.asyncio
async def test_update_verified_link_settings():
    owner = Owner(id=OWNER_ID, email="owner_update_link@example.com", status="active")
    await owner.insert()

    credential = Credential(
        id=PydanticObjectId(),
        issuer_org_id=ISSUER_ORG_ID,
        student_id="STD_UP",
        full_name="Update Test",
        dob=date(2000, 1, 1),
        graduation_year=2022,
        university_email="up@univ.edu.vn",
        status="claimed",
        owner_id=OWNER_ID,
    )
    await credential.insert()

    # 1. Create link with no restrictions
    link, _ = await verified_link_service.create_verified_link(
        OWNER_ID, CreateVerifiedLinkRequest(credential_id=str(credential.id))
    )
    assert link.consent_mode is None
    assert link.max_access_count is None

    # 2. Update link settings via service to set max_access_count = 10
    updated_link = await verified_link_service.update_verified_link(
        OWNER_ID,
        str(link.id),
        UpdateVerifiedLinkRequest(max_access_count=10),
    )
    assert updated_link.max_access_count == 10
    assert updated_link.remaining_access_count == 10
    assert updated_link.consent_mode == "access_count"

    # 3. Update link via HTTP PATCH endpoint
    app.dependency_overrides[require_current_actor] = mock_auth_dependency(owner, "owner")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        future_exp = (datetime.now(UTC) + timedelta(hours=48)).isoformat()
        res = await ac.patch(
            f"/api/v1/owner/verified-links/{link.id}",
            json={
                "expires_at": future_exp,
                "max_access_count": 5,
            },
        )
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["data"]["consent_mode"] == "custom"
        assert body["data"]["max_access_count"] == 5

    app.dependency_overrides.clear()
