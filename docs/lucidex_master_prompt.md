# LUCIDEX — MASTER PROMPT (đưa thẳng cho AI coding agent)

> **Cách dùng (gói Free):** đọc kỹ mục 9 trước khi bắt đầu — dự án này build qua nhiều session nhỏ trong 1 Claude Project, không dán 1 lần toàn bộ tài liệu. Tạo Project `Lucidex Pilot`, upload `lucidex_db_schema.md` + file này (`lucidex_master_prompt.md`) vào Project Knowledge, sau đó mở chat mới cho từng SESSION theo mục 6.

---

## VAI TRÒ

Bạn là Senior Full-stack Engineer. Nhiệm vụ: khởi tạo và code hoàn chỉnh dự án **Lucidex** — nền tảng xác thực văn bằng số hóa, Pilot 90 ngày, 4 portal (Issuer, Owner, Verifier, Admin), tất cả là **web app** ở giai đoạn này.

**Việc cần làm theo đúng thứ tự:**
1. Tạo cấu trúc thư mục dự án đầy đủ (backend + frontend) theo đúng mục 3 dưới đây.
2. Tạo `requirements.txt` (backend) và `package.json` (frontend) đầy đủ mọi thư viện cần dùng.
3. Tạo `.env.example` cho cả backend và frontend.
4. Code hoàn chỉnh: models (Beanie), schemas (Pydantic), services, API routes theo 4 portal, migration script tạo index, seed script tạo Platform Admin đầu tiên.
5. Frontend React: layout riêng cho từng portal, gọi API qua 1 lớp API client dùng chung.
6. Viết `README.md` hướng dẫn setup & chạy dự án.

Không dừng lại ở việc chỉ tạo file rỗng/placeholder — code phải chạy được, đúng logic nghiệp vụ theo AC đã cung cấp trong tài liệu đính kèm.

---

## 1. TECH STACK (đã chốt)

**Backend:** Python 3.11+, FastAPI, MongoDB + Beanie ODM + Pydantic v2, Motor (driver), python-jose hoặc PyJWT (JWT), passlib+bcrypt (hash password), Celery hoặc arq (background jobs — chọn **arq** vì nhẹ, async-native, phù hợp FastAPI hơn Celery), Redis (broker cho arq + cache ngắn hạn nếu cần).

**Frontend:** **React + Vite + TypeScript** — chọn vì: build nhanh, deploy tĩnh dễ (Vercel/Netlify/Nginx), dev server nhanh hơn CRA/Next đáng kể, không cần SSR (4 portal đều là dashboard sau-login, không cần SEO). Kèm: TailwindCSS (styling nhanh, dễ maintain 4 portal khác theme), React Router (routing theo portal), TanStack Query (data fetching + cache, khớp tự nhiên với kiến trúc API-first), Axios (HTTP client), React Hook Form + Zod (form + validate khớp AC), **qrcode.react** (dựng QR code cho luồng QR handoff CCCD, xem mục 4.1).

**DB:** MongoDB Atlas, connection string dùng biến môi trường (xem mục 2).

---

## 2. MÔI TRƯỜNG & SECRETS

**Không hardcode connection string hay bất kỳ secret nào trong code.** Tạo file `.env` (gitignore) từ `.env.example`.

