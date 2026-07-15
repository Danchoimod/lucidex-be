# LUCIDEX — Database Schema Tổng Hợp (MongoDB / Beanie ODM / Pydantic v2)

Pilot 90 ngày — FastAPI + MongoDB. Tài liệu này tổng hợp toàn bộ 16 collection, quan hệ, state machine theo luồng nghiệp vụ, session/RBAC, phân trang, dọn dẹp dữ liệu, và index chiến lược.

> **Trạng thái tài liệu:** đã xử lý toàn bộ các điểm yếu được chỉ ra ở lần đánh giá trước (unique index, luồng per_request, lịch sử eKYC, tách field verifier, độ ưu tiên index). Chỉ còn 1 mục thật sự treo do AC nghiệp vụ chưa chốt — xem mục 9.

---

## MỤC LỤC
1. Sơ đồ tổng thể quan hệ
2. Chi tiết từng Collection
3. Session & Auth
4. RBAC
5. Bảng tổng hợp Index
6. Ghi chú kiến trúc (điểm nghẽn & atomicity)
7. Phân trang cho danh sách lớn
8. Vòng đời & dọn dẹp dữ liệu vận hành
9. Các điểm còn treo (Open Items)

---

## 1. SƠ ĐỒ TỔNG THỂ QUAN HỆ

```
organizations (issuer/verifier) ──1:1──> institution_accounts
organizations ──1:N──> credentials (issuer_org_id)
organizations ──1:N──> access_records (verifier_org_id)
organizations ──1:N──> trusted_organizations (org_id)

owners ──1:N──> credentials (owner_id, sau khi claimed)
owners ──1:N──> claims (owner_id)
owners ──1:N──> verified_links (owner_id)
owners ──1:N──> trusted_organizations (owner_id)
owners ──1:N──> notifications (owner_id)
owners ──1:N──> sessions (actor_id)

credentials ──1:N──> claims (credential_id)
credentials ──(denormalize issuer_org_id)──> claims (Review Queue scoping, xem 2.6)
credentials ──1:N──> verified_links (credential_id)

owners ──1:N──> ekyc_capture_sessions (owner_id)
claims ──1:N──> ekyc_capture_sessions (claim_id)

csv_upload_jobs ──1:N──> csv_upload_rows (job_id)
csv_upload_rows ──(on success)──> credentials (denormalized, không FK cứng)

verified_links ──1:N──> access_records (link_id)

platform_admins ──1:N──> sessions (actor_id)

audit_logs: ghi nhận từ mọi actor, không có FK ràng buộc cứng (immutable, append-only)
otp_codes: dùng chung, tham chiếu polymorphic (subject_type + subject_id)
```

**Nguyên tắc Reference vs Embed:**
- **Reference (ObjectId)** là mặc định — phục vụ filter/search/join độc lập của Admin, Issuer, Verifier, Owner.
- **Embed** chỉ dùng cho dữ liệu nhỏ, bounded, luôn đọc kèm entity cha, không cần query riêng: `owners.consent_settings`, `claims.ekyc_attempts`, `organizations.documents[]`.

---

## 2. CHI TIẾT TỪNG COLLECTION

### 2.1 `organizations`
Hồ sơ đăng ký + profile Issuer/Verifier (gộp chung, phân biệt qua `type`).

```
{
  _id,
  type: "issuer" | "verifier",
  status: "pending_review" | "approved" | "rejected",
  name, tax_code, address, legal_rep_name,
  contact_email, contact_phone,
  registrant_name, registrant_title,           // registrant_title chỉ bắt buộc với verifier
  documents: [{ name, url, type }],             // business license, authorization letter
  rejection_reason, reviewed_by, reviewed_at,
  invite_token, invite_token_used: bool,
  account_status: "active" | "locked",          // trạng thái vận hành sau khi approved
  lock_reason, locked_by, locked_at,

  verifier_profile: {                           // chỉ tồn tại khi type = "verifier"
    plan: {                                      // ⚠ PLACEHOLDER — US 3.6/3.7 chưa chốt AC
      tier, monthly_quota, quota_used, reset_at  //   cấu trúc tối thiểu để không block code
    }                                            //   các luồng khác, cần review khi AC chốt
  }
}
```

