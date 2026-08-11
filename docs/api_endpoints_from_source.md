# API endpoints đối chiếu từ source code

# Super Admin

## CRUD — Admin account

### list_reset_requests

**Endpoint**
```http
GET /api/v1/admin/accounts/requests
```

**Parameters**

None

**Request body**
```json
None
```

**Response**
```json
[
  {
    "id": "string",
    "username": "string",
    "role": "string",
    "status": "string",
    "twofa_enabled": "boolean",
    "totp_reset_requested": "boolean",
    "totp_reset_requested_at": "datetime|null",
    "password_reset_requested": "boolean",
    "password_reset_requested_at": "datetime|null"
  }
]
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_ADMIN_ACCESS_TOKEN | Thiếu/sai/hết hạn access token; session không active, hết hạn, chưa xác minh TOTP; hoặc Admin không còn đủ điều kiện đăng nhập. |
| 403 | SUPER_ADMIN_REQUIRED | Admin hiện tại không có role `super_admin`. |

### create_admin

**Endpoint**
```http
POST /api/v1/admin/accounts
```

**Parameters**

None

**Request body**
```json
None
```

**Response**
```json
{
  "id": "string",
  "username": "string",
  "role": "string",
  "status": "string",
  "temporary_password": "string"
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_ADMIN_ACCESS_TOKEN | Admin access token hoặc session không hợp lệ. |
| 403 | SUPER_ADMIN_REQUIRED | Admin hiện tại không có role `super_admin`. |

### list_admins

**Endpoint**
```http
GET /api/v1/admin/accounts
```

**Parameters**

None

**Request body**
```json
None
```

**Response**
```json
[
  {
    "id": "string",
    "username": "string",
    "role": "string",
    "status": "string",
    "twofa_enabled": "boolean",
    "totp_reset_requested": "boolean",
    "totp_reset_requested_at": "datetime|null",
    "password_reset_requested": "boolean",
    "password_reset_requested_at": "datetime|null"
  }
]
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_ADMIN_ACCESS_TOKEN | Admin access token hoặc session không hợp lệ. |
| 403 | SUPER_ADMIN_REQUIRED | Admin hiện tại không có role `super_admin`. |

### get_admin

**Endpoint**
```http
GET /api/v1/admin/accounts/{id}
```

**Parameters**

- Path `id`: `string` — MongoDB ObjectId của Admin.

**Request body**
```json
None
```

**Response**
```json
{
  "id": "string",
  "username": "string",
  "role": "string",
  "status": "string",
  "twofa_enabled": "boolean",
  "totp_reset_requested": "boolean",
  "totp_reset_requested_at": "datetime|null",
  "password_reset_requested": "boolean",
  "password_reset_requested_at": "datetime|null"
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_ADMIN_ACCESS_TOKEN | Admin access token hoặc session không hợp lệ. |
| 403 | SUPER_ADMIN_REQUIRED | Admin hiện tại không có role `super_admin`. |
| 404 | ADMIN_NOT_FOUND | `id` không phải ObjectId hợp lệ hoặc không tìm thấy Admin. |

### update_admin

**Endpoint**
```http
PUT /api/v1/admin/accounts/{id}
```

**Parameters**

- Path `id`: `string` — MongoDB ObjectId của Admin.

**Request body**
```json
{
  "status": "active|locked",
  "reason": "string|null"
}
```

**Response**
```json
{
  "id": "string",
  "username": "string",
  "role": "string",
  "status": "string",
  "twofa_enabled": "boolean",
  "totp_reset_requested": "boolean",
  "totp_reset_requested_at": "datetime|null",
  "password_reset_requested": "boolean",
  "password_reset_requested_at": "datetime|null"
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 400 | REASON_REQUIRED | Chuyển sang `locked` nhưng `reason` thiếu hoặc chỉ có khoảng trắng. |
| 401 | INVALID_ADMIN_ACCESS_TOKEN | Admin access token hoặc session không hợp lệ. |
| 403 | SUPER_ADMIN_REQUIRED | Admin hiện tại không có role `super_admin`. |
| 403 | CANNOT_LOCK_SUPER_ADMIN | Target là Super Admin hoặc chính Admin đang gọi API khi yêu cầu `locked`. |
| 404 | ADMIN_NOT_FOUND | `id` không phải ObjectId hợp lệ hoặc không tìm thấy Admin. |
| 422 | VALIDATION_ERROR | Body thiếu `status`, sai kiểu, hoặc `status` không phải `active`/`locked`. |

### reset_admin_password

**Endpoint**
```http
POST /api/v1/admin/accounts/{id}/reset-password
```

**Parameters**

- Path `id`: `string` — MongoDB ObjectId của Admin.

**Request body**
```json
None
```

**Response**
```json
{
  "username": "string",
  "temporary_password": "string"
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_ADMIN_ACCESS_TOKEN | Admin access token hoặc session không hợp lệ. |
| 403 | SUPER_ADMIN_REQUIRED | Admin hiện tại không có role `super_admin`. |
| 403 | CANNOT_RESET_SUPER_ADMIN | Target là Super Admin khác với Super Admin đang gọi API. |
| 404 | ADMIN_NOT_FOUND | `id` không phải ObjectId hợp lệ hoặc không tìm thấy Admin. |

### reset_admin_2fa

**Endpoint**
```http
POST /api/v1/admin/accounts/{id}/reset-2fa
```

**Parameters**

- Path `id`: `string` — MongoDB ObjectId của Admin.

**Request body**
```json
None
```

**Response**
```json
{
  "id": "string",
  "username": "string",
  "role": "string",
  "status": "string",
  "twofa_enabled": "boolean",
  "totp_reset_requested": "boolean",
  "totp_reset_requested_at": "datetime|null",
  "password_reset_requested": "boolean",
  "password_reset_requested_at": "datetime|null"
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_ADMIN_ACCESS_TOKEN | Admin access token hoặc session không hợp lệ. |
| 403 | SUPER_ADMIN_REQUIRED | Admin hiện tại không có role `super_admin`. |
| 403 | CANNOT_RESET_SUPER_ADMIN | Target là Super Admin khác với Super Admin đang gọi API. |
| 404 | ADMIN_NOT_FOUND | `id` không phải ObjectId hợp lệ hoặc không tìm thấy Admin. |

### reject_admin_2fa_reset

**Endpoint**
```http
POST /api/v1/admin/accounts/{id}/reject-reset-totp
```

**Parameters**

- Path `id`: `string` — MongoDB ObjectId của Admin.

**Request body**
```json
None
```

**Response**
```json
{
  "id": "string",
  "username": "string",
  "role": "string",
  "status": "string",
  "twofa_enabled": "boolean",
  "totp_reset_requested": "boolean",
  "totp_reset_requested_at": "datetime|null",
  "password_reset_requested": "boolean",
  "password_reset_requested_at": "datetime|null"
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 400 | NO_PENDING_TOTP_RESET_REQUEST | Target không có yêu cầu reset TOTP đang chờ. |
| 401 | INVALID_ADMIN_ACCESS_TOKEN | Admin access token hoặc session không hợp lệ. |
| 403 | SUPER_ADMIN_REQUIRED | Admin hiện tại không có role `super_admin`. |
| 404 | ADMIN_NOT_FOUND | `id` không phải ObjectId hợp lệ hoặc không tìm thấy Admin. |

### reject_admin_password_reset

**Endpoint**
```http
POST /api/v1/admin/accounts/{id}/reject-reset-password
```

**Parameters**

- Path `id`: `string` — MongoDB ObjectId của Admin.

**Request body**
```json
None
```

**Response**
```json
{
  "id": "string",
  "username": "string",
  "role": "string",
  "status": "string",
  "twofa_enabled": "boolean",
  "totp_reset_requested": "boolean",
  "totp_reset_requested_at": "datetime|null",
  "password_reset_requested": "boolean",
  "password_reset_requested_at": "datetime|null"
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 400 | NO_PENDING_PASSWORD_RESET_REQUEST | Target không có yêu cầu reset password đang chờ. |
| 401 | INVALID_ADMIN_ACCESS_TOKEN | Admin access token hoặc session không hợp lệ. |
| 403 | SUPER_ADMIN_REQUIRED | Admin hiện tại không có role `super_admin`. |
| 404 | ADMIN_NOT_FOUND | `id` không phải ObjectId hợp lệ hoặc không tìm thấy Admin. |

### delete_admin

**Endpoint**
```http
DELETE /api/v1/admin/accounts/{id}
```

**Parameters**

- Path `id`: `string` — MongoDB ObjectId của Admin.

**Request body**
```json
None
```

**Response**
```json
None
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_ADMIN_ACCESS_TOKEN | Admin access token hoặc session không hợp lệ. |
| 403 | SUPER_ADMIN_REQUIRED | Admin hiện tại không có role `super_admin`. |
| 403 | CANNOT_DELETE_SUPER_ADMIN | Target là Super Admin hoặc chính Admin đang gọi API. |
| 404 | ADMIN_NOT_FOUND | `id` không phải ObjectId hợp lệ hoặc không tìm thấy Admin. |

# Admin

## Auth

### login_admin

**Endpoint**
```http
POST /api/v1/admin/auth/login
```

**Parameters**

None

**Request body**
```json
{
  "username": "string (min length 1)",
  "password": "string (min length 1)"
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "requires_totp_setup": "boolean|null",
    "requires_totp": "boolean|null",
    "setup_token": "string|null",
    "challenge_token": "string|null",
    "totp_uri": "string|null",
    "manual_entry_key": "string|null",
    "qr_code": "string|null"
  },
  "message": "Additional authentication is required."
}
```

Các field `null` trong `data` bị loại khỏi JSON thực tế bởi `response_model_exclude_none=True`.

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_ADMIN_CREDENTIALS | Sai username/password; account không active; role không phải `super_admin`/`operations_admin`; hoặc `twofa_method` không phải `totp`. |
| 422 | VALIDATION_ERROR | Thiếu/sai kiểu username hoặc password, hoặc chuỗi rỗng. |
| 500 | ADMIN_AUTHENTICATION_STATE_ERROR | Trạng thái TOTP không nhất quán: đã bật 2FA nhưng thiếu secret, hoặc không thể tạo/lưu secret setup. |

### verify_totp_setup

**Endpoint**
```http
POST /api/v1/admin/auth/totp/setup/verify
```

**Parameters**

None

**Request body**
```json
{
  "setup_token": "string",
  "otp_code": "string (exactly 6 digits)"
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "access_token": "string",
    "token_type": "bearer",
    "refresh_token": "string"
  },
  "message": "Logged in successfully.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_ADMIN_TOKEN | Setup token sai/hết hạn/sai purpose; account không còn đủ điều kiện; setup state không hợp lệ hoặc đã thay đổi đồng thời. |
| 401 | INVALID_AUTHENTICATION_CODE | TOTP code không hợp lệ. |
| 422 | VALIDATION_ERROR | Body thiếu/sai kiểu hoặc `otp_code` không đúng 6 chữ số. |

### verify_totp_login

**Endpoint**
```http
POST /api/v1/admin/auth/totp/login/verify
```

**Parameters**

None

**Request body**
```json
{
  "challenge_token": "string",
  "otp_code": "string (exactly 6 digits)"
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "access_token": "string",
    "token_type": "bearer",
    "refresh_token": "string"
  },
  "message": "Logged in successfully.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_ADMIN_TOKEN | Challenge token sai/hết hạn/sai purpose; account không còn đủ điều kiện; hoặc account chưa bật TOTP/thiếu secret. |
| 401 | INVALID_AUTHENTICATION_CODE | TOTP code không hợp lệ. |
| 422 | VALIDATION_ERROR | Body thiếu/sai kiểu hoặc `otp_code` không đúng 6 chữ số. |

## Self-service reset

### get_request_status

**Endpoint**
```http
GET /api/v1/admin/accounts/request-status
```

**Parameters**

None

**Request body**
```json
None
```

**Response**
```json
{
  "id": "string",
  "username": "string",
  "totp_reset_requested": "boolean",
  "totp_reset_requested_at": "datetime|null",
  "password_reset_requested": "boolean",
  "password_reset_requested_at": "datetime|null"
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_ADMIN_ACCESS_TOKEN | Admin access token hoặc session không hợp lệ. |

### request_totp_reset

**Endpoint**
```http
POST /api/v1/admin/accounts/request-reset-totp
```

**Parameters**

None

**Request body**
```json
None
```

**Response**
```json
{
  "id": "string",
  "username": "string",
  "role": "string",
  "status": "string",
  "twofa_enabled": "boolean",
  "totp_reset_requested": "boolean",
  "totp_reset_requested_at": "datetime|null",
  "password_reset_requested": "boolean",
  "password_reset_requested_at": "datetime|null"
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_ADMIN_ACCESS_TOKEN | Admin access token hoặc session không hợp lệ. |

### request_password_reset

**Endpoint**
```http
POST /api/v1/admin/accounts/request-reset-password
```

**Parameters**

None

**Request body**
```json
None
```

**Response**
```json
{
  "id": "string",
  "username": "string",
  "role": "string",
  "status": "string",
  "twofa_enabled": "boolean",
  "totp_reset_requested": "boolean",
  "totp_reset_requested_at": "datetime|null",
  "password_reset_requested": "boolean",
  "password_reset_requested_at": "datetime|null"
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_ADMIN_ACCESS_TOKEN | Admin access token hoặc session không hợp lệ. |

## CRUD — Organization review

### list_organizations_endpoint

**Endpoint**
```http
GET /api/v1/admin/organizations/list
```

**Parameters**

- Query `type`: `issuer|verifier|null` — mặc định `null`.
- Query `status`: `pending_review|approved|rejected|null` — mặc định `pending_review`.

**Request body**
```json
None
```

**Response**
```json
{
  "success": true,
  "data": [
    {
      "id": "string",
      "type": "issuer|verifier",
      "status": "pending_review|approved|rejected",
      "name": "string",
      "tax_code": "string",
      "address": "string",
      "legal_rep_name": "string",
      "contact_email": "email",
      "contact_phone": "string",
      "registrant_name": "string",
      "registrant_title": "string|null",
      "documents": [{"name": "string", "url": "string", "type": "string"}],
      "rejection_reason": "string|null",
      "reviewed_by": "string|null",
      "reviewed_at": "datetime|null",
      "created_at": "datetime"
    }
  ],
  "message": "Organizations retrieved successfully.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_ADMIN_ACCESS_TOKEN | Admin access token hoặc session không hợp lệ. |
| 422 | VALIDATION_ERROR | `type` hoặc `status` không thuộc enum được khai báo. |

### list_organizations_endpoint

**Endpoint**
```http
GET /api/v1/admin/organizations
```

**Parameters**

- Query `type`: `issuer|verifier|null` — mặc định `null`.
- Query `status`: `pending_review|approved|rejected|null` — mặc định `pending_review`.

**Request body**
```json
None
```

**Response**
```json
{
  "success": true,
  "data": [
    {
      "id": "string",
      "type": "issuer|verifier",
      "status": "pending_review|approved|rejected",
      "name": "string",
      "tax_code": "string",
      "address": "string",
      "legal_rep_name": "string",
      "contact_email": "email",
      "contact_phone": "string",
      "registrant_name": "string",
      "registrant_title": "string|null",
      "documents": [{"name": "string", "url": "string", "type": "string"}],
      "rejection_reason": "string|null",
      "reviewed_by": "string|null",
      "reviewed_at": "datetime|null",
      "created_at": "datetime"
    }
  ],
  "message": "Organizations retrieved successfully.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_ADMIN_ACCESS_TOKEN | Admin access token hoặc session không hợp lệ. |
| 422 | VALIDATION_ERROR | `type` hoặc `status` không thuộc enum được khai báo. |

## Approve / Reject

### approve_organization_endpoint

**Endpoint**
```http
POST /api/v1/admin/organizations/{organization_id}/approve
```

**Parameters**

- Path `organization_id`: MongoDB ObjectId.

**Request body**
```json
None
```

**Response**
```json
{
  "success": true,
  "data": {
    "organization_id": "string",
    "organization_status": "approved",
    "invite_status": "pending",
    "invite_expires_at": "datetime",
    "email_sent": true,
    "invite_token": "string"
  },
  "message": "Organization approved and invitation sent.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_ADMIN_ACCESS_TOKEN | Admin access token hoặc session không hợp lệ. |
| 404 | ORGANIZATION_NOT_FOUND | Không tìm thấy organization trước/trong/sau cập nhật quyết định. |
| 409 | ORGANIZATION_DECISION_FINAL | Organization không còn ở `pending_review`, kể cả do concurrent update. |
| 409 | ORGANIZATION_DECISION_CONFLICT | Organization sau cập nhật không có status `approved`. |
| 409 | INVITATION_ROTATION_CONFLICT | Trùng invite khi rotate hoặc invite mới không còn pending trước lúc gửi mail. |
| 422 | VALIDATION_ERROR | `organization_id` không phải MongoDB ObjectId hợp lệ. |
| 500 | INTERNAL_SERVER_ERROR | Admin/organization/invite đã persist nhưng không có `id`, qua global exception handler. |
| 502 | INVITATION_EMAIL_FAILED | Không resolve được template hoặc gửi email invitation thất bại; invite mới bị revoke. |

### reject_organization_endpoint

**Endpoint**
```http
POST /api/v1/admin/organizations/{organization_id}/reject
```

**Parameters**

- Path `organization_id`: MongoDB ObjectId.

**Request body**
```json
{
  "reason": "string|null"
}
```

Body là optional trong signature, nhưng service bắt buộc `reason` sau khi trim phải khác rỗng; model cấm field thừa.

**Response**
```json
{
  "success": true,
  "data": {
    "organization_id": "string",
    "organization_status": "rejected",
    "rejection_reason": "string",
    "reviewed_at": "datetime"
  },
  "message": "Organization application rejected.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_ADMIN_ACCESS_TOKEN | Admin access token hoặc session không hợp lệ. |
| 404 | ORGANIZATION_NOT_FOUND | Không tìm thấy organization trước/trong/sau cập nhật quyết định. |
| 409 | ORGANIZATION_DECISION_FINAL | Organization không còn ở `pending_review`, kể cả do concurrent update. |
| 409 | ORGANIZATION_DECISION_CONFLICT | Organization sau cập nhật không có status `rejected`. |
| 422 | VALIDATION_ERROR | `organization_id` sai; body sai schema/có field thừa; hoặc `reason` thiếu/rỗng sau khi trim. |
| 500 | REJECTION_NOTIFICATION_FAILED | Insert notification từ chối thất bại. |
| 500 | REJECTION_AUDIT_FAILED | Insert audit log từ chối thất bại. |
| 500 | INTERNAL_SERVER_ERROR | Admin/organization đã persist nhưng không có `id`, qua global exception handler. |
| 502 | REJECTION_EMAIL_FAILED | Không resolve được template hoặc gửi email từ chối thất bại. |

## Health

### health_check

**Endpoint**
```http
GET /api/v1/admin/health
```

**Parameters**

None

**Request body**
```json
None
```

**Response**
```json
{
  "success": true,
  "data": {"message": "Admin portal is running."},
  "message": "OK",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| — | — | None |

# Issuer

## Health

### health_check

**Endpoint**
```http
GET /api/v1/issuer/health
```

**Parameters**

None

**Request body**
```json
None
```

**Response**
```json
{
  "success": true,
  "data": {"message": "Issuer portal is running."},
  "message": "OK",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| — | — | None |

## Register

### register_issuer

**Endpoint**
```http
POST /api/v1/issuer/register
```

**Parameters**

None

**Request body**
```json
{
  "name": "string (2..255)",
  "tax_code": "string",
  "address": "string (1..500)",
  "legal_rep_name": "string (2..100)",
  "contact_email": "valid Gmail address",
  "contact_phone": "valid phone string",
  "registrant_name": "string (2..100)",
  "document": "binary PDF, required, max 20 MiB"
}
```

Handler khai báo các field dưới dạng `multipart/form-data`; nhánh code cũng đọc các field text từ JSON, nhưng `document` vẫn là `UploadFile` bắt buộc.

**Response**
```json
{
  "success": true,
  "data": {
    "id": "string",
    "status": "pending_review"
  },
  "message": "Your registration application has been submitted successfully and is pending review.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 400 | DOCUMENT_REQUIRED | Không có file hoặc filename rỗng. |
| 400 | INVALID_FILE_TYPE | Filename không kết thúc bằng `.pdf` (không phân biệt hoa/thường). |
| 400 | FILE_EMPTY | File PDF có 0 byte. |
| 400 | FILE_TOO_LARGE | File lớn hơn 20 MiB. |
| 409 | TAX_CODE_ALREADY_REGISTERED | Đã có live registration cùng tax code/type, hoặc insert vi phạm unique index. |
| 410 | PHONE_ALREADY_REGISTERED | Contact phone đã được dùng bởi live registration. |
| 411 | EMAIL_ALREADY_REGISTERED | Contact email đã được dùng bởi live registration. |
| 422 | VALIDATION_ERROR | Thiếu/sai kiểu/vi phạm constraint hoặc validator của registration fields. |
| 500 | INTERNAL_SERVER_ERROR | Upload GCS hoặc lưu document URL thất bại; code xóa organization rồi re-raise qua global handler. |
| 502 | ORGANIZATION_EMAIL_SENDING_FAILED | Gửi email xác nhận nhận hồ sơ thất bại; organization vừa insert bị xóa. |

## Invitation activation

### submit_issuer_password

**Endpoint**
```http
POST /api/v1/issuer/invites/password
```

**Parameters**

None

**Request body**
```json
{
  "invite_token": "string",
  "password": "string",
  "confirm_password": "string"
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "requires_otp": true,
    "otp_expires_in_seconds": 300
  },
  "message": "Password set successfully. Please check your email for the activation OTP code.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 400 | INVALID_INVITE | Invite không tồn tại, không pending, hết hạn, hoặc không có `id`. |
| 400 | ACCOUNT_NOT_ELIGIBLE | Không tìm thấy organization tương ứng invite. |
| 400 | PASSWORD_MISMATCH | `password` khác `confirm_password`. |
| 400 | WEAK_PASSWORD | Password không đạt độ dài/regex strength trong `owner.constants`. |
| 422 | VALIDATION_ERROR | Body thiếu field hoặc sai kiểu. |
| 500 | EMAIL_SENDING_FAILED | Gửi OTP email thất bại; OTP active vừa tạo bị invalidate. |

### verify_issuer_otp

**Endpoint**
```http
POST /api/v1/issuer/invites/verify-otp
```

**Parameters**

None

**Request body**
```json
{
  "invite_token": "string",
  "otp_code": "string (length exactly 6)"
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "success": true,
    "message": "OTP verified and organization account activated successfully."
  },
  "message": "Organization account activated successfully.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 400 | INVALID_INVITE | Invite không tồn tại, không pending, hết hạn, hoặc không có `id`. |
| 400 | ACCOUNT_NOT_ELIGIBLE | Không tìm thấy institution account tương ứng invite. |
| 422 | VALIDATION_ERROR | Body thiếu/sai kiểu hoặc `otp_code` không dài đúng 6 ký tự. |
| 500 | INTERNAL_SERVER_ERROR | OTP không tồn tại, hết hạn, đã dùng, sai type hoặc sai code: `OtpError` không được translate và rơi vào global handler. |

# Verifier

## Health

### health_check

**Endpoint**
```http
GET /api/v1/verifier/health
```

**Parameters**

None

**Request body**
```json
None
```

**Response**
```json
{
  "success": true,
  "data": {"message": "Verifier portal is running."},
  "message": "OK",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| — | — | None |

## Register

### register_verifier

**Endpoint**
```http
POST /api/v1/verifier/register
```

**Parameters**

None

**Request body**
```json
{
  "name": "string (2..255)",
  "tax_code": "string",
  "address": "string (1..500)",
  "legal_rep_name": "string (2..100)",
  "contact_email": "valid Gmail address",
  "contact_phone": "valid phone string",
  "registrant_name": "string (2..100)",
  "registrant_title": "string (1..100)",
  "document": "binary PDF, required, max 20 MiB"
}
```

Handler khai báo các field dưới dạng `multipart/form-data`; nhánh code cũng đọc các field text từ JSON, nhưng `document` vẫn là `UploadFile` bắt buộc.

**Response**
```json
{
  "success": true,
  "data": {
    "id": "string",
    "status": "pending_review"
  },
  "message": "Your verifier registration application has been submitted successfully and is pending review.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 400 | DOCUMENT_REQUIRED | Không có file hoặc filename rỗng. |
| 400 | INVALID_FILE_TYPE | Filename không kết thúc bằng `.pdf` (không phân biệt hoa/thường). |
| 400 | FILE_EMPTY | File PDF có 0 byte. |
| 400 | FILE_TOO_LARGE | File lớn hơn 20 MiB. |
| 409 | TAX_CODE_ALREADY_REGISTERED | Đã có live registration cùng tax code/type, hoặc insert vi phạm unique index. |
| 410 | PHONE_ALREADY_REGISTERED | Contact phone đã được dùng bởi live registration. |
| 411 | EMAIL_ALREADY_REGISTERED | Contact email đã được dùng bởi live registration. |
| 422 | VALIDATION_ERROR | Thiếu/sai kiểu/vi phạm constraint hoặc validator của registration fields, gồm `registrant_title`. |
| 500 | INTERNAL_SERVER_ERROR | Upload GCS hoặc lưu document URL thất bại; code xóa organization rồi re-raise qua global handler. |
| 502 | ORGANIZATION_EMAIL_SENDING_FAILED | Gửi email xác nhận nhận hồ sơ thất bại; organization vừa insert bị xóa. |

## Invitation activation

### submit_verifier_password

**Endpoint**
```http
POST /api/v1/verifier/invites/password
```

**Parameters**

None

**Request body**
```json
{
  "invite_token": "string",
  "password": "string",
  "confirm_password": "string"
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "requires_otp": true,
    "otp_expires_in_seconds": 300
  },
  "message": "Password set successfully. Please check your email for the activation OTP code.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 400 | INVALID_INVITE | Invite không tồn tại, không pending, hết hạn, hoặc không có `id`. |
| 400 | ACCOUNT_NOT_ELIGIBLE | Không tìm thấy organization tương ứng invite. |
| 400 | PASSWORD_MISMATCH | `password` khác `confirm_password`. |
| 400 | WEAK_PASSWORD | Password không đạt độ dài/regex strength trong `owner.constants`. |
| 422 | VALIDATION_ERROR | Body thiếu field hoặc sai kiểu. |
| 500 | EMAIL_SENDING_FAILED | Gửi OTP email thất bại; OTP active vừa tạo bị invalidate. |

### verify_verifier_otp

**Endpoint**
```http
POST /api/v1/verifier/invites/verify-otp
```

**Parameters**

None

**Request body**
```json
{
  "invite_token": "string",
  "otp_code": "string (length exactly 6)"
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "success": true,
    "message": "OTP verified and organization account activated successfully."
  },
  "message": "Organization account activated successfully.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 400 | INVALID_INVITE | Invite không tồn tại, không pending, hết hạn, hoặc không có `id`. |
| 400 | ACCOUNT_NOT_ELIGIBLE | Không tìm thấy institution account tương ứng invite. |
| 422 | VALIDATION_ERROR | Body thiếu/sai kiểu hoặc `otp_code` không dài đúng 6 ký tự. |
| 500 | INTERNAL_SERVER_ERROR | OTP không tồn tại, hết hạn, đã dùng, sai type hoặc sai code: `OtpError` không được translate và rơi vào global handler. |
# Owner

## Health

### health_check

**Endpoint**
```http
GET /api/v1/owner/health
```

**Parameters**

None

**Request body**
```json
None
```

**Response**
```json
{
  "success": true,
  "data": {"message": "Owner portal is running."},
  "message": "OK",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| — | — | None |

## Register / OTP

### register_owner

**Endpoint**
```http
POST /api/v1/owner/register
```

**Parameters**

None

**Request body**
```json
{
  "email": "valid email",
  "password": "string (min length 8)",
  "confirm_password": "string",
  "full_name": "string|null",
  "phone": "string|null"
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "id": "string",
    "email": "email",
    "status": "pending"
  },
  "message": "Account created successfully.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 400 | PASSWORD_MISMATCH | Password và confirm password không khớp. |
| 400 | WEAK_PASSWORD | Password không đạt min length/regex strength. |
| 400 | EMAIL_ALREADY_REGISTERED | Email trùng Owner hoặc contact email của live organization; hoặc insert vi phạm unique index. |
| 400 | PHONE_ALREADY_REGISTERED | Phone trùng Owner hoặc contact phone của live organization. |
| 422 | VALIDATION_ERROR | Body thiếu/sai kiểu, email sai format, hoặc password ngắn hơn 8 ký tự. |
| 500 | EMAIL_SENDING_FAILED | Gửi OTP đăng ký thất bại; Owner vừa tạo bị xóa. |

### verify_otp

**Endpoint**
```http
POST /api/v1/owner/verify-otp
```

**Parameters**

None

**Request body**
```json
{
  "email": "valid email",
  "otp_code": "string (length 4..6)"
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "id": "string",
    "email": "email",
    "status": "active",
    "access_token": "string",
    "refresh_token": "string",
    "token_type": "bearer"
  },
  "message": "Account activated successfully.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 400 | OWNER_ALREADY_ACTIVE | Owner đã có status `active`. |
| 400 | INVALID_OTP | OTP không tồn tại, hết hạn, đã dùng, sai type hoặc sai code; message lấy từ `OtpError`. |
| 404 | OWNER_NOT_FOUND | Không tìm thấy Owner theo email. |
| 422 | VALIDATION_ERROR | Email sai format, body thiếu/sai kiểu, hoặc `otp_code` không dài 4..6 ký tự. |

## Google OAuth

### login_owner_with_google

**Endpoint**
```http
POST /api/v1/owner/auth/google
```

**Parameters**

None

**Request body**
```json
{
  "credential": "string (min length 1)"
}
```

Model cấm field thừa.

**Response**
```json
{
  "success": true,
  "data": {
    "access_token": "string",
    "token_type": "bearer",
    "refresh_token": "string",
    "owner_id": "string",
    "email": "email",
    "full_name": "string|null"
  },
  "message": "Logged in successfully.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_GOOGLE_TOKEN | Google credential sai/hết hạn, verify thất bại, hoặc provider không được hỗ trợ. |
| 403 | GOOGLE_EMAIL_NOT_VERIFIED | Google identity báo email chưa verified. |
| 403 | INACTIVE_ACCOUNT | Owner tìm được/tạo được nhưng status không phải `active`. |
| 409 | GOOGLE_ACCOUNT_MISMATCH | Email/Google subject/provider không khớp account, gồm conflict khi concurrent insert. |
| 409 | PASSWORD_ACCOUNT_OAUTH_LOGIN_NOT_ALLOWED | Email đã thuộc account đăng nhập bằng password. |
| 422 | VALIDATION_ERROR | Thiếu credential, credential rỗng/sai kiểu, hoặc có field thừa. |
| 503 | GOOGLE_OAUTH_UNAVAILABLE | Google OAuth chưa cấu hình. |

### google_oauth_qa_test_page

**Endpoint**
```http
GET /api/v1/owner/auth/google/test
```

**Parameters**

None

**Request body**
```json
None
```

**Response**
```json
"HTMLResponse rendered from owner/templates/google_oauth_qa.html"
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 404 | HTTP_404 | `ENV` không thuộc `local`, `development`, `test`. |
| 503 | HTTP_503 | Thiếu `GOOGLE_CLIENT_ID`. |

# Dùng chung

## Auth — Owner / Issuer / Verifier

### login

**Endpoint**
```http
POST /api/v1/auth/login
```

**Parameters**

None

**Request body**
```json
{
  "email": "string",
  "password": "string",
  "sendingemail": "boolean (default true)"
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "otp_token": "string",
    "message": "Please verify the OTP code sent to your email to complete login.",
    "role": "string|null"
  },
  "message": "Verification OTP sent to your email.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_CREDENTIALS | Password sai. |
| 404 | ACCOUNT_NOT_FOUND | Không tìm thấy Owner lẫn InstitutionAccount theo email. |
| 403 | INACTIVE_ACCOUNT | Account không active; Owner còn pending/locked; hoặc organization/contact email liên kết InstitutionAccount không tồn tại. |
| 409 | GOOGLE_ACCOUNT_PASSWORD_LOGIN_NOT_ALLOWED | Owner được đăng ký qua Google nhưng dùng password login. |
| 422 | VALIDATION_ERROR | Body thiếu field hoặc sai kiểu. |
| 500 | INTERNAL_SERVER_ERROR | Mailer ném `EmailDeliveryError`/`EmailTemplateError` khi gửi OTP và lỗi không được translate. |

### verify_login_otp

**Endpoint**
```http
POST /api/v1/auth/login/verify-otp
```

**Parameters**

None

**Request body**
```json
{
  "otp_token": "string",
  "otp_code": "string"
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "access_token": "string",
    "token_type": "bearer",
    "refresh_token": "string",
    "owner_id": "string",
    "email": "string"
  },
  "message": "Logged in successfully.",
  "error_code": null
}
```

Field `owner_id` vẫn được dùng cho cả InstitutionAccount theo response model hiện tại.

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 400 | INVALID_OTP | OTP sai, hết hạn, đã dùng, không tồn tại, hoặc sai type. |
| 401 | HTTP_401 | Temp token sai/hết hạn hoặc sai `purpose`; lỗi đến từ `HTTPException` và global handler tạo code này. |
| 401 | INVALID_CREDENTIALS | Token decode ra actor id nhưng không tìm thấy Owner/InstitutionAccount. |
| 422 | VALIDATION_ERROR | Body thiếu field hoặc sai kiểu. |

### resend_otp

**Endpoint**
```http
POST /api/v1/auth/resend-otp
```

**Parameters**

None

**Request body**
```json
{
  "email": "string|null",
  "token": "string|null"
}
```

**Response**
```json
{
  "success": true,
  "data": null,
  "message": "OTP resent successfully.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 403 | INACTIVE_ACCOUNT | Owner có status khác `pending` và `active`. |
| 404 | ACCOUNT_NOT_FOUND | Không suy ra được email từ invite token, hoặc không tìm thấy Owner/InstitutionAccount. |
| 422 | VALIDATION_ERROR | Cả `email` và `token` đều thiếu/rỗng, hoặc body sai schema. |
| 500 | INTERNAL_SERVER_ERROR | Mailer ném lỗi khi gửi OTP và lỗi không được translate. |

## Auth — mọi actor có session

### refresh_access_token

**Endpoint**
```http
POST /api/v1/auth/refresh
```

**Parameters**

None

**Request body**
```json
{
  "refresh_token": "string (min length 1)"
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "access_token": "string",
    "token_type": "bearer"
  },
  "message": "Access token refreshed successfully.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_REFRESH_TOKEN | Không tìm thấy session active khớp hash refresh token. |
| 401 | EXPIRED_REFRESH_TOKEN | Session tìm thấy nhưng `expires_at` đã qua; session bị chuyển sang `expired`. |
| 422 | VALIDATION_ERROR | Thiếu/sai kiểu hoặc refresh token rỗng. |

### refresh_access_token

**Endpoint**
```http
POST /api/v1/auth/refresh-token
```

**Parameters**

None

**Request body**
```json
{
  "refresh_token": "string (min length 1)"
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "access_token": "string",
    "token_type": "bearer"
  },
  "message": "Access token refreshed successfully.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | INVALID_REFRESH_TOKEN | Không tìm thấy session active khớp hash refresh token. |
| 401 | EXPIRED_REFRESH_TOKEN | Session tìm thấy nhưng `expires_at` đã qua; session bị chuyển sang `expired`. |
| 422 | VALIDATION_ERROR | Thiếu/sai kiểu hoặc refresh token rỗng. |

### get_me

**Endpoint**
```http
GET /api/v1/auth/me
```

**Parameters**

None

**Request body**
```json
None
```

**Response**
```json
{
  "success": true,
  "data": {
    "actor_type": "string",
    "actor_id": "string",
    "email": "string|null",
    "username": "string|null",
    "full_name": "string|null",
    "role": "string|null",
    "status": "string|null",
    "org_id": "string|null",
    "organization_name": "string|null",
    "twofa_enabled": "boolean|null",
    "totp_reset_requested": "boolean|null",
    "totp_reset_requested_at": "datetime|null",
    "password_reset_requested": "boolean|null",
    "password_reset_requested_at": "datetime|null",
    "details": "object|null"
  },
  "message": "Profile fetched successfully.",
  "error_code": null
}
```

`details` được serializer tạo theo actor: Admin có `twofa_method`; Owner có `phone`, `avatar_url`, `dob`, `oauth_provider`; InstitutionAccount có `organization_type`, `organization_status`, `twofa_method`.

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 401 | UNAUTHORIZED | Thiếu/sai token; token thiếu actor/session; session không active/hết hạn/sai actor; actor không tồn tại; Admin chưa verify TOTP/không active; hoặc actor type không hỗ trợ. |

## Operations

### health_check

**Endpoint**
```http
GET /health
```

**Parameters**

None

**Request body**
```json
None
```

**Response**
```json
{
  "success": true,
  "data": {"status": "ok"},
  "message": "Lucidex API is healthy.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| — | — | None |

## Debug / Testing

### delete_user_debug

**Endpoint**
```http
POST /api/v1/debug/delete-user
```

**Parameters**

None

**Request body**
```json
{
  "email": "valid email"
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "deleted_owners": "integer",
    "deleted_institution_accounts": "integer",
    "deleted_organizations": "integer",
    "deleted_invites": "integer",
    "deleted_sessions": "integer",
    "deleted_otps": "integer"
  },
  "message": "User with email '<input email>' has been completely deleted.",
  "error_code": null
}
```

**List Error**
| HTTP | Mã lỗi | Trường hợp |
|---|---|---|
| 422 | VALIDATION_ERROR | Body thiếu email, sai kiểu hoặc email sai format. |