`backend/.env.example`:
```
MONGODB_URI=mongodb+srv://admin:<db_password>@lucidexserver.ooqpjuu.mongodb.net/?appName=LucidexServer
MONGODB_DB_NAME=lucidex

JWT_SECRET_KEY=<generate-random-secret>
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

REDIS_URL=redis://localhost:6379/0

EMAIL_SMTP_HOST=
EMAIL_SMTP_PORT=
EMAIL_SMTP_USER=
EMAIL_SMTP_PASSWORD=

SMS_GATEWAY_API_KEY=

# eKYC provider — FPT.AI (OCR + Face Match + Liveness), xem lý do chọn ở lucidex_master_prompt.md mục 4.4
EKYC_PROVIDER=fpt_ai
EKYC_MOCK_MODE=true              # true khi dev/test (không gọi API thật, trả score giả lập cấu hình được)
EKYC_MOCK_SCORE=95               # chỉ dùng khi EKYC_MOCK_MODE=true, đổi số để test cả 2 nhánh >=90% và <90%
FPT_AI_API_KEY=
FPT_AI_OCR_URL=https://api.fpt.ai/vision/ocr
FPT_AI_LIVENESS_URL=https://api.fpt.ai/dmp/liveness/v3
FPT_AI_FACEMATCH_URL=https://api.fpt.ai/dmp/liveness/v3   # facematch trả cùng response với liveness API, xem 4.4

# QR handoff (chụp CCCD chuyển sang điện thoại) — xem mục 4.4
EKYC_CAPTURE_SESSION_TTL_MINUTES=10
FRONTEND_MOBILE_CAPTURE_BASE_URL=http://localhost:5173/mobile-capture

FILE_STORAGE_BACKEND=local   # local | s3
FILE_STORAGE_PATH=./uploads  # nếu local
S3_BUCKET_NAME=
S3_ACCESS_KEY=
S3_SECRET_KEY=

CORS_ALLOWED_ORIGINS=http://localhost:5173
```

> Lưu ý cho AI: `<db_password>` là placeholder thật do người dùng cung cấp — **thay bằng biến môi trường**, không bao giờ in ra log, không commit vào git. Thêm `.env` vào `.gitignore` ngay từ commit đầu tiên.

> **Về eKYC provider**: đã khảo sát, không có gói free vĩnh viễn chính thức nào cho sản phẩm eKYC bundle đầy đủ (FPT.AI yêu cầu liên hệ sale để cấp hạn mức; VNPT eKYC quảng cáo free 30 ngày dùng thử). Vì build trải dài nhiều session, **mặc định `EKYC_MOCK_MODE=true`** trong suốt quá trình dev — chỉ bật `false` + API key thật khi cần test luồng end-to-end thật. `ekyc_service.py` phải trừu tượng hoá provider (interface chung `verify_id(front_img, back_img, selfie) -> EkycResult`), để đổi sang VNPT hoặc provider khác sau này chỉ cần viết 1 class mới, không sửa luồng nghiệp vụ.

**MongoDB Atlas là replica set sẵn** (bắt buộc cho multi-document transaction ở luồng migration eKYC) — không cần setup thêm gì cho việc này, chỉ cần dùng đúng transaction API của Motor/Beanie.

---

## 3. CẤU TRÚC DỰ ÁN (bắt buộc theo đúng cây thư mục này)

