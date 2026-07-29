# API Structure by Role

Base URL:

```text
/api/v1
```

Đây là cấu trúc folder đề xuất cho Postman/Bruno và tài liệu API. API dùng
chung được đặt lại trong từng role để Frontend dễ tìm theo portal.

## 1. SUPER ADMIN

### 1.1 Auth

| Tên API | Method | Endpoint |
|---|---|---|
| Login | `POST` | `/api/v1/admin/auth/login` |
| Verify TOTP lần đầu | `POST` | `/api/v1/admin/auth/totp/setup/verify` |
| Verify TOTP khi đăng nhập | `POST` | `/api/v1/admin/auth/totp/login/verify` |
| Get my profile | `GET` | `/api/v1/auth/me` |

### 1.2 Organization Review

| Tên API | Method | Endpoint |
|---|---|---|
| List organizations | `GET` | `/api/v1/admin/organizations/list` |
| Approve organization | `POST` | `/api/v1/admin/organizations/{organization_id}/approve` |
| Reject organization | `POST` | `/api/v1/admin/organizations/{organization_id}/reject` |

API list hỗ trợ query:

```text
type=issuer|verifier
status=pending_review|approved|rejected
```

### 1.3 Admin Account CRUD

| Tên API | Method | Endpoint |
|---|---|---|
| Create Admin | `POST` | `/api/v1/admin/accounts` |
| List Admins | `GET` | `/api/v1/admin/accounts` |
| Get Admin detail | `GET` | `/api/v1/admin/accounts/{id}` |
| Update Admin | `PUT` | `/api/v1/admin/accounts/{id}` |
| Delete Admin | `DELETE` | `/api/v1/admin/accounts/{id}` |

### 1.4 Admin Reset Request Management

| Tên API | Method | Endpoint |
|---|---|---|
| List pending reset requests | `GET` | `/api/v1/admin/accounts/requests` |
| Approve password reset | `POST` | `/api/v1/admin/accounts/{id}/reset-password` |
| Approve TOTP/2FA reset | `POST` | `/api/v1/admin/accounts/{id}/reset-2fa` |
| Reject password reset | `POST` | `/api/v1/admin/accounts/{id}/reject-reset-password` |
| Reject TOTP/2FA reset | `POST` | `/api/v1/admin/accounts/{id}/reject-reset-totp` |

### 1.5 Health

| Tên API | Method | Endpoint |
|---|---|---|
| Admin health | `GET` | `/api/v1/admin/health` |

---

## 2. ADMIN (OPERATIONS ADMIN)

### 2.1 Auth

| Tên API | Method | Endpoint |
|---|---|---|
| Login | `POST` | `/api/v1/admin/auth/login` |
| Verify TOTP lần đầu | `POST` | `/api/v1/admin/auth/totp/setup/verify` |
| Verify TOTP khi đăng nhập | `POST` | `/api/v1/admin/auth/totp/login/verify` |
| Get my profile | `GET` | `/api/v1/auth/me` |

### 2.2 Organization Review

| Tên API | Method | Endpoint |
|---|---|---|
| List organizations | `GET` | `/api/v1/admin/organizations/list` |
| Approve organization | `POST` | `/api/v1/admin/organizations/{organization_id}/approve` |
| Reject organization | `POST` | `/api/v1/admin/organizations/{organization_id}/reject` |

### 2.3 My Reset Requests

| Tên API | Method | Endpoint |
|---|---|---|
| Get my request status | `GET` | `/api/v1/admin/accounts/request-status` |
| Request password reset | `POST` | `/api/v1/admin/accounts/request-reset-password` |
| Request TOTP/2FA reset | `POST` | `/api/v1/admin/accounts/request-reset-totp` |

### 2.4 Health

| Tên API | Method | Endpoint |
|---|---|---|
| Admin health | `GET` | `/api/v1/admin/health` |

> Operations Admin không có quyền CRUD tài khoản Admin hoặc xử lý reset request
> của Admin khác.

---

## 3. ISSUER

### 3.1 Registration

| Tên API | Method | Endpoint |
|---|---|---|
| Register Issuer organization | `POST` | `/api/v1/issuer/register` |

### 3.2 Invitation & Account Activation

