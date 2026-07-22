# Admin Organization Approval & Invitation API

Tài liệu này mô tả phần Thành viên 1 đã triển khai: Super Admin phê duyệt
Organization, phát hành InviteLink và contract validate invite bàn giao cho
Thành viên 2.

## 1. Yêu cầu xác thực

API approve bắt buộc sử dụng access token của Super Admin đã hoàn tất password
login và TOTP.

Luồng lấy access token:

```text
POST /api/v1/admin/auth/login
→ nhận setup_token hoặc challenge_token
→ verify TOTP
→ nhận access_token
```

Nếu tài khoản chưa thiết lập TOTP:

```http
POST /api/v1/admin/auth/totp/setup/verify
```

Nếu tài khoản đã thiết lập TOTP:

```http
POST /api/v1/admin/auth/totp/login/verify
```

Gửi access token bằng header:

```http
Authorization: Bearer <access_token>
```

Trong Swagger, nhấn **Authorize** và chỉ dán giá trị `access_token`.

Không sử dụng `setup_token`, `challenge_token` hoặc token của Owner.

## 2. Approve Organization

```http
POST /api/v1/admin/organizations/{organization_id}/approve
```

Endpoint không có request body.

### Path parameter

| Field | Type | Required | Description |
|---|---|---:|---|
| `organization_id` | ObjectId | Có | ID của Organization cần phê duyệt hoặc gửi lại invite |

### Authorization

Chỉ `PlatformAdmin` thỏa mãn toàn bộ điều kiện sau được phép gọi:

- Access token hợp lệ và chưa hết hạn.
- `actor_type=platform_admin`.
- Session tồn tại và active.
- Session chưa hết hạn.
- `twofa_verified=true`.
- Session actor khớp JWT subject.
- Admin có `status=active`.
- Admin có `role=super_admin`.

### Business flow

```text
Super Admin authorization
→ load Organization
→ pending_review chuyển thành approved
→ Organization đã approved thì cho phép re-invite
→ revoke InviteLink pending cũ
→ sinh raw token mới bằng CSPRNG
→ lưu SHA-256 token hash
→ tạo InviteLink pending, TTL 72 giờ
→ gửi email invite
→ trả response không chứa token
```

Task này không tạo InstitutionAccount và không tạo OTP.

### Success response

HTTP `200 OK`:

```json
{
  "success": true,
  "data": {
    "organization_id": "6a59e269c9cd9ac958c05e6a",
    "organization_status": "approved",
    "invite_status": "pending",
    "invite_expires_at": "2026-07-23T09:16:35.748104Z",
    "email_sent": true
  },
  "message": "Organization approved and invitation sent.",
  "error_code": null
}
```

Response không chứa `raw_token`, `token_hash`, password hoặc OTP.

### Curl example

```bash
curl -X POST \
  'http://127.0.0.1:8000/api/v1/admin/organizations/ORGANIZATION_ID/approve' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer ACCESS_TOKEN'
```

### Error responses

| HTTP | Error code | Meaning |
|---:|---|---|
| 401 | `INVALID_ADMIN_ACCESS_TOKEN` | Thiếu/sai/hết hạn access token hoặc Session chưa verify |
| 403 | `SUPER_ADMIN_REQUIRED` | Admin hợp lệ nhưng không có role Super Admin |
| 404 | `ORGANIZATION_NOT_FOUND` | Không tìm thấy Organization |
| 409 | `ORGANIZATION_NOT_APPROVABLE` | Organization không ở trạng thái được phép approve |
| 409 | `ORGANIZATION_APPROVAL_CONFLICT` | Conditional update xung đột với request khác |
| 502 | `INVITATION_EMAIL_FAILED` | Gửi email thất bại; invite mới đã bị revoke |

## 3. Re-invite behavior

Gọi lại cùng endpoint khi Organization đã `approved`:

```text
Invite pending cũ
→ status=revoked
→ revoked_at được cập nhật

Invite mới
→ status=pending
→ token_hash mới
→ expires_at mới
```

Mỗi Organization chỉ có tối đa một invite pending nhờ partial unique index.
Raw token cũ không còn hợp lệ.

## 4. Email invite

Subject:

```text
Hoàn tất thiết lập tài khoản tổ chức Lucidex
```

Invite URL:

```text
{FRONTEND_BASE_URL}/invite?token={raw_token}
```

Cấu hình local mặc định:

```dotenv
FRONTEND_BASE_URL=http://localhost:5173
```

Production và staging phải override bằng URL frontend thật.

Nếu gửi email thất bại, Organization có thể vẫn giữ `approved`, nhưng InviteLink
mới sẽ được chuyển từ `pending` sang `revoked`.

## 5. Shared contract cho Thành viên 2

Import:

```python
from src.invitation import InviteContext, validate_pending_invite
```

Contract:

```python
class InviteContext(BaseModel):
    invite_id: PydanticObjectId
    org_id: PydanticObjectId
    contact_email: str
    expires_at: datetime


async def validate_pending_invite(
    *,
    raw_token: str,
    session=None,
) -> InviteContext:
    ...
```

Cách gọi thông thường:

```python
context = await validate_pending_invite(raw_token=payload.invite_token)
```

Trong MongoDB transaction:

```python
context = await validate_pending_invite(
    raw_token=payload.invite_token,
    session=mongo_session,
)
```

Hàm thực hiện:

```text
SHA-256 raw token
→ tìm InviteLink theo token_hash
→ status phải là pending
→ expires_at phải lớn hơn thời gian hiện tại
→ trả InviteContext
```

Token sai, revoked, used hoặc hết hạn trả lỗi chung:

```text
error_code=INVALID_INVITE
message=Invalid or expired invitation link.
```

Hàm không consume/revoke invite, không tạo InstitutionAccount và không tạo OTP.
Invite chỉ chuyển sang `used` trong transaction activation của Thành viên 2 sau
khi OTP được verify thành công.

## 6. Kiểm tra nhanh

```bash
uv run pytest tests/admin/test_organizations.py tests/invitation/test_service.py -q
```

Kiểm tra toàn bộ Admin và Invitation:

```bash
uv run pytest tests/admin tests/invitation -q
```