```
lucidex/
├── backend/
│   ├── app/
│   │   ├── main.py                        # FastAPI app entrypoint, mount routers, CORS, lifespan (init Beanie)
│   │   ├── core/
│   │   │   ├── config.py                  # Settings (pydantic-settings, đọc .env)
│   │   │   ├── security.py                # hash password, verify, JWT encode/decode
│   │   │   ├── database.py                # Motor client + Beanie init_beanie(document_models=[...])
│   │   │   └── deps.py                    # FastAPI Depends: get_current_owner, get_current_issuer, get_current_admin, get_current_verifier, require_permission()
│   │   ├── models/                        # 1 file/collection, Beanie Document, đúng field theo lucidex_db_schema.md
│   │   │   ├── organization.py
│   │   │   ├── institution_account.py
│   │   │   ├── platform_admin.py
│   │   │   ├── owner.py
│   │   │   ├── credential.py
│   │   │   ├── claim.py
│   │   │   ├── csv_upload_job.py
│   │   │   ├── csv_upload_row.py
│   │   │   ├── verified_link.py
│   │   │   ├── access_record.py
│   │   │   ├── trusted_organization.py
│   │   │   ├── notification.py
│   │   │   ├── audit_log.py
│   │   │   ├── otp_code.py
│   │   │   ├── session.py
│   │   │   ├── role.py
│   │   │   └── ekyc_capture_session.py     # model bổ sung ngoài lucidex_db_schema.md gốc, xem mục 4.1
│   │   ├── schemas/                       # Pydantic request/response DTO, tách khỏi Document model
│   │   │   ├── auth.py
│   │   │   ├── organization.py
│   │   │   ├── credential.py
│   │   │   ├── claim.py
│   │   │   ├── verified_link.py
│   │   │   └── ...
│   │   ├── services/                      # business logic thuần, không phụ thuộc FastAPI request/response
│   │   │   ├── auth_service.py            # login, 2FA, refresh token, session revoke
│   │   │   ├── otp_service.py             # sinh/verify OTP, gửi qua email/sms channel
│   │   │   ├── audit_service.py           # ghi audit_logs, mask email, format detail string
│   │   │   ├── notification_service.py    # tạo notification, generic theo entity
│   │   │   ├── csv_service.py             # parse, validate, dedup, queue CSV
│   │   │   ├── ekyc_service.py            # gọi FPT.AI (hoặc mock nếu EKYC_MOCK_MODE=true), tính combined_score, xóa ảnh ngay
│   │   │   ├── ekyc_capture_service.py    # tạo/quản lý ekyc_capture_sessions, atomic invalidate token, xem mục 4.1
│   │   │   ├── claim_service.py           # claim qua email OTP + eKYC fallback + migration transaction
│   │   │   ├── consent_service.py         # verified_link, access_records, 4 loại consent
│   │   │   └── file_storage_service.py    # upload local/S3, trừu tượng hoá để đổi backend dễ
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── admin/          # US 4.1–4.6 — API-first, mobile-ready
│   │   │       ├── issuer/         # US 1.0–1.9 — API-first, mobile-ready
│   │   │       ├── owner/          # US 2.1–2.12 — API-first, mobile-ready
│   │   │       └── verifier/       # US 3.0–3.7 — API-first, mobile-ready
│   │   ├── workers/
│   │   │   ├── csv_worker.py       # arq task xử lý CSV background
│   │   │   ├── purge_worker.py     # cron: hard-purge soft-deleted quá hạn
│   │   │   └── cleanup_worker.py   # cron: dọn csv_upload_rows/notifications cũ (mục 8 db schema)
│   │   └── utils/
│   │       ├── hashing.py          # SHA-256 cho national_id
│   │       └── pagination.py       # cursor-based pagination helper
│   ├── scripts/
│   │   ├── create_indexes.py       # tạo toàn bộ index mục 5 lucidex_db_schema.md (chạy trước khi seed)
│   │   └── seed_admin.py           # tạo Platform Admin đầu tiên
│   ├── tests/
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── portals/
│   │   │   ├── admin/              # routes + pages + components riêng
│   │   │   ├── issuer/
│   │   │   ├── owner/              # tổ chức API call qua 1 lớp riêng, dễ tái dùng cho mobile sau này
│   │   │   └── verifier/
│   │   ├── mobile-capture/          # trang chụp CCCD qua QR handoff — KHÔNG cần đăng nhập, chỉ cần token
│   │   │   └── [token]/             # route /mobile-capture/:token, xem mục 4.1
│   │   ├── shared/
│   │   │   ├── api/                # axios instance, interceptor refresh token, endpoint theo portal
│   │   │   ├── components/         # UI dùng chung (button, table, modal...)
│   │   │   ├── hooks/               # useAuth, usePagination...
│   │   │   └── types/               # TypeScript types khớp Pydantic schemas
│   │   ├── App.tsx                  # router chính, phân theo portal theo subpath hoặc subdomain
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── .env.example                 # VITE_API_BASE_URL=http://localhost:8000/api/v1
│
├── docker-compose.yml                # optional: redis + backend + frontend cho dev local (Mongo dùng Atlas, không cần container)
└── README.md                         # hướng dẫn setup toàn bộ dự án
```

