import io
from datetime import UTC, date, datetime, timedelta

import pytest
from beanie import PydanticObjectId
from httpx import ASGITransport, AsyncClient

from src.auth.dependencies import require_current_actor
from src.credential.models import Credential, VerifiedLinkAccessLog
from src.credential.schemas import CreateVerifiedLinkRequest
from src.credential.services import verified_link as verified_link_service
from src.main import app
from src.organization.models import InstitutionAccount, Organization
from src.owner.models import Owner

OWNER_ID = PydanticObjectId("507f1f77bcf86cd799439011")
ISSUER_ORG_ID = PydanticObjectId("507f1f77bcf86cd799439013")
VERIFIER_ORG_ID = PydanticObjectId("507f1f77bcf86cd799439014")
OTHER_VERIFIER_ORG_ID = PydanticObjectId("507f1f77bcf86cd799439015")
VERIFIER_ACCOUNT_ID = PydanticObjectId("507f1f77bcf86cd799439016")


def mock_auth_dependency(actor_obj, actor_type: str):
    async def override():
        class MockSession:
            id = PydanticObjectId()

        return actor_obj, MockSession(), actor_type

    return override


@pytest.mark.asyncio
async def test_bulk_verify_mixed_batch():
    """Test bulk verification with active, expired, revoked, and not_found codes."""
    owner = Owner(id=OWNER_ID, email="owner_bulk@example.com", status="active")
    await owner.insert()

    credential = Credential(
        id=PydanticObjectId(),
        issuer_org_id=ISSUER_ORG_ID,
        student_id="STD_BULK_1",
        full_name="Nguyễn Văn Bulk",
        dob=date(2000, 1, 1),
        graduation_year=2022,
        university_email="student_bulk@univ.edu.vn",
        status="claimed",
        owner_id=OWNER_ID,
    )
    await credential.insert()

    verifier_account = InstitutionAccount(
        id=VERIFIER_ACCOUNT_ID,
        org_id=VERIFIER_ORG_ID,
        email="verifier_bulk@org.com",
        password_hash="hashed",
        org_type="verifier",
        status="active",
    )
    await verifier_account.insert()

    # 1. Active link
    _, code_active = await verified_link_service.create_verified_link(
        owner_id=OWNER_ID,
        payload=CreateVerifiedLinkRequest(
            credential_id=str(credential.id),
            max_access_count=5,
        ),
    )

    # 2. Expired link
    link_expired_doc, code_expired = await verified_link_service.create_verified_link(
        owner_id=OWNER_ID,
        payload=CreateVerifiedLinkRequest(
            credential_id=str(credential.id),
        ),
    )
    link_expired_doc.expires_at = datetime.now(UTC) - timedelta(days=1)
    await link_expired_doc.save()

    # 3. Revoked link
    link_revoked_doc, code_revoked = await verified_link_service.create_verified_link(
        owner_id=OWNER_ID,
        payload=CreateVerifiedLinkRequest(
            credential_id=str(credential.id),
        ),
    )
    await verified_link_service.revoke_verified_link(
        owner_id=OWNER_ID,
        link_id=str(link_revoked_doc.id),
    )

    # 4. Not found code
    code_not_found = "INVALID-CODE-999"

    # Prepare CSV content with blank lines to test skipping
    csv_content = f"{code_active}\n\n  \n{code_expired}\n{code_revoked}\n{code_not_found}\n"

    app.dependency_overrides[require_current_actor] = mock_auth_dependency(
        verifier_account, "institution_account"
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        files = {"file": ("codes.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
        response = await client.post("/api/v1/verifier/verified-links/bulk-verify", files=files)

    app.dependency_overrides.clear()

    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    data = res_json["data"]

    assert data["total"] == 4
    assert data["summary"] == {
        "active": 1,
        "expired": 1,
        "revoked": 1,
        "not_found": 1,
    }
    assert len(data["results"]) == 4

    # Check Active row
    r1 = data["results"][0]
    assert r1["row_number"] == 1
    assert r1["code"] == code_active
    assert r1["status"] == "active"
    assert r1["is_restricted"] is False
    assert r1["credential_id"] == str(credential.id)
    assert r1["owner_name"] == "Nguyễn Văn Bulk"

    # Check Expired row
    r2 = data["results"][1]
    assert r2["row_number"] == 2
    assert r2["code"] == code_expired
    assert r2["status"] == "expired"
    assert r2["credential_id"] is None

    # Check Revoked row
    r3 = data["results"][2]
    assert r3["row_number"] == 3
    assert r3["code"] == code_revoked
    assert r3["status"] == "revoked"

    # Check Not Found row
    r4 = data["results"][3]
    assert r4["row_number"] == 4
    assert r4["code"] == code_not_found
    assert r4["status"] == "not_found"

    # Access log check: exactly 1 log written for active code
    logs = await VerifiedLinkAccessLog.find_all().to_list()
    assert len(logs) == 1


@pytest.mark.asyncio
async def test_bulk_verify_trusted_organizations_restriction():
    """Test is_restricted flag when Trusted Organizations is ON vs OFF."""
    owner = Owner(id=OWNER_ID, email="owner_restr@example.com", status="active")
    await owner.insert()

    # Create Organization records so validation passes
    other_org = Organization(
        id=OTHER_VERIFIER_ORG_ID,
        name="Other Verifier Org",
        type="verifier",
        status="approved",
        tax_code="1234567890",
        address="123 Street",
        legal_rep_name="Rep Name",
        contact_email="other_org@example.com",
        contact_phone="0123456789",
        registrant_name="Registrant Name",
    )
    await other_org.insert()

    credential = Credential(
        id=PydanticObjectId(),
        issuer_org_id=ISSUER_ORG_ID,
        student_id="STD_BULK_2",
        full_name="Nguyễn Văn Restricted",
        dob=date(2000, 1, 1),
        graduation_year=2022,
        university_email="student_restr@univ.edu.vn",
        status="claimed",
        owner_id=OWNER_ID,
    )
    await credential.insert()

    verifier_account = InstitutionAccount(
        id=VERIFIER_ACCOUNT_ID,
        org_id=VERIFIER_ORG_ID,
        email="verifier_restr@org.com",
        password_hash="hashed",
        org_type="verifier",
        status="active",
    )
    await verifier_account.insert()

    # Trusted Orgs ON: restricted to OTHER_VERIFIER_ORG_ID only
    _, code_restricted = await verified_link_service.create_verified_link(
        owner_id=OWNER_ID,
        payload=CreateVerifiedLinkRequest(
            credential_id=str(credential.id),
            allowed_org_ids=[str(OTHER_VERIFIER_ORG_ID)],
            max_access_count=10,
        ),
    )

    csv_content = f"{code_restricted}\n"

    app.dependency_overrides[require_current_actor] = mock_auth_dependency(
        verifier_account, "institution_account"
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        files = {"file": ("codes.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
        response = await client.post("/api/v1/verifier/verified-links/bulk-verify", files=files)

    app.dependency_overrides.clear()

    assert response.status_code == 200
    res_json = response.json()
    data = res_json["data"]

    assert data["total"] == 1
    assert data["summary"]["active"] == 1

    r = data["results"][0]
    assert r["code"] == code_restricted
    assert r["status"] == "active"
    assert r["is_restricted"] is True
    assert r["credential_id"] is None
    assert r["owner_name"] is None

    # No access log entry should be written for restricted code
    logs = await VerifiedLinkAccessLog.find_all().to_list()
    assert len(logs) == 0


@pytest.mark.asyncio
async def test_bulk_verify_row_limit_exceeded():
    """Test exceeding 500 rows limit returns 422 BULK_VERIFY_ROW_LIMIT_EXCEEDED."""
    verifier_account = InstitutionAccount(
        id=VERIFIER_ACCOUNT_ID,
        org_id=VERIFIER_ORG_ID,
        email="verifier_limit@org.com",
        password_hash="hashed",
        org_type="verifier",
        status="active",
    )
    await verifier_account.insert()

    # Generate 501 rows
    lines = [f"CODE-{i}" for i in range(501)]
    csv_content = "\n".join(lines)

    app.dependency_overrides[require_current_actor] = mock_auth_dependency(
        verifier_account, "institution_account"
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        files = {"file": ("codes.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
        response = await client.post("/api/v1/verifier/verified-links/bulk-verify", files=files)

    app.dependency_overrides.clear()

    assert response.status_code == 422
    res_json = response.json()
    assert res_json["success"] is False
    assert res_json["error_code"] == "BULK_VERIFY_ROW_LIMIT_EXCEEDED"


@pytest.mark.asyncio
async def test_bulk_verify_empty_or_invalid_file():
    """Test empty file returns 400 INVALID_CSV_FILE."""
    verifier_account = InstitutionAccount(
        id=VERIFIER_ACCOUNT_ID,
        org_id=VERIFIER_ORG_ID,
        email="verifier_empty@org.com",
        password_hash="hashed",
        org_type="verifier",
        status="active",
    )
    await verifier_account.insert()

    app.dependency_overrides[require_current_actor] = mock_auth_dependency(
        verifier_account, "institution_account"
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        files = {"file": ("empty.csv", io.BytesIO(b"   \n  \n"), "text/csv")}
        response = await client.post("/api/v1/verifier/verified-links/bulk-verify", files=files)

    app.dependency_overrides.clear()

    assert response.status_code == 400
    res_json = response.json()
    assert res_json["success"] is False
    assert res_json["error_code"] == "INVALID_CSV_FILE"
