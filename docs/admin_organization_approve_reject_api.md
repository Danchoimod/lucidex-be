# Backend API Documentation

Hai API bên dưới yêu cầu Admin access token hợp lệ:

```http
Authorization: Bearer <admin_access_token>
```

Role được phép sử dụng: `super_admin` hoặc `operations_admin`.

## Admin Approve Organization
`POST /api/v1/admin/organizations/{organization_id}/approve`

**Path parameter**

| Tên | Kiểu | Mô tả |
|---|---|---|
| `organization_id` | MongoDB ObjectId | ID của Organization cần phê duyệt |

**Request**
```json
{}
```

API này không nhận request body.

**Response success**
```json
{
  "success": true,
  "data": {
    "organization_id": "507f1f77bcf86cd799439011",
    "organization_status": "approved",
    "invite_status": "pending",
    "invite_expires_at": "2026-07-28T09:16:35.748104Z",
    "email_sent": true,
    "invite_token": "<raw-invite-token>"
  },
  "message": "Organization approved and invitation sent.",
  "error_code": null
}
```

**Lỗi (nếu không success)**

| HTTP | Mã lỗi | Trường hợp |
|---:|---|---|
| `401` | `INVALID_ADMIN_ACCESS_TOKEN` | Thiếu token, token sai/hết hạn, session không active/chưa xác thực 2FA, hoặc tài khoản Admin không hợp lệ |
| `404` | `ORGANIZATION_NOT_FOUND` | Không tìm thấy Organization theo `organization_id` |
| `409` | `ORGANIZATION_DECISION_FINAL` | Organization không còn ở trạng thái `pending_review` vì đã được approve hoặc reject |
| `409` | `ORGANIZATION_DECISION_CONFLICT` | Trạng thái Organization sau khi cập nhật không khớp với quyết định approve |
| `409` | `INVITATION_ROTATION_CONFLICT` | Invite mới không còn ở trạng thái `pending` trước khi gửi email |
| `502` | `INVITATION_EMAIL_FAILED` | Gửi email mời thất bại; invite vừa tạo sẽ bị thu hồi |
| `422` | `VALIDATION_ERROR` | `organization_id` không đúng định dạng MongoDB ObjectId |

**WF**
```text
Xác thực Admin → Kiểm tra Organization đang pending_review
→ Cập nhật status=approved, reviewed_by, reviewed_at
→ Thu hồi invite pending cũ và tạo invite mới (hết hạn sau 72 giờ)
→ Gửi email chứa link thiết lập mật khẩu
→ Ghi structured log → Trả kết quả
```

---

## Admin Reject Organization
`POST /api/v1/admin/organizations/{organization_id}/reject`

**Path parameter**

| Tên | Kiểu | Mô tả |
|---|---|---|
| `organization_id` | MongoDB ObjectId | ID của Organization cần từ chối |

**Request**
```json
{
  "reason": "Required compliance documents were not provided."
}
```

`reason` là bắt buộc về mặt nghiệp vụ. Chuỗi rỗng hoặc chỉ chứa khoảng trắng không được chấp nhận; khoảng trắng ở đầu và cuối sẽ được loại bỏ.

**Response success**
```json
{
  "success": true,
  "data": {
    "organization_id": "507f1f77bcf86cd799439011",
    "organization_status": "rejected",
    "rejection_reason": "Required compliance documents were not provided.",
    "reviewed_at": "2026-07-25T09:16:35.748104Z"
  },
  "message": "Organization application rejected.",
  "error_code": null
}
```

**Lỗi (nếu không success)**

| HTTP | Mã lỗi | Trường hợp |
|---:|---|---|
| `401` | `INVALID_ADMIN_ACCESS_TOKEN` | Thiếu token, token sai/hết hạn, session không active/chưa xác thực 2FA, hoặc tài khoản Admin không hợp lệ |
| `404` | `ORGANIZATION_NOT_FOUND` | Không tìm thấy Organization theo `organization_id` |
| `409` | `ORGANIZATION_DECISION_FINAL` | Organization không còn ở trạng thái `pending_review` vì đã được approve hoặc reject |
| `409` | `ORGANIZATION_DECISION_CONFLICT` | Trạng thái Organization sau khi cập nhật không khớp với quyết định reject |
| `422` | `VALIDATION_ERROR` | Thiếu `reason`, `reason` rỗng/chỉ có khoảng trắng, body có field không được hỗ trợ, hoặc `organization_id` sai định dạng |
| `500` | `REJECTION_NOTIFICATION_FAILED` | Không thể tạo notification thông báo Organization bị từ chối |
| `500` | `REJECTION_AUDIT_FAILED` | Không thể ghi audit log cho thao tác reject |
| `502` | `REJECTION_EMAIL_FAILED` | Không thể gửi email thông báo từ chối |

**WF**
```text
Xác thực Admin → Validate và chuẩn hóa reason
→ Kiểm tra Organization đang pending_review
→ Cập nhật status=rejected, rejection_reason, reviewed_by, reviewed_at
→ Gửi email thông báo từ chối
→ Tạo notification → Ghi audit log → Trả kết quả
```

> Lưu ý: quyết định approve/reject là quyết định cuối cùng. API không cho phép chuyển một Organization đã `approved` hoặc `rejected` sang trạng thái khác.