---

## 4. NGUYÊN TẮC KIẾN TRÚC BẮT BUỘC (không được bỏ qua)

1. **API-first & token-based auth cho CẢ 4 PORTAL** — không dùng cookie session cho bất kỳ portal nào, vì tất cả 4 portal (Issuer, Owner, Verifier, Admin) đều sẽ có mobile app kết nối cùng API trong tương lai. Toàn bộ tính năng phải đi qua REST API JSON versioned (`/api/v1/...`); web frontend chỉ là 1 client, mobile app sau này là client thứ 2 gọi cùng API, không viết lại backend cho bất kỳ portal nào.
2. **Atomic conditional update cho mọi cờ "dùng 1 lần"** (`invite_token_used`, `otp_codes.used`...) — dùng `find_one_and_update` với filter match giá trị cũ, không đọc-rồi-ghi. Áp dụng đúng pattern này cho toàn bộ luồng có nguy cơ race condition.
3. **MongoDB multi-document transaction** cho luồng migration eKYC (owner cũ → owner mới) — bắt buộc, kèm optimistic concurrency check, retry logic cho `TransientTransactionError`.
4. **Zero-Retention**: hash SHA-256 national_id ngay khi nhận, xóa ảnh CCCD/selfie khỏi RAM/disk ngay sau khi `ekyc_service` tính xong score — không lưu file ảnh xuống storage dưới bất kỳ hình thức nào.
5. **Audit log**: `detail` luôn là plain-text string theo đúng bảng format trong AC US 4.6, mask email, tuyệt đối không log OTP/password/CCCD thô. Không expose route PATCH/DELETE cho `audit_logs`.
6. **Index**: chạy `scripts/create_indexes.py` (tạo đúng toàn bộ bảng mục 5.1 và 5.2 của `lucidex_db_schema.md`, chú ý các index cần **partial** chứ không phải unique tuyệt đối) **trước** khi có bất kỳ dữ liệu thật nào được ghi.
7. **CSV upload**: xử lý qua `arq` worker, không block request, tách `csv_upload_rows` khỏi `csv_upload_jobs`, insert theo batch, hỗ trợ resume sau khi restart server (đọc lại theo `processing_status: queued`).
8. **RBAC tenant scoping**: mọi query trả dữ liệu theo tổ chức (`credentials`, `csv_upload_jobs`, `claims`, `access_records`) phải filter theo `org_id` lấy từ JWT payload của session hiện tại, không tin `org_id` do client gửi lên trong request body/query param.
9. **Soft-delete**: dùng cron worker (`purge_worker.py`), không dùng TTL index, cho các entity cần ghi audit log trước khi hard-purge (`credentials`, `verified_links`, `owners`, `organizations`).
10. **QR handoff cho luồng chụp CCCD** (chi tiết ở mục 4.1 dưới đây) — bổ sung kỹ thuật **ngoài AC gốc** (AC US 2.4 không quy định thiết bị chụp), do người dùng yêu cầu thêm: desktop hiện QR, điện thoại quét để mở trang chụp ảnh, link tự hủy sau khi submit, desktop chuyển sang trạng thái "đang xác thực" rồi hiện kết quả theo đúng AC US 2.4 gốc (>=90% auto-approve, <90% cảnh báo + Scan Again/Confirm).

### 4.1 Chi tiết luồng QR Handoff (bổ sung ngoài AC gốc)

**Model mới cần thêm** vào `models/` (không có trong `lucidex_db_schema.md` gốc — thêm collection `ekyc_capture_sessions`):
```
{
  _id, owner_id (FK -> owners), claim_id (FK -> claims, tạo trước ở trạng thái khởi tạo),
  token,                                    # chuỗi random dùng trong URL QR, KHÔNG phải OTP hiển thị cho user đọc
  status: "pending" | "submitted" | "processing" | "completed" | "expired",
  expires_at,                               # now + EKYC_CAPTURE_SESSION_TTL_MINUTES (mặc định 10 phút)
  outcome: "auto_approved" | "low_confidence" | "unreadable_image" | "liveness_failed" | null
}
```
Index: `unique(token)`, TTL index trên `expires_at` (session hết hạn tự dọn, khác với claim/credential vốn cần cron vì cần audit — session này không phải dữ liệu compliance nên TTL thuần là hợp lý).

