# Hướng dẫn dùng Invite Link Service

## Mục đích

Module này dùng để tạo và lưu invite link cho luồng onboarding issuer/verifier.

## Các file đã thêm

- backend/src/invitation/service.py
  - Chứa logic chính: sinh raw token, hash token, tính expires_at = created_at + 30 ngày, revoke pending invite cũ nếu cùng org_id, rồi lưu document mới.
- backend/src/invitation/repository.py
  - Chứa truy vấn/lưu dữ liệu qua Beanie.
- backend/src/invitation/exceptions.py
  - Chứa lỗi dùng cho việc tạo invite link.

## Cách gọi từ code khác

Import service đã expose sẵn:

```python
from src.invitation.service import invite_link_service
```

Gọi như sau:

```python
raw_token = await invite_link_service.create_invite_link(
    org_id=org_id,
    contact_email=contact_email,
    created_by=created_by,
)
```

### Tham số

- org_id: ID của organization cần tạo invite cho.
- contact_email: email liên hệ của người nhận invite.
- created_by: ID của người/admin tạo invite.

### Giá trị trả về

- Trả về raw_token dạng string.
- Token gốc KHÔNG được lưu vào DB; DB chỉ lưu token_hash.

## Lưu ý quan trọng

- Chỉ làm phần tạo + lưu invite link ở task này.
- Không làm gửi email ở đây.
- Không làm verify/consume token ở đây.
- Không tích hợp vào admin approve flow ở đây.

## Logic đã có sẵn

- Model InviteLink đã có ở backend/src/invitation/models.py.
- Enum InviteStatus đã có ở backend/src/invitation/constants.py và bao gồm:
  - PENDING
  - USED
  - REVOKED

## Hành vi khi tạo invite mới cho cùng org_id

Nếu org_id đã có pending invite, service sẽ tự động:
1. revoke invite cũ,
2. tạo invite mới.

Điều này giúp tránh lỗi duplicate key do unique partial index trên org_id với status pending.

## Test cần kiểm tra tiếp

Các test mong đợi:
- token_hash khớp regex 64 hex chars,
- expires_at = created_at + 30 ngày,
- invite cũ bị revoke khi tạo invite mới cho cùng org_id,
- không phát sinh duplicate key khi gọi nhiều lần,
- email được normalize trước khi lưu.
