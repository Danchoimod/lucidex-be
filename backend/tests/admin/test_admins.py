import pytest
from httpx import AsyncClient
from src.admin.models import PlatformAdmin
from src.auth.services import verify_password
from src.audit.models import AuditLog

@pytest.fixture(autouse=True)
async def cleanup_database():
    """Connect to database, initialize Beanie for testing, and clear collections."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from beanie import init_beanie
    from src.config import settings
    
    test_db_name = f"{settings.MONGODB_DB_NAME}-test"
    client = AsyncIOMotorClient(settings.MONGODB_URI, uuidRepresentation="standard")
    await init_beanie(
        database=client[test_db_name],
        document_models=[PlatformAdmin, AuditLog]
    )
    
    # Clean up before
    await PlatformAdmin.get_motor_collection().delete_many({})
    await AuditLog.get_motor_collection().delete_many({})
    
    yield
    
    # Clean up after
    await PlatformAdmin.get_motor_collection().delete_many({})
    await AuditLog.get_motor_collection().delete_many({})
    client.close()


@pytest.fixture
async def client():
    from httpx import ASGITransport, AsyncClient
    from src.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac



async def create_test_super_admin() -> PlatformAdmin:
    admin = PlatformAdmin(
        username="super-admin",
        password_hash="dummy_hash",
        role="super_admin",
        twofa_method="totp",
        twofa_enabled=True,
        status="active",
    )
    await admin.insert()
    return admin


async def create_test_operations_admin(username="admin-123456") -> PlatformAdmin:
    admin = PlatformAdmin(
        username=username,
        password_hash="dummy_hash",
        role="operations_admin",
        twofa_method="totp",
        twofa_enabled=False,
        status="active",
    )
    await admin.insert()
    return admin


@pytest.mark.asyncio
async def test_create_admin_success(client: AsyncClient, monkeypatch):
    super_admin = await create_test_super_admin()
    
    # Mock require_super_admin dependency to return our super_admin
    from src.admin.dependencies import require_super_admin
    async def mock_require_super_admin():
        return super_admin
        
    # We can override the dependency in FastAPI
    from src.main import app
    app.dependency_overrides[require_super_admin] = mock_require_super_admin
    
    try:
        response = await client.post("/api/v1/admin/accounts")
        assert response.status_code == 211 or response.status_code == 201
        
        data = response.json()
        assert "username" in data
        assert "temporary_password" in data
        assert data["username"].startswith("admin-")
        assert len(data["username"]) == 12
        assert data["role"] == "operations_admin"
        assert data["status"] == "active"
        
        # Verify stored hash
        db_admin = await PlatformAdmin.get(data["id"])
        assert db_admin is not None
        assert db_admin.username == data["username"]
        assert verify_password(data["temporary_password"], db_admin.password_hash)
        
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_admin_requires_super_admin(client: AsyncClient):
    # Without dependency overrides, it should fail (either 401 or 403 depending on bearer credentials)
    response = await client.post("/api/v1/admin/accounts")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_admins(client: AsyncClient):
    super_admin = await create_test_super_admin()
    op_admin = await create_test_operations_admin()
    
    from src.admin.dependencies import require_super_admin
    async def mock_require_super_admin():
        return super_admin
        
    from src.main import app
    app.dependency_overrides[require_super_admin] = mock_require_super_admin
    
    try:
        response = await client.get("/api/v1/admin/accounts")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        usernames = [x["username"] for x in data]
        assert "super-admin" in usernames
        assert "admin-123456" in usernames
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_admin_detail(client: AsyncClient):
    super_admin = await create_test_super_admin()
    op_admin = await create_test_operations_admin()
    
    from src.admin.dependencies import require_super_admin
    async def mock_require_super_admin():
        return super_admin
        
    from src.main import app
    app.dependency_overrides[require_super_admin] = mock_require_super_admin
    
    try:
        response = await client.get(f"/api/v1/admin/accounts/{str(op_admin.id)}")
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin-123456"
        assert data["role"] == "operations_admin"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_admin_lock_and_unlock(client: AsyncClient):
    super_admin = await create_test_super_admin()
    op_admin = await create_test_operations_admin()
    
    from src.admin.dependencies import require_super_admin
    async def mock_require_super_admin():
        return super_admin
        
    from src.main import app
    app.dependency_overrides[require_super_admin] = mock_require_super_admin
    
    try:
        # Lock request without reason should fail
        response = await client.put(
            f"/api/v1/admin/accounts/{str(op_admin.id)}",
            json={"status": "locked"}
        )
        assert response.status_code == 400
        assert "reason" in response.text or "Reason" in response.text
        
        # Lock with reason should succeed
        response = await client.put(
            f"/api/v1/admin/accounts/{str(op_admin.id)}",
            json={"status": "locked", "reason": "Repeated security violations"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "locked"
        
        # Check database update
        db_admin = await PlatformAdmin.get(op_admin.id)
        assert db_admin.status == "locked"
        
        # Check audit log was written
        audit_logs = await AuditLog.find_all().to_list()
        assert len(audit_logs) == 1
        assert audit_logs[0].action_type == "account_suspended"
        assert "Repeated security violations" in audit_logs[0].detail
        
        # Unlock the account
        response = await client.put(
            f"/api/v1/admin/accounts/{str(op_admin.id)}",
            json={"status": "active"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "active"
        
        db_admin = await PlatformAdmin.get(op_admin.id)
        assert db_admin.status == "active"
        
        # Check reinstatement audit log
        audit_logs = await AuditLog.find_all().to_list()
        assert len(audit_logs) == 2
        assert audit_logs[1].action_type == "account_reinstated"
        
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_lock_super_admin_forbidden(client: AsyncClient):
    super_admin = await create_test_super_admin()
    
    from src.admin.dependencies import require_super_admin
    async def mock_require_super_admin():
        return super_admin
        
    from src.main import app
    app.dependency_overrides[require_super_admin] = mock_require_super_admin
    
    try:
        # Cannot lock super admin
        response = await client.put(
            f"/api/v1/admin/accounts/{str(super_admin.id)}",
            json={"status": "locked", "reason": "Self lock"}
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_reset_admin_password(client: AsyncClient):
    super_admin = await create_test_super_admin()
    op_admin = await create_test_operations_admin()
    
    from src.admin.dependencies import require_super_admin
    async def mock_require_super_admin():
        return super_admin
        
    from src.main import app
    app.dependency_overrides[require_super_admin] = mock_require_super_admin
    
    try:
        # Reset operations admin password should succeed
        response = await client.post(f"/api/v1/admin/accounts/{str(op_admin.id)}/reset-password")
        assert response.status_code == 200
        data = response.json()
        assert "temporary_password" in data
        
        # Verify db updated password
        db_admin = await PlatformAdmin.get(op_admin.id)
        assert verify_password(data["temporary_password"], db_admin.password_hash)

        # Reset self (super admin) password should succeed
        response_self = await client.post(f"/api/v1/admin/accounts/{str(super_admin.id)}/reset-password")
        assert response_self.status_code == 200
        data_self = response_self.json()
        assert "temporary_password" in data_self

        # Reset another super admin password should fail (403)
        other_super_admin = PlatformAdmin(
            username="super-admin-2",
            password_hash="dummy_hash",
            role="super_admin",
            twofa_method="totp",
            twofa_enabled=True,
            status="active",
        )
        await other_super_admin.insert()

        response_other = await client.post(f"/api/v1/admin/accounts/{str(other_super_admin.id)}/reset-password")
        assert response_other.status_code == 403
        assert response_other.json()["error_code"] == "CANNOT_RESET_SUPER_ADMIN"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_reset_admin_2fa(client: AsyncClient):
    super_admin = await create_test_super_admin()
    op_admin = await create_test_operations_admin()
    op_admin.twofa_enabled = True
    op_admin.totp_secret = "JBSWY3DPEHPK3PXP"
    await op_admin.save()
    
    from src.admin.dependencies import require_super_admin
    async def mock_require_super_admin():
        return super_admin
        
    from src.main import app
    app.dependency_overrides[require_super_admin] = mock_require_super_admin
    
    try:
        response = await client.post(f"/api/v1/admin/accounts/{str(op_admin.id)}/reset-2fa")
        assert response.status_code == 200
        data = response.json()
        assert data["twofa_enabled"] is False
        
        # Verify db updated fields
        db_admin = await PlatformAdmin.get(op_admin.id)
        assert db_admin.twofa_enabled is False
        assert db_admin.totp_secret is None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_admin(client: AsyncClient):
    super_admin = await create_test_super_admin()
    op_admin = await create_test_operations_admin()
    
    from src.admin.dependencies import require_super_admin
    async def mock_require_super_admin():
        return super_admin
        
    from src.main import app
    app.dependency_overrides[require_super_admin] = mock_require_super_admin
    
    try:
        response = await client.delete(f"/api/v1/admin/accounts/{str(op_admin.id)}")
        assert response.status_code == 204
        
        db_admin = await PlatformAdmin.get(op_admin.id)
        assert db_admin is None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_admin_request_resets_and_super_admin_approval(client: AsyncClient):
    super_admin = await create_test_super_admin()
    op_admin = await create_test_operations_admin()
    
    from src.admin.dependencies import require_admin, require_super_admin
    from src.main import app

    # 1. Regular admin requests TOTP reset and Password reset
    async def mock_require_admin():
        return op_admin
    app.dependency_overrides[require_admin] = mock_require_admin

    try:
        res_totp = await client.post("/api/v1/admin/accounts/request-reset-totp")
        assert res_totp.status_code == 200
        assert res_totp.json()["totp_reset_requested"] is True

        res_pass = await client.post("/api/v1/admin/accounts/request-reset-password")
        assert res_pass.status_code == 200
        assert res_pass.json()["password_reset_requested"] is True

        db_op = await PlatformAdmin.get(op_admin.id)
        assert db_op.totp_reset_requested is True
        assert db_op.password_reset_requested is True
    finally:
        app.dependency_overrides.clear()

    # 2. Super Admin lists requests
    async def mock_require_super_admin():
        return super_admin
    app.dependency_overrides[require_super_admin] = mock_require_super_admin

    try:
        res_list = await client.get("/api/v1/admin/accounts/requests")
        assert res_list.status_code == 200
        reqs = res_list.json()
        assert len(reqs) == 1
        assert reqs[0]["username"] == op_admin.username
        assert reqs[0]["totp_reset_requested"] is True
        assert reqs[0]["password_reset_requested"] is True

        # 3. Super Admin approves TOTP reset -> sets totp_reset_requested back to False
        res_app_totp = await client.post(f"/api/v1/admin/accounts/{str(op_admin.id)}/reset-2fa")
        assert res_app_totp.status_code == 200
        assert res_app_totp.json()["totp_reset_requested"] is False

        # 4. Super Admin approves Password reset -> sets password_reset_requested back to False
        res_app_pass = await client.post(f"/api/v1/admin/accounts/{str(op_admin.id)}/reset-password")
        assert res_app_pass.status_code == 200
        
        # Verify db status
        db_after = await PlatformAdmin.get(op_admin.id)
        assert db_after.totp_reset_requested is False
        assert db_after.password_reset_requested is False
    finally:
        app.dependency_overrides.clear()