| Tên API | Method | Endpoint |
|---|---|---|
| Set password from invitation | `POST` | `/api/v1/issuer/invites/password` |
| Verify activation OTP | `POST` | `/api/v1/issuer/invites/verify-otp` |

### 3.3 Auth & Session

| Tên API | Method | Endpoint |
|---|---|---|
| Login | `POST` | `/api/v1/auth/login` |
| Verify login OTP | `POST` | `/api/v1/auth/login/verify-otp` |
| Resend OTP | `POST` | `/api/v1/auth/resend-otp` |
| Refresh access token | `POST` | `/api/v1/auth/refresh` |
| Get my profile | `GET` | `/api/v1/auth/me` |

### 3.4 Health

| Tên API | Method | Endpoint |
|---|---|---|
| Issuer health | `GET` | `/api/v1/issuer/health` |

---

## 4. VERIFIER

### 4.1 Registration

| Tên API | Method | Endpoint |
|---|---|---|
| Register Verifier organization | `POST` | `/api/v1/verifier/register` |

### 4.2 Invitation & Account Activation

| Tên API | Method | Endpoint |
|---|---|---|
| Set password from invitation | `POST` | `/api/v1/verifier/invites/password` |
| Verify activation OTP | `POST` | `/api/v1/verifier/invites/verify-otp` |

### 4.3 Auth & Session

| Tên API | Method | Endpoint |
|---|---|---|
| Login | `POST` | `/api/v1/auth/login` |
| Verify login OTP | `POST` | `/api/v1/auth/login/verify-otp` |
| Resend OTP | `POST` | `/api/v1/auth/resend-otp` |
| Refresh access token | `POST` | `/api/v1/auth/refresh` |
| Get my profile | `GET` | `/api/v1/auth/me` |

### 4.4 Health

| Tên API | Method | Endpoint |
|---|---|---|
| Verifier health | `GET` | `/api/v1/verifier/health` |

---

## 5. OWNER

### 5.1 Registration

| Tên API | Method | Endpoint |
|---|---|---|
| Register Owner | `POST` | `/api/v1/owner/register` |
| Verify registration OTP | `POST` | `/api/v1/owner/verify-otp` |

### 5.2 Password Auth

| Tên API | Method | Endpoint |
|---|---|---|
| Login | `POST` | `/api/v1/auth/login` |
| Verify login OTP | `POST` | `/api/v1/auth/login/verify-otp` |
| Resend OTP | `POST` | `/api/v1/auth/resend-otp` |

### 5.3 Google Auth

| Tên API | Method | Endpoint |
|---|---|---|
| Login/Register with Google | `POST` | `/api/v1/owner/auth/google` |

### 5.4 Session & Profile

| Tên API | Method | Endpoint |
|---|---|---|
| Refresh access token | `POST` | `/api/v1/auth/refresh` |
| Get my profile | `GET` | `/api/v1/auth/me` |

### 5.5 Health

| Tên API | Method | Endpoint |
|---|---|---|
| Owner health | `GET` | `/api/v1/owner/health` |

---

## 6. OTHER

### 6.1 System

| Tên API | Method | Endpoint |
|---|---|---|
| System health | `GET` | `/health` |
| Swagger UI | `GET` | `/docs` |
| OpenAPI schema | `GET` | `/openapi.json` |

### 6.2 Debug / Testing

| Tên API | Method | Endpoint |
|---|---|---|
| Delete test user data | `POST` | `/api/v1/debug/delete-user` |
| Open Google OAuth QA page | `GET` | `/api/v1/owner/auth/google/test` |

> Nhóm Debug/Testing chỉ nên bật trong môi trường development hoặc QA, không nên
> public trên production.

---

## Cây folder rút gọn

```text
SUPER ADMIN
├── Auth
├── Organization Review
├── Admin Account CRUD
├── Admin Reset Request Management
└── Health

ADMIN
├── Auth
├── Organization Review
├── My Reset Requests
└── Health

ISSUER
├── Registration
├── Invitation & Account Activation
├── Auth & Session
└── Health

VERIFIER
├── Registration
├── Invitation & Account Activation
├── Auth & Session
└── Health

OWNER
├── Registration
├── Password Auth
├── Google Auth
├── Session & Profile
└── Health

OTHER
├── System
└── Debug / Testing
```
