from datetime import UTC, date, datetime, timedelta

import pytest
from beanie import PydanticObjectId
from httpx import ASGITransport, AsyncClient

from src.auth.dependencies import require_current_actor
from src.config import settings
from src.credential.models import Credential, VerifiedLinkAccessLog
from src.credential.schemas import CreateVerifiedLinkRequest
from src.credential.services import verified_link as verified_link_service
from src.credential.services import verify_code as verify_code_service
from src.exceptions import AppError
from src.main import app
from src.organization.models import InstitutionAccount, Organization
from src.owner.models import Owner

TEST_DB_NAME = f"{settings.MONGODB_DB_NAME}-test"

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
async def test_create_and_verify_verified_link():
    """T019a: Happy path create (US1) and verify (US3)."""
    owner = Owner(id=OWNER_ID, email="owner@example.com", status="active")
    await owner.insert()

    credential = Credential(
        id=PydanticObjectId(),
        issuer_org_id=ISSUER_ORG_ID,
        student_id="STD001",
        full_name="Nguyễn Văn A",
        dob=date(2000, 1, 1),
        graduation_year=2022,
        university_email="student@univ.edu.vn",
        status="claimed",
        owner_id=OWNER_ID,
    )
    await credential.insert()

    verifier_account = InstitutionAccount(
        id=VERIFIER_ACCOUNT_ID,
        org_id=VERIFIER_ORG_ID,
        email="verifier@org.com",
        password_hash="hash",
    )
    await verifier_account.insert()

    # 1. Create Verified Link via Service
    payload = CreateVerifiedLinkRequest(credential_id=str(credential.id))
    link, code = await verified_link_service.create_verified_link(OWNER_ID, payload)
    assert link is not None
    assert len(code) == 12

    # 2. Verify Code via Service
    verify_res = await verify_code_service.verify_code(code, verifier_account)
    assert verify_res.success is True
    assert verify_res.data is not None
    assert verify_res.data.credential.full_name == "Nguyễn Văn A"
    assert verify_res.data.credential.student_id == "STD001"

    # Check access log written
    logs = await VerifiedLinkAccessLog.find({"link_id": link.id}).to_list()
    assert len(logs) == 1
    assert logs[0].verifier_org_id == VERIFIER_ORG_ID


@pytest.mark.asyncio
async def test_revoke_and_verify_denial():
    """T019b: Revoke link (US5) and check verify denial (US3)."""
    owner = Owner(id=OWNER_ID, email="owner@example.com", status="active")
    await owner.insert()

    credential = Credential(
        id=PydanticObjectId(),
        issuer_org_id=ISSUER_ORG_ID,
        student_id="STD002",
        full_name="Trần Thị B",
        dob=date(2001, 5, 5),
        graduation_year=2023,
        university_email="student2@univ.edu.vn",
        status="claimed",
        owner_id=OWNER_ID,
    )
    await credential.insert()

    verifier_account = InstitutionAccount(
        id=VERIFIER_ACCOUNT_ID,
        org_id=VERIFIER_ORG_ID,
        email="verifier@org.com",
        password_hash="hash",
    )
    await verifier_account.insert()

    link, code = await verified_link_service.create_verified_link(
        OWNER_ID, CreateVerifiedLinkRequest(credential_id=str(credential.id))
    )

    # Revoke link
    revoked_link = await verified_link_service.revoke_verified_link(OWNER_ID, str(link.id))
    assert revoked_link.status == "revoked"

    # Verify revoked link
    verify_res = await verify_code_service.verify_code(code, verifier_account)
    assert verify_res.success is False
    assert verify_res.error_code == "LINK_REVOKED"
    assert verify_res.message == "Access revoked."