**Luồng xử lý:**
1. Owner (desktop) bấm "Claim via CCCD" → API tạo `ekyc_capture_sessions` (status=`pending`) → trả về `token` → frontend desktop dựng QR code từ URL `${FRONTEND_MOBILE_CAPTURE_BASE_URL}/{token}` (dùng thư viện `qrcode.react` ở frontend).
2. Desktop bắt đầu **poll** `GET /api/v1/owner/ekyc-sessions/{token}/status` mỗi 2–3 giây (short-poll, đúng nguyên tắc mobile-ready đã chốt — không dùng cơ chế chỉ web mới có).
3. User quét QR bằng điện thoại → mở trang `/mobile-capture/{token}` — đây **vẫn là trang web** (React, cùng codebase frontend), **không phải bản mobile app native** sẽ làm sau này. Trang này không cần đăng nhập, chỉ cần token hợp lệ, hiển thị đúng hướng dẫn chụp theo AC US 2.4 (6 bước hướng dẫn + chụp mặt trước/sau CCCD + selfie).
4. User bấm submit trên điện thoại → API nhận ảnh, xử lý atomic conditional update: `find_one_and_update(token=token, status="pending")` → set `status="submitted"`. Nếu 0 document match (đã dùng rồi/hết hạn) → trả lỗi, không cho submit — đây chính là cơ chế "**link tự hủy**" bạn yêu cầu, dùng đúng pattern atomic đã áp dụng cho `invite_token_used` (mục 4, nguyên tắc số 2), không phải xóa session mà là chuyển trạng thái không thể quay lại.
5. Trang mobile hiện thông báo dạng "Đã gửi ảnh, vui lòng kiểm tra trên máy tính của bạn" — kết thúc vai trò của điện thoại tại đây.
6. Backend đẩy job vào `arq` worker → `status="processing"` → worker gọi `ekyc_service.verify_id()` (thật hoặc mock tùy `EKYC_MOCK_MODE`) → ghi kết quả vào `claims.ekyc_attempts` (đúng cấu trúc đã có trong `lucidex_db_schema.md`) → cập nhật `ekyc_capture_sessions.status="completed"` + `outcome`.
7. Desktop (đang poll) thấy `status` chuyển `pending → processing` → **tự động chuyển UI từ QR sang màn hình spinner** "Hệ thống đang kiểm tra thông tin xác thực..." (đúng yêu cầu của bạn).
8. Desktop thấy `status="completed"` → gọi API lấy chi tiết claim → hiển thị đúng theo AC US 2.4 gốc:
   - `outcome="auto_approved"` (>=90%) → thông báo "Your credential has been successfully claimed."
   - `outcome="low_confidence"` (<90%) → cảnh báo + 2 nút "Scan Again" / "Confirm" (đúng AC gốc)
   - Nếu chọn "Scan Again" → tạo **session mới** (quay lại bước 1, QR mới), vì ảnh chụp trên điện thoại, không quay lại chụp trên desktop.

**Bảo mật cho token QR** (không có trong AC gốc, tự thêm vì đây là cơ chế mới): token phải đủ entropy (≥128 bit, dùng `secrets.token_urlsafe`), TTL ngắn (10 phút), single-use qua atomic update ở bước 4, và endpoint `/mobile-capture/{token}` phải rate-limit theo IP để chống dò token.

---

## 5. NỘI DUNG NGHIỆP VỤ