> Field đặc thù của từng loại tổ chức (hiện chỉ có `plan` cho verifier) được gom vào `verifier_profile` thay vì để phẳng ở root — tránh sparse field khi Issuer/Verifier phân kỳ thêm field theo thời gian, nhưng vẫn giữ 1 collection chung để Admin (US 4.1–4.5) query/filter cả 2 loại cùng lúc mà không cần join.

### 2.2 `institution_accounts`
Tài khoản đăng nhập của Issuer Admin / Verifier Admin.

```
{
  _id, org_id (FK -> organizations),
  username, password_hash,
  twofa_method: "email" | "sms", twofa_enabled: bool,
  status: "active" | "locked"                    // đồng bộ với organizations.account_status
}
```

> **1 account / 1 tổ chức** (AC US 3.1 "One account per Verifier"): chặn qua `invite_token_used` (invite link chỉ dùng được 1 lần) — không thêm `unique(org_id)` ở tầng DB vì sẽ chặn luôn khả năng mở rộng multi-user per organization sau này (Open Items #2), trong khi AC hiện tại chưa yêu cầu ràng buộc cứng ở DB, chỉ cần đúng hành vi nghiệp vụ.

### 2.3 `platform_admins`
Tài khoản Admin TIC.

```
{
  _id, username, password_hash,
  twofa_method, twofa_enabled: bool,
  status: "active" | "locked"
}
```

### 2.4 `owners`
Tài khoản Credential Owner (sinh viên).

```
{
  _id, email,
  password_hash,                                 // null nếu đăng ký qua OAuth
  oauth_provider, oauth_subject_id,              // null nếu đăng ký email/pass
  full_name, phone, avatar_url, dob,
  status: "active" | "locked_migrated" | "soft_deleted",
  consent_settings: {
    default_type: "one_time"|"per_request"|"org_level"|"time_bound",
    default_org_id, default_duration
  },
  deleted_at, purge_after, restored_at            // soft-delete 30 ngày
}
```

### 2.5 `credentials`
Entity trung tâm — văn bằng số hóa.

```
{
  _id, issuer_org_id (FK -> organizations),
  student_id, full_name, dob, major,
  graduation_year, classification,
  university_email, national_id_hash,            // SHA-256, không lưu số thô
  phone,
  status: "unclaimed" | "claimed" | "revoked",
  unclaimed_reason_code: "AWAITING_CLAIM" | "CLAIM_REJECTED",
  owner_id: FK -> owners | null,
  claim_method: "university_email" | "national_id" | null,
  claimed_at, unclaimed_at,
  revoked_reason, revoked_by, revoked_at,
  deleted_at, purge_after, restored_at            // soft-delete 3 ngày (item-level)
}
```

### 2.6 `claims`
Từng lần yêu cầu nhận bằng.

```
{
  _id, owner_id (FK -> owners), credential_id (FK -> credentials),
  issuer_org_id (FK -> organizations),                // denormalized từ credential_id, để Issuer Review Queue
                                                       // (US 1.6) lọc trực tiếp theo tenant, không cần join
                                                       // mỗi lần truy vấn (đúng nguyên tắc tenant-scoping mục 4)
  method: "university_email" | "cccd_ekyc",
  status: "otp_pending" | "pending_review" | "approved" | "rejected" | "needs_info",
  ekyc_attempts: [{                                 // MỘT phần tử mỗi lần "Scan Again"/"Confirm"
    attempt_no: int,
    ocr_score, face_match_score, liveness_passed: bool,
    national_id_hash, combined_score,
    outcome: "auto_approved" | "low_confidence" | "unreadable_image" | "liveness_failed",
    attempted_at
  }],                                                // KHÔNG chứa ảnh gốc — xóa RAM/Disk ngay sau mỗi lần
  scan_retry_count: int,                             // = len(ekyc_attempts) - 1, giới hạn 3 lần "Scan Again"
  rejection_reason, reviewed_by, reviewed_at,
  migrated_from_owner_id: FK -> owners | null,        // đánh dấu kết quả "cướp quyền/migration"
  queue_entered_at: datetime | null                   // set khi status chuyển sang pending_review,
                                                       // dùng để sort "oldest first" đúng AC US 1.6
                                                       // thay vì dựa vào updated_at (dễ bị lệch khi
                                                       // claim quay lại queue sau "needs_info")
}
```

> Đổi từ 1 object `ekyc_result` sang mảng `ekyc_attempts`: mỗi lần "Scan Again" (tối đa 3 lần theo AC) tạo 1 phần tử mới thay vì ghi đè — giữ được lịch sử đầy đủ để tra soát khi có khiếu nại claim bị từ chối oan. Mảng này bounded tuyệt đối (≤4 phần tử theo giới hạn retry của AC) nên embed an toàn, không cần tách collection riêng.

> **Về "Review Queue" (US 1.6):** không tách thành collection riêng — queue chỉ là **view** của `claims` với `status: "pending_review"`, sort theo `queue_entered_at`. Lý do không tách: queue không có dữ liệu độc lập, không có lifecycle riêng ngoài `claims`, tách ra sẽ phải đồng bộ 2 nơi. Nếu sau pilot cần thêm field riêng cho vận hành queue (vd. `assigned_to`, `priority`, SLA) thì bổ sung trực tiếp vào `claims`, chưa cần tách bảng.

### 2.7 `csv_upload_jobs`
Metadata 1 lần upload CSV.

```
{
  _id, org_id (FK -> organizations), filename,
  total_rows, valid_count, error_count, created_count,
  status: "validating" | "awaiting_confirmation" | "processing" | "completed" | "failed",
  overwrite_all: bool
}
```

### 2.8 `csv_upload_rows`
Từng dòng dữ liệu (tách riêng khỏi job để tránh vượt giới hạn 16MB BSON và cho phép resume).

```
{
  _id, job_id (FK -> csv_upload_jobs), seq_no,
  student_id, raw_payload,
  validation_status: "valid" | "invalid" | "duplicate_pending" | "resolved",
  error_reason,                                     // STT, Student ID, reason cho error list
  resolution: "overwrite" | "skip" | null,
  processing_status: "queued" | "created" | "failed"
}
```

### 2.9 `verified_links`
Link chia sẻ + cấu hình consent.

```
{
  _id, owner_id (FK -> owners), credential_id (FK -> credentials),
  consent_type: "one_time" | "per_request" | "org_level" | "time_bound",
  bound_org_id: FK -> organizations | null,          // bắt buộc nếu org_level
  duration: "24h" | "7d" | "30d" | "permanent" | null, // bắt buộc nếu time_bound
  otp_hash, expires_at,
  status: "active" | "expired" | "revoked",
  view_count: int
}
```

### 2.10 `access_records`
Lịch sử xem/từ chối qua Verified Link (structured, phục vụ dashboard & audit của Owner/Verifier).

```
{
  _id, link_id (FK -> verified_links),
  owner_id (FK -> owners),                             // denormalized từ verified_links, tránh join khi query "pending requests của tôi"
  verifier_org_id (FK -> organizations),
  credential_id (FK -> credentials),
  result: "pending" | "verified" | "denied",          // "pending" chỉ dùng cho consent_type = per_request
  deny_reason,                                         // "expired" | "revoked" | "otp_invalid" | "owner_declined"
  consent_type_snapshot,                               // chụp lại tại thời điểm xem
  requested_at,                                        // thời điểm Verifier bấm xem (mọi consent_type)
  decided_at, decided_by,                               // chỉ set khi per_request: thời điểm & ai duyệt (owner)
  viewed_at                                             // chỉ set khi result chuyển "verified" và dữ liệu đã trả về
}
```

> **Xử lý luồng `per_request` (US 2.8):** khi Verifier mở link với consent_type = `per_request`, hệ thống tạo ngay 1 `access_records` với `result: "pending"` (thay vì chờ có kết quả mới ghi) — đây chính là "chỗ lưu request đang chờ duyệt" mà thiết kế trước còn thiếu. Owner poll hoặc nhận real-time (qua `notifications`, thêm type `access_request_pending`) danh sách các bản ghi `result: "pending"` của mình để Approve/Decline. Verifier client polling theo `_id` để biết khi nào `result` chuyển từ `pending` sang `verified`/`denied` rồi mới trả dữ liệu về UI. `owner_id` đã denormalize sẵn ở field trên nên query "pending requests của tôi" (`{owner_id, result: "pending"}`) không cần join.

### 2.11 `trusted_organizations`
Bảng nối Owner ⇄ Organization.

```
{ _id, owner_id (FK -> owners), org_id (FK -> organizations), added_at }
```

### 2.12 `notifications`
Notification Center của Owner.

```
{
  _id, owner_id (FK -> owners),
  type: "claim_submitted" | "claim_review" | "claim_approved" | "claim_rejected"
      | "link_viewed" | "access_denied" | "access_request_pending",   // request per_request đang chờ duyệt
  message, related_entity_id, related_entity_type,
  is_read: bool, created_at
}
```

### 2.13 `audit_logs`
Nhật ký bất biến toàn hệ thống.

```
{
  _id,
  actor_type: "issuer" | "owner" | "verifier" | "admin",
  actor_id, action_type,                              // enum theo bảng chuẩn 4.6
  detail: string,                                      // plain-text, mask email, KHÔNG chứa OTP/password/CCCD thô
  timestamp
}
```

### 2.14 `otp_codes`
Dùng chung cho mọi luồng OTP (login 2FA, register, claim, forgot-password, link-access).

```
{
  _id,
  subject_type: "owner" | "institution_account" | "verified_link" | "pending_registration",
  subject_id,
  purpose: "2fa_login" | "register" | "claim_email" | "password_reset" | "link_access",
  code_hash, channel: "email" | "sms",
  attempts: int, max_attempts: int,
  expires_at, used: bool
}
```

### 2.15 `sessions`
Quản lý phiên đăng nhập (xem chi tiết mục 3).

```
{
  _id, actor_type: "owner" | "institution_account" | "platform_admin",
  actor_id, org_id: FK | null,
  refresh_token_hash,
  device_info: { user_agent, ip },
  status: "active" | "revoked",
  twofa_verified: bool,
  issued_at, last_used_at, expires_at,
  revoked_at, revoked_reason
}
```

### 2.16 `ekyc_capture_sessions` (bổ sung sau — phục vụ luồng QR handoff chụp CCCD, ngoài phạm vi AC gốc)

Không có trong thiết kế ban đầu — thêm khi quyết định luồng chụp CCCD chuyển sang điện thoại qua QR code thay vì chụp trực tiếp trên desktop.

```
{
  _id, owner_id (FK -> owners), claim_id (FK -> claims),
  token,                                    # random ≥128-bit, dùng trong URL QR, không hiển thị cho user đọc như OTP
  status: "pending" | "submitted" | "processing" | "completed" | "expired",
  expires_at,                               # TTL ngắn, mặc định 10 phút
  outcome: "auto_approved" | "low_confidence" | "unreadable_image" | "liveness_failed" | null
}
```

- **Index**: `unique(token)`, TTL index trên `expires_at`.
- **Không cần soft-delete/cron purge** như các entity khác — đây không phải dữ liệu compliance (ảnh CCCD không được lưu vào đây, chỉ lưu trạng thái phiên), TTL index thuần là đủ.
- **"Link tự hủy sau khi submit"**: dùng đúng pattern atomic conditional update đã áp dụng cho `invite_token_used` (mục 6) — `find_one_and_update(token=token, status="pending")` → set `status="submitted"`, không phải xóa document.

---

## 3. SESSION & AUTH

- **Access token (JWT)**: TTL 10–15 phút, payload `{sub, actor_type, org_id, session_id, exp}` — verify chữ ký, không tra DB mỗi request (đáp ứng yêu cầu "<2 giây" của luồng verify).
- **Refresh token**: TTL 7–30 ngày, lưu hash trong `sessions`, **rotate mỗi lần dùng**.
- **Revoke gần-tức-thời**: Lock account → set `status: locked` trên `organizations`/`institution_accounts` + revoke toàn bộ `sessions` liên quan → access token cũ tự hết hiệu lực trong ≤15 phút (không refresh được).
- **Revoke tuyệt đối tức thời** (nếu cần): thêm Redis blocklist theo `actor_id`, check ở middleware trước khi verify JWT — không bắt buộc cho pilot 90 ngày nhưng nên chừa sẵn field.
- **2FA flow tách 2 bước**: `pending_2fa_token` (JWT riêng, TTL 5 phút, không gọi được API nghiệp vụ) → verify OTP → mới tạo `sessions` thật.
- **Verified Link revoke** không phụ thuộc session — check trực tiếp `verified_links.status` mỗi lần truy cập, nên tự nhiên tức thời.

---

## 4. RBAC

Đơn giản hoá còn **2 tầng** (đã bỏ tầng permission/`roles` — xem lý do ở dưới):

- **Tầng 1 — Actor type**: `owner` / `institution_account` (issuer|verifier qua `organizations.type`) / `platform_admin` — chặn ở router middleware. Đây cũng chính là căn cứ để route vào đúng giao diện 1 trong 4 portal sau khi đăng nhập.
- **Tầng 2 — Multi-tenancy scoping** (quan trọng nhất, hay bị bỏ sót): mọi query nghiệp vụ **bắt buộc** filter thêm `issuer_org_id == token.org_id` hoặc `verifier_org_id == token.org_id`, không dựa vào client gửi đúng `org_id`. Áp dụng cho `credentials`, `csv_upload_jobs`, `claims`, `access_records`. `platform_admin` không bị scope — thấy toàn bộ dữ liệu.

> **Vì sao không có tầng permission/`roles`**: AC hiện tại mỗi loại account chỉ có đúng 1 vai trò duy nhất — 1 Issuer Admin làm hết mọi việc trong Issuer Portal (upload CSV, duyệt claim, revoke, xem dashboard), không có AC nào mô tả "nhân viên A chỉ được xem, nhân viên B mới được duyệt". Vì vậy **Tầng 1 (actor_type) đã đủ** để quyết định 1 account được làm gì — không cần thêm collection `roles`/`permissions` để giải quyết một nhu cầu chưa tồn tại trong AC. Nếu sau pilot phát sinh nhu cầu phân quyền nhiều cấp trong cùng 1 tổ chức, đây là điểm cần quay lại thiết kế thêm (đã ghi ở Open Items mục 9).

**Pipeline middleware:** Verify JWT → (optional) check blocklist → xác định actor_type từ token → áp org/owner scope filter vào query.

---

## 5. BẢNG TỔNG HỢP INDEX

### 5.1 Unique index bắt buộc (chặn race condition ở tầng DB, không chỉ dựa vào application check)

| Collection | Index | Mục đích |
|---|---|---|
| `owners` | `unique(email)` | Chặn AC "This email is already registered" khi 2 request đăng ký cùng lúc — application-level check không đủ vì có race condition |
| `owners` | `partial unique(oauth_provider, oauth_subject_id)` khi field tồn tại | Chặn 1 tài khoản OAuth tạo trùng nếu callback bị gọi 2 lần |
| `institution_accounts` | `unique(username)` | Chặn trùng username khi setup account qua invite link |
| `platform_admins` | `unique(username)` | Tương tự, cho Admin |
| `organizations` | `partial unique({tax_code, type})` where `status in ["pending_review", "approved"]` | Chặn 2 tổ chức cùng tax_code+type nộp/tồn tại song song ở trạng thái "đang sống", nhưng **không** chặn resubmit sau khi bị reject (US 3.2: document rejected cũ vẫn giữ nguyên, document mới tạo thêm — nếu dùng unique tuyệt đối sẽ tự phá AC này) |
| `verified_links` | `partial unique(otp_hash)` where `status = "active"` | OTP không trùng giữa các link **đang active**; không thể unique tuyệt đối vĩnh viễn vì OTP thường ngắn (numeric, entropy thấp) — theo thời gian, xác suất trùng giữa 1 OTP mới với OTP của 1 link đã `expired`/`revoked` từ lâu là chắc chắn xảy ra, unique tuyệt đối sẽ khiến việc tạo link mới ngẫu nhiên bị insert-fail vô lý |

> Đây là điểm sửa quan trọng nhất so với bản trước — thiếu unique index ở tầng DB nghĩa là AC "email đã đăng ký" chỉ đúng khi không có 2 request chạm gần như đồng thời; với unique index, request thua sẽ nhận lỗi duplicate key và tầng application map lại thành đúng message trong AC. Riêng `organizations` dùng **partial** index (không phải unique tuyệt đối) vì AC resubmit sau reject yêu cầu nhiều document cùng tax_code+type được phép tồn tại song song, miễn là chỉ 1 trong số đó đang ở trạng thái "sống" (`pending_review`/`approved`) tại một thời điểm.

### 5.2 Index truy vấn & hiệu năng

| Collection | Index | Mục đích |
|---|---|---|
| `credentials` | `unique({issuer_org_id, student_id})` | Chặn double-issue, phát hiện trùng khi upload CSV |
| `credentials` | `{national_id_hash: 1}` | Tra cứu eKYC match & migration |
| `credentials` | `{owner_id: 1, status: 1}` | "My Credentials" list |
| `csv_upload_rows` | `{job_id: 1, validation_status: 1}` | Query error list / creation queue |
| `csv_upload_rows` | `{job_id: 1, student_id: 1}` | Check trùng trong batch đang upload |
| `claims` | `{issuer_org_id: 1, status: 1, queue_entered_at: 1}` | Review Queue (US 1.6), sort "oldest first", scoped theo tenant |
| `claims` | `{owner_id: 1, status: 1}` | "Claim của tôi" — Owner xem trạng thái claim đang chờ |
| `claims` | `{credential_id: 1}` | Tra cứu claim theo credential (migration, kiểm tra trùng) |
| `csv_upload_jobs` | `{org_id: 1, status: 1, created_at: -1}` | Resume sau khi restart (US 1.5 "does not need to re-upload"), lịch sử upload của Issuer |
| `verified_links` | `{owner_id: 1, status: 1}` | "My Links" |
| `access_records` | `{link_id: 1, viewed_at: -1}` | Audit log của Owner |
| `access_records` | `{verifier_org_id: 1, viewed_at: -1}` | Dashboard Verifier |
| `audit_logs` | text index trên `detail` (+ compound `actor_type`,`action_type`,`timestamp`) | Full-text search Admin — ⏳ tạo sớm không hại gì (collection rỗng), nhưng giá trị đo lường được chỉ rõ khi volume đủ lớn; không phải ưu tiên tuần đầu |
| `otp_codes` | TTL index trên `expires_at` | Tự dọn OTP hết hạn |
| `ekyc_capture_sessions` | `unique(token)` + TTL index trên `expires_at` | Lookup token nhanh khi mobile submit, tự dọn session hết hạn (mục 2.16) |
| `organizations` | `{status: 1, type: 1, created_at: 1}` | Pending Requests, oldest-first |
| `sessions` | `{refresh_token_hash: 1}` | Lookup khi refresh token |
| `sessions` | `{actor_id: 1, status: 1}` | Revoke hàng loạt khi lock/xóa account |
| `sessions` | TTL index trên `expires_at` | Tự dọn session hết hạn |
| `notifications` | `{owner_id: 1, is_read: 1, created_at: -1}` | Notification Center |
| `trusted_organizations` | `unique({owner_id, org_id})` | Chặn thêm trùng, check org_level consent |
| `access_records` | `{owner_id: 1, result: 1}` | Query "pending requests của tôi" (luồng per_request) |

> **Về mức độ ưu tiên:** bảng 5.1 (unique index) nên có **ngay từ migration script đầu tiên**, trước khi viết endpoint đăng ký. Các index ở 5.2 phần lớn cũng nên tạo sớm (index trên collection rỗng không tốn chi phí), riêng text index trên `audit_logs` là chỗ duy nhất có thể lùi lại nếu cần ưu tiên thời gian, vì lợi ích của nó chỉ rõ ràng khi audit log đã có volume đáng kể để search.

---

## 6. GHI CHÚ KIẾN TRÚC

**Điểm nghẽn CSV 20MB:** so với 100MB thì rủi ro OOM ở tầng đọc file gần như không còn (20MB đọc thẳng vào memory vẫn an toàn cho hầu hết worker), nhưng rủi ro thật sự nằm ở **số lượng dòng**, không phải dung lượng file — 20MB CSV vẫn có thể chứa 50.000–100.000 dòng sinh viên. Vì vậy vẫn giữ nguyên kiến trúc: tách `csv_upload_rows` khỏi `csv_upload_jobs` (một job với vài chục nghìn dòng error/queue chắc chắn vượt giới hạn 16MB/document nếu nhét chung), insert theo batch (`insertMany` unordered, 500–1000 dòng/batch), hash national_id ngay khi đọc dòng (Zero-Retention). File gốc có thể đọc gọn một lần rồi parse (không bắt buộc stream theo chunk như file 100MB), nhưng **ghi kết quả xuống `csv_upload_rows` vẫn nên theo batch** để tránh nghẽn khi insert số lượng lớn document cùng lúc. Resume dựa vào trạng thái đã persist trong `csv_upload_rows`, không cần giữ queue trong RAM.

**Atomicity cho luồng eKYC migration:** dùng MongoDB **multi-document transaction** (yêu cầu chạy trên replica set, kể cả 1-node RS cho dev/pilot — standalone `mongod` không hỗ trợ). Transaction gồm: update `credentials.owner_id` sang owner mới, set `owners(cũ).status = locked_migrated`, revoke `verified_links` cũ liên quan, ghi `audit_logs` — tất cả trong 1 session transaction với `read_concern="snapshot"`, `write_concern="majority"`. Gọi API eKYC provider (FPT.AI hoặc mock, xem `lucidex_master_prompt.md` mục 2) phải hoàn tất **trước khi** mở transaction; transaction chỉ chứa write vào Mongo, có retry logic cho `TransientTransactionError`.

**Race condition khi 2 claim cùng migrate 1 credential:** nếu owner cũ và một request khác (hoặc chính owner cũ thao tác song song trên 2 thiết bị) cùng lúc trigger migration trên cùng `national_id_hash`, có nguy cơ 2 transaction cùng đọc `credentials.owner_id` ở trạng thái cũ rồi cùng ghi đè. Chặn bằng:
- Update `credentials.owner_id` trong transaction dùng **điều kiện so khớp giá trị cũ** (`find_one_and_update` với filter bao gồm `owner_id: <old_owner_id>` đã đọc được, không update mù) — nếu giá trị đã đổi (do transaction khác thắng trước), thao tác trả về 0 document match → transaction hiện tại abort và trả lỗi "credential đã được xử lý", để client retry hoặc báo lỗi rõ ràng thay vì ghi đè âm thầm.
- `read_concern="snapshot"` đã đảm bảo transaction không đọc dữ liệu đang bị transaction khác sửa dở, nhưng **không tự động chặn** 2 transaction cùng bắt đầu gần như đồng thời — điều kiện so khớp ở trên mới là cơ chế chặn thật sự (optimistic concurrency).

**Soft-delete:** dùng field chuẩn `deleted_at` / `purge_after` / `restored_at` trên các collection cần (`credentials`, `verified_links`, `owners`, `organizations`), xử lý hard-purge bằng **cron job** (không dùng TTL index tự động) để có thể ghi audit log trước khi xóa vĩnh viễn.

---

## 7. PHÂN TRANG CHO DANH SÁCH LỚN

Các danh sách có thể tăng không giới hạn theo thời gian: `audit_logs` (mọi action toàn hệ thống), `credentials` (Display History của Issuer), `access_records` (Audit Log của Owner/Verifier). Offset-based pagination (`skip`/`limit`) sẽ chậm dần khi offset lớn vì MongoDB vẫn phải duyệt qua toàn bộ document bị skip.

**Chiến lược:**
- Dùng **cursor-based pagination** (keyset) thay vì `skip`: sort theo `{_id: -1}` hoặc `{created_at: -1, _id: -1}` (compound để tránh trùng khi 2 document cùng timestamp), client gửi lên `last_seen_id` của trang trước, query `{_id: {$lt: last_seen_id}}`.
- Áp dụng bắt buộc cho: `audit_logs`, `access_records`, `credentials` (Display History), `notifications`.
- `trusted_organizations` (US 2.9 đã có AC "phân trang 10 mục/trang") dùng offset-based cũng chấp nhận được vì per-owner list hiếm khi vượt vài trăm bản ghi — không cần cursor.
- Index phục vụ cursor: các index đã liệt kê ở mục 5 (vd. `{owner_id: 1, created_at: -1}` cho `notifications`) đã đủ hỗ trợ cursor pagination, không cần thêm index riêng.

---

## 8. VÒNG ĐỜI & DỌN DẸP DỮ LIỆU VẬN HÀNH

Một số collection mang tính "vận hành tạm thời" (không phải dữ liệu nghiệp vụ cốt lõi) và sẽ phình vô hạn nếu không có chính sách dọn dẹp — khác với soft-delete (vốn dành cho dữ liệu người dùng chủ động xóa).

| Collection | Vấn đề nếu không dọn | Chính sách đề xuất |
|---|---|---|
| `csv_upload_rows` | Mỗi job hàng chục nghìn row, giữ mãi dù job đã `completed` từ lâu | Sau khi `csv_upload_jobs.status = completed` và đã qua **30 ngày** (đủ thời gian Issuer đối chiếu nếu có khiếu nại), cron job archive các row `processing_status: created` ra cold storage (hoặc xóa hẳn, giữ lại `csv_upload_jobs` làm summary vĩnh viễn vì đã có `created_count`/`error_count`). Row lỗi (`invalid`) có thể xóa sớm hơn (7 ngày) vì không có giá trị tra cứu dài hạn. |
| `otp_codes` | Sinh liên tục ở mọi luồng (login, claim, reset password, link access) | Đã có TTL index trên `expires_at` (mục 5) — tự động dọn, không cần cron thêm. |
| `sessions` (đã revoked hoặc hết hạn) | Tích lũy theo số lần login | Đã có TTL index trên `expires_at`; session `status: revoked` nhưng chưa hết hạn nên giữ tối thiểu vài ngày để phục vụ điều tra bảo mật, sau đó để TTL tự dọn theo `expires_at` gốc — không cần xóa ngay khi revoke. |
| `access_records` | Tăng liên tục theo mỗi lượt xem, là dữ liệu audit nên **không được xóa** | Không xóa — đây là dữ liệu compliance. Nếu volume lớn sau pilot, cân nhắc archive (không xóa) các bản ghi cũ hơn 1 năm sang collection/cluster riêng, giữ nguyên khả năng truy vấn khi cần. |
| `notifications` | Tích lũy vô hạn theo owner, phần lớn không còn giá trị sau khi đã đọc | Cron job xóa cứng (không phải soft-delete, vì đây không phải dữ liệu owner chủ động tạo) các notification `is_read: true` và cũ hơn **90 ngày**. |

> Nguyên tắc chung: **dữ liệu compliance/audit không bao giờ bị cron xóa** (`audit_logs`, `access_records`); **dữ liệu vận hành tạm thời** (`csv_upload_rows`, `otp_codes`, `sessions`, `notifications`) có chính sách dọn riêng theo từng loại, tách bạch với cơ chế soft-delete 3/30 ngày vốn chỉ áp dụng cho hành động xóa chủ động của Owner.

---

## 9. CÁC ĐIỂM CÒN TREO (OPEN ITEMS)

| # | Vấn đề | Trạng thái |
|---|---|---|
| 1 | `plan`/quota của Verifier (US 3.6, 3.7) | AC nghiệp vụ chưa chốt (billing, tier, reset cycle). Schema đã đặt placeholder tối thiểu ở `organizations.verifier_profile.plan`, cần review lại khi AC rõ ràng. |
| 2 | Multi-user per organization (nhiều nhân viên cùng 1 Issuer/Verifier) | Spec hiện tại là 1 account/1 tổ chức (US 3.1 "One account per Verifier"). Nếu sau này cần multi-user, sẽ cần đổi quan hệ Account↔Org từ 1:1 sang N:1 **và** thiết kế lại RBAC thêm tầng permission (đã bỏ ở mục 4) — đây là thay đổi cấu trúc thật sự, không phải "đã chừa sẵn". Cần xác nhận có nằm trong scope pilot 90 ngày không trước khi quyết định có làm sẵn hay để sau. |
| 3 | Redis blocklist cho revoke tức thời tuyệt đối | Chưa bắt buộc cho pilot (độ trễ ≤15 phút của access token JWT được xem là chấp nhận được). Cần quyết định rõ nếu yêu cầu bảo mật đòi hỏi khắt khe hơn. |
| 4 | Archive `access_records`/`csv_upload_rows` sau pilot | Chính sách ở mục 8 là đề xuất dựa trên giả định volume của pilot 90 ngày; cần đánh giá lại khi có số liệu thực tế về lượng CSV upload và lượt verify. |

**Đã xử lý (không còn treo):** unique/partial-unique index cho email/username/tax_code+type/otp_hash (mục 5.1 — `organizations` và `verified_links` dùng **partial** index để không phá luồng resubmit sau reject và không chặn nhầm việc tái sử dụng OTP của link đã hết hiệu lực) · cơ chế lưu trạng thái "đang chờ duyệt" cho consent `per_request` (`access_records.result: pending`) · lịch sử đầy đủ các lần eKYC scan (`claims.ekyc_attempts`) · tách field đặc thù Verifier khỏi `organizations` root (`verifier_profile`) · phân loại độ ưu tiên tạo index theo volume pilot · **bỏ hẳn collection `roles`/`role_ids`** (AC không có nhu cầu phân quyền nội bộ, xem mục 4) · **thêm `issuer_org_id` denormalized vào `claims`** + đủ index cho `claims`/`csv_upload_jobs` (trước đó bị thiếu hoàn toàn, phát hiện qua log thực tế chỉ tạo được 14/16 collection có index) · bổ sung `ekyc_capture_sessions` cho luồng QR handoff CCCD.

Ngoài 4 điểm trên, schema đã đủ để triển khai toàn bộ AC đã cung cấp cho 4 Portal (Issuer, Owner, Verifier, Admin).