@pytest.mark.asyncio
async def test_expired_code_denial():
    """T019c: Expired code verification denial (US3)."""
    owner = Owner(id=OWNER_ID, email="owner@example.com", status="active")
    await owner.insert()

    credential = Credential(
        id=PydanticObjectId(),
        issuer_org_id=ISSUER_ORG_ID,
        student_id="STD003",
        full_name="Lê Văn C",
        dob=date(1999, 3, 3),
        graduation_year=2021,
        university_email="student3@univ.edu.vn",
        status="claimed",
        owner_id=OWNER_ID,
    )
    await credential.insert()

    verifier_account = InstitutionAccount(
        id=VERIFIER_ACCOUNT_ID,
        org_id=VERIFIER_ORG_ID,
        email="verifier@org.com",
        password_hash="hash",
    )
    await verifier_account.insert()

    future_exp = datetime.now(UTC) + timedelta(hours=1)
    link, code = await verified_link_service.create_verified_link(
        OWNER_ID, CreateVerifiedLinkRequest(credential_id=str(credential.id), expires_at=future_exp)
    )

    # Manually update DB expires_at to past
    link.expires_at = datetime.now(UTC) - timedelta(hours=1)
    await link.save()

    # Verify expired link
    verify_res = await verify_code_service.verify_code(code, verifier_account)
    assert verify_res.success is False
    assert verify_res.error_code == "LINK_EXPIRED"
    assert verify_res.message == "This link has expired."


@pytest.mark.asyncio
async def test_exhausted_access_count_denial():
    """T019d: Access count max_access_count=1 (US3). First succeeds, second denied."""
    owner = Owner(id=OWNER_ID, email="owner@example.com", status="active")
    await owner.insert()

    credential = Credential(
        id=PydanticObjectId(),
        issuer_org_id=ISSUER_ORG_ID,
        student_id="STD004",
        full_name="Phạm Văn D",
        dob=date(2002, 2, 2),
        graduation_year=2024,
        university_email="student4@univ.edu.vn",
        status="claimed",
        owner_id=OWNER_ID,
    )
    await credential.insert()

    verifier_account = InstitutionAccount(
        id=VERIFIER_ACCOUNT_ID,
        org_id=VERIFIER_ORG_ID,
        email="verifier@org.com",
        password_hash="hash",
    )
    await verifier_account.insert()

    link, code = await verified_link_service.create_verified_link(
        OWNER_ID, CreateVerifiedLinkRequest(credential_id=str(credential.id), max_access_count=1)
    )

    # 1st verify succeeds
    v1 = await verify_code_service.verify_code(code, verifier_account)
    assert v1.success is True

    # 2nd verify fails (expired due to exhausted access count)
    v2 = await verify_code_service.verify_code(code, verifier_account)
    assert v2.success is False
    assert v2.error_code == "LINK_EXPIRED"
    assert v2.message == "This link has expired."


@pytest.mark.asyncio
async def test_org_restricted_code_denial():
    """T019e: Org-restricted code verification denial (US3)."""
    owner = Owner(id=OWNER_ID, email="owner@example.com", status="active")
    await owner.insert()

    credential = Credential(
        id=PydanticObjectId(),
        issuer_org_id=ISSUER_ORG_ID,
        student_id="STD005",
        full_name="Vũ Văn E",
        dob=date(2001, 10, 10),
        graduation_year=2023,
        university_email="student5@univ.edu.vn",
        status="claimed",
        owner_id=OWNER_ID,
    )
    await credential.insert()

    allowed_org = Organization(
        id=VERIFIER_ORG_ID,
        type="verifier",
        name="Allowed Org",
        tax_code="1234567890",
        address="123 Street",
        legal_rep_name="Legal Rep",
        contact_email="org@test.com",
        contact_phone="0901234567",
        registrant_name="Registrant Name",
        status="approved",
    )
    await allowed_org.insert()

    allowed_account = InstitutionAccount(
        id=PydanticObjectId(),
        org_id=VERIFIER_ORG_ID,
        email="allowed@org.com",
        password_hash="hash",
    )
    await allowed_account.insert()

    disallowed_account = InstitutionAccount(
        id=PydanticObjectId(),
        org_id=OTHER_VERIFIER_ORG_ID,
        email="disallowed@org.com",
        password_hash="hash",
    )
    await disallowed_account.insert()

    # Disallowed org verify fails (non-existent org ID at creation raises InvalidOrgIdError)
    with pytest.raises(AppError) as exc_info:
        await verified_link_service.create_verified_link(
            OWNER_ID,
            CreateVerifiedLinkRequest(
                credential_id=str(credential.id), allowed_org_ids=[str(PydanticObjectId())]
            ),
        )
    assert exc_info.value.error_code == "INVALID_ORG_ID"

    # Valid org ID at creation
    link, code = await verified_link_service.create_verified_link(
        OWNER_ID,
        CreateVerifiedLinkRequest(
            credential_id=str(credential.id), allowed_org_ids=[str(VERIFIER_ORG_ID)]
        ),
    )

    assert link.consent_mode == "trusted_orgs"

    # Disallowed org verify fails
    v1 = await verify_code_service.verify_code(code, disallowed_account)
    assert v1.success is False
    assert v1.error_code == "UNAUTHORIZED_VERIFIER"
    assert v1.message == "This organization is not authorized to view this credential."

    # Allowed org verify succeeds
    v2 = await verify_code_service.verify_code(code, allowed_account)
    assert v2.success is True