Toàn bộ Acceptance Criteria chi tiết theo từng User Story (US 1.0–1.9, 2.1–2.12, 3.0–3.7, 4.1–4.6) đã có trong tài liệu gốc đính kèm cùng prompt này — implement **đúng từng message lỗi, đúng từng điều kiện, đúng từng state transition** đã mô tả, không rút gọn hay tự diễn giải lại. Với các mục AC ghi "chưa xác định" (US 3.6, 3.7 — Quota & Plan), tạo cấu trúc tối thiểu theo `lucidex_db_schema.md` (`organizations.verifier_profile.plan`) nhưng **không** tự bịa ra logic billing/nâng cấp — để API trả về dữ liệu tĩnh/mock và đánh dấu rõ `# TODO: chờ chốt AC US 3.6/3.7` trong code.

---

## 6. THỨ TỰ BUILD — CHIA THEO SESSION CHO GÓI FREE

> Dự án này build trên **claude.ai gói Free**, không có Claude Code. Free tier giới hạn khoảng 15–40 tin nhắn/5 giờ (số liệu thay đổi theo thời gian, kiểm tra lại tại support.claude.com nếu cần chính xác), và không có RAG cho Project Knowledge nên mỗi tin nhắn vẫn tính phí token theo toàn bộ tài liệu đính kèm. Vì vậy **chia nhỏ hơn nhiều** so với 5 phase gốc — mỗi session dưới đây được thiết kế để hoàn thành trong 1 cửa sổ 5 giờ (nhiều khả năng chỉ dùng 10–20 tin nhắn/session nếu làm đúng cách ở mục 9).

```
SESSION 0   — Scaffold: cấu trúc thư mục, requirements.txt, package.json, .env.example
SESSION 1   — create_indexes.py + seed_admin.py (chạy thử được, kết nối MongoDB Atlas thành công)
SESSION 2   — core/: config.py, security.py, database.py, deps.py
SESSION 3   — models/: toàn bộ 16 Beanie Document (chỉ định nghĩa field, chưa viết logic)
SESSION 4   — services/: auth_service.py + otp_service.py
SESSION 5   — services/: audit_service.py + notification_service.py
SESSION 6   — RBAC middleware (deps.py mở rộng: require_permission, tenant scoping)
SESSION 7   — Admin API: US 4.1–4.3 (Pending Requests, Detail, Approve/Reject)
SESSION 8   — Admin API: US 4.4–4.6 (Dashboard, Account Management, Audit Log)
SESSION 9   — Admin frontend (React) — layout + toàn bộ trang tương ứng SESSION 7–8
SESSION 10  — Issuer API: US 1.0–1.4 (Registration, Onboarding, Login/2FA, Forgot Password)
SESSION 11  — Issuer API: US 1.5 (Upload CSV) — riêng 1 session vì luồng này phức tạp nhất
SESSION 12  — Issuer API: US 1.6–1.9 (Review Queue, History, Revoke, Dashboard)
SESSION 13  — Issuer frontend — layout + toàn bộ trang tương ứng SESSION 10–12
SESSION 14  — Owner API: US 2.1–2.3 (Register/Login, Notification, Claim .edu)
SESSION 15  — Owner API: US 2.4 (Claim CCCD/eKYC + Migration transaction) + QR handoff (mục 4.1) — riêng 1 session
SESSION 16  — Owner API: US 2.5–2.8 (Credential List, Profile, Verified Link, Consent Settings)
SESSION 17  — Owner API: US 2.9–2.12 (Trusted Org, Audit Log, Dashboard, Data Deletion)
SESSION 18  — Owner frontend — layout + toàn bộ trang tương ứng SESSION 14–17
SESSION 19  — Verifier API: US 3.0–3.2 (Registration, Onboarding, Status Tracking)
SESSION 20  — Verifier API: US 3.3–3.7 (Verify Link, Dashboard, Export, Quota — mock)
SESSION 21  — Verifier frontend — layout + toàn bộ trang tương ứng SESSION 19–20
SESSION 22  — workers/: csv_worker, purge_worker, cleanup_worker + README.md tổng
```