@pytest.mark.asyncio
async def test_invalid_code_submitted():
    """T019f: Invalid code verification denial (US3)."""
    verifier_account = InstitutionAccount(
        id=PydanticObjectId(),
        org_id=VERIFIER_ORG_ID,
        email="verifier_invalid@org.com",
        password_hash="hash",
    )
    await verifier_account.insert()

    res = await verify_code_service.verify_code("INVALIDCODE99", verifier_account)
    assert res.success is False
    assert res.error_code == "INVALID_VERIFICATION_CODE"


@pytest.mark.asyncio
async def test_list_verified_links():
    """T019g: List verification codes with display_status (US2)."""
    owner = Owner(id=OWNER_ID, email="owner@example.com", status="active")
    await owner.insert()

    issuer_org = Organization(
        id=ISSUER_ORG_ID,
        type="issuer",
        name="Test University",
        tax_code="1234567891",
        address="123 Street",
        legal_rep_name="Legal Rep",
        contact_email="org2@test.com",
        contact_phone="0901234568",
        registrant_name="Registrant Name",
        status="approved",
    )
    await issuer_org.insert()

    credential = Credential(
        id=PydanticObjectId(),
        issuer_org_id=ISSUER_ORG_ID,
        student_id="STD006",
        full_name="Đặng Văn F",
        dob=date(2000, 4, 4),
        degree_type="Bachelor",
        graduation_year=2022,
        university_email="student6@univ.edu.vn",
        status="claimed",
        owner_id=OWNER_ID,
    )
    await credential.insert()

    await verified_link_service.create_verified_link(
        OWNER_ID, CreateVerifiedLinkRequest(credential_id=str(credential.id))
    )
    await verified_link_service.create_verified_link(
        OWNER_ID, CreateVerifiedLinkRequest(credential_id=str(credential.id))
    )

    list_res = await verified_link_service.list_verified_links(OWNER_ID)
    assert list_res.total == 2
    assert len(list_res.items) == 2
    assert list_res.items[0].display_status == "active"
    assert list_res.items[0].issuer_name == "Test University"
    assert list_res.items[0].degree_type == "Bachelor"
    assert list_res.items[0].graduation_year == 2022


@pytest.mark.asyncio
async def test_double_revoke_rejected():
    """T019j: Attempt double revoke rejected (US5)."""
    owner = Owner(id=OWNER_ID, email="owner@example.com", status="active")
    await owner.insert()

    credential = Credential(
        id=PydanticObjectId(),
        issuer_org_id=ISSUER_ORG_ID,
        student_id="STD009",
        full_name="Đỗ Văn I",
        dob=date(2000, 9, 9),
        graduation_year=2022,
        university_email="student9@univ.edu.vn",
        status="claimed",
        owner_id=OWNER_ID,
    )
    await credential.insert()

    link, _ = await verified_link_service.create_verified_link(
        OWNER_ID, CreateVerifiedLinkRequest(credential_id=str(credential.id))
    )

    await verified_link_service.revoke_verified_link(OWNER_ID, str(link.id))

    with pytest.raises(AppError) as exc_info:
        await verified_link_service.revoke_verified_link(OWNER_ID, str(link.id))
    assert exc_info.value.error_code == "LINK_ALREADY_REVOKED"


@pytest.mark.asyncio
async def test_api_endpoints_via_httpx():
    """Integration test via HTTP endpoints using httpx ASGITransport."""
    owner = Owner(id=OWNER_ID, email="owner@example.com", status="active")
    await owner.insert()

    credential = Credential(
        id=PydanticObjectId(),
        issuer_org_id=ISSUER_ORG_ID,
        student_id="STD010",
        full_name="Ngô Văn J",
        dob=date(2000, 10, 10),
        graduation_year=2022,
        university_email="student10@univ.edu.vn",
        status="claimed",
        owner_id=OWNER_ID,
    )
    await credential.insert()

    verifier_account = InstitutionAccount(
        id=VERIFIER_ACCOUNT_ID,
        org_id=VERIFIER_ORG_ID,
        email="verifier@org.com",
        password_hash="hash",
    )
    await verifier_account.insert()

    app.dependency_overrides[require_current_actor] = mock_auth_dependency(owner, "owner")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # POST create
        res = await ac.post("/api/v1/owner/verified-links", json={"credential_id": str(credential.id)})
        assert res.status_code == 201
        body = res.json()
        assert body["success"] is True
        code = body["data"]["code"]
        link_id = body["data"]["id"]

        # GET list
        res_list = await ac.get("/api/v1/owner/verified-links")
        assert res_list.status_code == 200
        assert res_list.json()["data"]["total"] == 1

        # POST verify (switch actor to verifier)
        app.dependency_overrides[require_current_actor] = mock_auth_dependency(verifier_account, "institution_account")
        res_verify = await ac.post("/api/v1/verifier/verified-links/verify", json={"code": code})
        assert res_verify.status_code == 200
        assert res_verify.json()["success"] is True
        assert res_verify.json()["data"]["credential"]["student_id"] == "STD010"

        # DELETE revoke (switch back to owner)
        app.dependency_overrides[require_current_actor] = mock_auth_dependency(owner, "owner")
        res_revoke = await ac.delete(f"/api/v1/owner/verified-links/{link_id}/revoke")
        assert res_revoke.status_code == 200
        assert res_revoke.json()["data"]["status"] == "revoked"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_verified_link_applies_owner_defaults():
    """Test that create_verified_link applies owner default link settings when fields are omitted."""
    from src.owner.models import DefaultLinkSettings

    owner = Owner(
        id=PydanticObjectId(),
        email="owner_defaults@example.com",
        status="active",
        default_link_settings=DefaultLinkSettings(
            default_consent_mode="access_count",
            default_max_access_count=5,
            default_expiry_hours=24,
        ),
    )
    await owner.insert()

    credential = Credential(
        id=PydanticObjectId(),
        issuer_org_id=ISSUER_ORG_ID,
        student_id="STD_DEF",
        full_name="Default Test User",
        dob=date(2000, 1, 1),
        graduation_year=2022,
        university_email="default@univ.edu.vn",
        status="claimed",
        owner_id=owner.id,
    )
    await credential.insert()

    # Create link with fields omitted -> should use owner defaults
    payload = CreateVerifiedLinkRequest(credential_id=str(credential.id))
    link, _ = await verified_link_service.create_verified_link(owner.id, payload, owner=owner)

    assert link.max_access_count == 5
    assert link.expires_at is not None
    assert link.consent_mode == "access_count"  # default_consent_mode takes precedence when options omitted

    # Explicit null max_access_count -> overrides saved default to unlimited
    payload_override = CreateVerifiedLinkRequest(credential_id=str(credential.id), max_access_count=None)
    link_override, _ = await verified_link_service.create_verified_link(owner.id, payload_override, owner=owner)

    assert link_override.max_access_count is None


@pytest.mark.asyncio
async def test_create_verified_link_unclaimed_credential_raises_not_found():
    """Test that creating a verified link for an unclaimed credential raises CredentialNotFoundError (404)."""
    from src.credential.exceptions import CredentialNotFoundError

    owner = Owner(
        id=PydanticObjectId(),
        email="unclaimed_owner@example.com",
        status="active",
    )
    await owner.insert()

    credential = Credential(
        id=PydanticObjectId(),
        issuer_org_id=ISSUER_ORG_ID,
        student_id="STD_UNCLAIMED",
        full_name="Unclaimed User",
        dob=date(2000, 1, 1),
        graduation_year=2022,
        university_email="unclaimed@univ.edu.vn",
        status="unclaimed",
        owner_id=owner.id,
    )
    await credential.insert()

    payload = CreateVerifiedLinkRequest(credential_id=str(credential.id))
    with pytest.raises(CredentialNotFoundError):
        await verified_link_service.create_verified_link(owner.id, payload, owner=owner)