Sau mỗi session: đảm bảo phần vừa code chạy được độc lập (`uvicorn app.main:app --reload` không lỗi import), không để lỗi dồn sang session sau.

---

## 7. DELIVERABLES CUỐI CÙNG (checklist)

- [ ] Cấu trúc thư mục đầy đủ theo mục 3
- [ ] `backend/requirements.txt` — liệt kê đủ version cụ thể, không để trống version
- [ ] `frontend/package.json` — đầy đủ dependencies + devDependencies
- [ ] `.env.example` cho cả backend và frontend
- [ ] `scripts/create_indexes.py` chạy được, tạo đúng toàn bộ index (kể cả partial)
- [ ] `scripts/seed_admin.py` tạo được Platform Admin đầu tiên để đăng nhập lần đầu
- [ ] Toàn bộ model Beanie khớp đúng field trong `lucidex_db_schema.md`
- [ ] API 4 portal chạy được end-to-end ít nhất cho luồng chính (happy path) của mỗi US
- [ ] `README.md` gốc: hướng dẫn cài đặt, chạy backend, chạy frontend, chạy worker, seed admin, test thử 1 luồng
- [ ] Không có secret nào bị hardcode trong code

---

## 8. GHI CHÚ CHO AI KHI BẮT ĐẦU

Nếu có bất kỳ điểm nào trong AC gốc mâu thuẫn với `lucidex_db_schema.md`, **ưu tiên AC gốc** (vì đó là nguồn nghiệp vụ chính thức), nhưng phải nêu rõ mâu thuẫn đó ra thay vì tự ý chọn 1 bên và im lặng. Nếu thiếu thông tin để quyết định (ví dụ: frontend cần thư viện UI component cụ thể nào, provider email/SMS nào), chọn phương án phổ biến/tiêu chuẩn nhất và ghi chú lại trong README để người dùng biết có thể đổi sau.

---

## 9. QUY TRÌNH CHIA PHIÊN CHO GÓI FREE (bắt buộc đọc trước khi bắt đầu SESSION 0)

### 9.1 Setup 1 lần duy nhất

1. Vào claude.ai → **Projects** → tạo project tên `Lucidex Pilot` (Free cho phép tối đa 5 project, dùng 1 cái cho dự án này).
2. Upload vào **Project Knowledge** đúng 2 file: `lucidex_db_schema.md` và `lucidex_master_prompt.md` (bản đã cập nhật này). **Không** upload `lucidex_build_prompt.md` (nội dung đã gộp vào master prompt, tránh trùng lặp tốn token) và **không** upload nguyên văn toàn bộ tài liệu AC gốc (quá dài) — xem cách xử lý AC ở mục 9.3.
3. Đặt Project Instructions (system prompt của project) = nguyên văn mục "VAI TRÒ" + mục 1, 2 của `lucidex_master_prompt.md` (ngắn gọn, áp dụng cho mọi chat trong project).

> Lưu ý: Free tier **không có RAG** cho Project Knowledge (chỉ Pro trở lên), nghĩa là mỗi tin nhắn trong project vẫn nạp toàn bộ 2 file này vào context — không miễn phí về token, chỉ đỡ phải upload tay lại mỗi lần. Vì vậy càng cần giữ Project Knowledge gọn.

### 9.2 Mỗi session — bắt đầu 1 chat MỚI trong project (không dùng lại chat cũ)

Chat càng dài, mỗi tin nhắn sau càng tốn token hơn (Claude đọc lại toàn bộ lịch sử) → cạn quota 5 giờ nhanh hơn. Vì vậy: **1 session = 1 chat mới**, không nối dài chat cũ sang session tiếp theo.

Tin nhắn đầu tiên của mỗi session theo khuôn mẫu:
```
Tiếp tục dự án Lucidex. Đây là SESSION [số] — [tên session theo mục 6].

[Dán nguyên văn "SESSION STATE" từ cuối session trước — xem mục 9.4]

[Nếu session này động tới AC cụ thể của 1 portal, dán kèm đoạn AC liên quan
 từ tài liệu gốc — CHỈ đoạn cần dùng, không dán cả tài liệu]

Bắt đầu SESSION [số] theo đúng lucidex_master_prompt.md.
```

### 9.3 Cách mang theo AC gốc mà không tốn token

Tài liệu AC gốc (US 1.0–4.6) đã được **tách sẵn thành 4 file riêng theo portal**, dùng thay vì dán cả tài liệu gốc:
- `lucidex_ac_admin.md` (US 4.1–4.6)
- `lucidex_ac_issuer.md` (US 1.0–1.9)
- `lucidex_ac_owner.md` (US 2.1–2.12)
- `lucidex_ac_verifier.md` (US 3.0–3.7)

Cách dùng theo session:
- Với các session **models/services/scaffold** (0–6, 22): không cần AC, chỉ cần `lucidex_db_schema.md` + `lucidex_master_prompt.md` trong Project Knowledge là đủ.
- Với các session theo portal (7–21): **chỉ upload/đính kèm đúng 1 file AC của portal đang code trong session đó** (vd. SESSION 7–9 dùng `lucidex_ac_admin.md`, SESSION 10–13 dùng `lucidex_ac_issuer.md`...) — không cần cả 4 file cùng lúc.
- Có thể đính kèm trực tiếp vào từng chat riêng lẻ (không cần bỏ vào Project Knowledge chung) vì mỗi file AC chỉ dùng trong đúng nhóm session của portal đó rồi thôi — tránh Project Knowledge phình to không cần thiết.

### 9.4 Giao thức bàn giao giữa các session — "SESSION STATE"

**Cuối mỗi session**, trước khi hết quota hoặc trước khi dừng, gửi tin nhắn cuối cùng:
```
Trước khi kết thúc session, tóm tắt lại SESSION STATE theo đúng khuôn mẫu sau
để mình mang sang session tiếp theo:

- Session vừa hoàn thành: [số + tên]
- File đã tạo/sửa trong session này: [liệt kê đường dẫn]
- Điểm còn dang dở (nếu có): [...]
- Quyết định kỹ thuật phát sinh cần nhớ (nếu có, vd. đã chọn thư viện X thay vì Y): [...]
- Session tiếp theo nên bắt đầu từ đâu: [...]
```
Copy nguyên văn phần Claude trả lời, lưu lại (paste vào 1 file text riêng trên máy bạn, đặt tên `session_state.md`) — đây là thứ duy nhất bạn dán vào đầu session kế tiếp (theo khuôn ở mục 9.2), **không cần dán lại toàn bộ code đã viết** — code đã nằm trên máy bạn rồi, Claude chỉ cần biết đã đi tới đâu, không cần đọc lại.

### 9.5 Quy tắc tiết kiệm quota trong lúc chat (theo khuyến nghị chính thức của Anthropic)

- Gộp nhiều yêu cầu liên quan vào 1 tin nhắn thay vì chia nhiều tin nhắn nhỏ (vd. thay vì hỏi riêng từng file, yêu cầu "tạo cả 3 file models sau trong 1 lượt").
- Tránh sửa qua lại nhiều vòng kiểu "không đúng ý, thử lại" — mô tả rõ yêu cầu ngay từ đầu để giảm số lượt follow-up (mỗi follow-up cộng dồn chi phí đọc lại toàn bộ chat).
- Tắt các tính năng không cần (web search, extended thinking) khi chat thuần code — các tính năng này tốn thêm token.
- Nếu 1 session bắt đầu bị Claude trả lời cụt hoặc báo gần hết độ dài phản hồi, đó là dấu hiệu nên chốt SESSION STATE và dừng lại ngay, đừng cố kéo dài thêm trong cùng chat.
