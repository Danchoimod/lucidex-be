# How to run backend (python 3.14)
pip install uv
uv sync

cd backend
uv run fastapi dev app/main.py

Quy tac su dung git:
# Quy trình sử dụng Git cho 2 Backend Developer

Tài liệu này mô tả cách 2 Backend Developer làm việc chung trên một repository mà không đè code của nhau.

---

## 1. Cấu trúc branch

Repository sử dụng các branch chính:

```text
main
develop
feature/*
fix/*
chore/*
refactor/*
```

Ý nghĩa:

- `main`: code ổn định, dùng cho production hoặc release.
- `develop`: nơi tích hợp code hằng ngày.
- `feature/*`: làm tính năng mới.
- `fix/*`: sửa lỗi.
- `chore/*`: cấu hình, CI/CD, Docker, tài liệu kỹ thuật.
- `refactor/*`: cải thiện cấu trúc code nhưng không thay đổi chức năng.
- `doc/*`: thêm tài liệu mới

Không code trực tiếp trên `main` hoặc `develop`.

---

## 2. Khi bắt đầu làm việc

Mỗi người clone repository về máy riêng:

```bash
git clone git remote set-url origin https://github.com/NguyenNgocChien-01/lucidex-be.git

cd backend
```

Chuyển sang branch `develop`:

```bash
git switch develop
git pull origin develop
```

Luôn cập nhật `develop` trước khi nhận task mới.

---

## 3. Khi nhận một task

Ví dụ task là làm API đăng nhập.

Từ `develop`, tạo branch riêng:

```bash
git switch develop
git pull origin develop
git switch -c feature/auth-login
```

Kiểm tra branch hiện tại:

```bash
git branch
```

Kết quả mong đợi:

```text
* feature/auth-login
  develop
  main
```

---

## 4. Quy tắc đặt tên branch

Ví dụ:

```text
feature/auth-login
feature/credential-import
feature/admin-approval
fix/login-error
fix/cors-error
chore/setup-ci
chore/update-docker
refactor/user-service
```

Không đặt tên branch quá chung chung như:

```text
test
new
update
my-branch
```

---

## 5. Trong lúc code

Mỗi người chỉ làm trên branch của mình.

Ví dụ:

### Developer 1

```text
feature/auth-login
```

### Developer 2

```text
feature/organization-management
```

Hai người nên tránh cùng sửa mạnh một file tại cùng thời điểm, đặc biệt là:

```text
app/main.py
app/models.py
compose.yml
pyproject.toml
```

Nếu bắt buộc phải sửa cùng file, cần báo trước trong nhóm.

---

## 6. Commit code

Kiểm tra file đã thay đổi:

```bash
git status
```

Thêm file:

```bash
git add .
```

Commit:

```bash
git commit -m "feat(auth): add login endpoint"
```

Một số mẫu commit:

```text
feat(auth): add login endpoint
feat(credentials): add credential model
fix(auth): reject locked users
chore(ci): add backend test workflow
refactor(users): split user service
test(auth): add login tests
docs(readme): update setup guide
```

Không dùng commit message như:

```text
fix
update
done
new code
```

---

## 7. Push branch lên GitHub

```bash
git push -u origin feature/auth-login
```

Sau lần đầu, các lần sau chỉ cần:

```bash
git push
```

---

## 8. Tạo Pull Request

Trên GitHub, tạo Pull Request:

```text
base: develop
compare: feature/auth-login
```

Không tạo Pull Request trực tiếp vào `main`.

Mẫu mô tả Pull Request:

```markdown
## Task

Add login endpoint.

## Changes

- Validate email and password
- Generate JWT token
- Reject locked accounts

## Endpoint

POST /api/v1/auth/login

## Database Changes

None.

## How to Test

1. Run backend
2. Open `/docs`
3. Call login endpoint
4. Test valid and invalid credentials

## Known Limitations

Refresh token is not included yet.
```

---

## 9. Review code cho nhau

Developer 1 review Pull Request của Developer 2.

Developer 2 review Pull Request của Developer 1.

Checklist review:

- Code có đúng yêu cầu không?
- Có validation chưa?
- Có kiểm tra quyền không?
- Có test chưa?
- Có migration nếu thay đổi database không?
- Có lộ secret không?
- Có sửa file không liên quan không?
- Swagger có cập nhật không?
- Error response có đúng format không?

Chỉ merge sau khi review xong.

---

## 10. Sau khi Pull Request được merge

Cập nhật `develop`:

```bash
git switch develop
git pull origin develop
```

Xóa branch local:

```bash
git branch -d feature/auth-login
```

Nếu GitHub chưa tự xóa branch remote:

```bash
git push origin --delete feature/auth-login
```

---

## 11. Khi đang code nhưng `develop` đã thay đổi

Ví dụ người còn lại vừa merge code mới.

Cập nhật branch của bạn:

```bash
git switch develop
git pull origin develop
git switch feature/auth-login
git merge develop
```

Nếu không có conflict, tiếp tục code.

Nếu có conflict, Git sẽ báo file bị xung đột.

---

## 12. Cách xử lý conflict

Trong file conflict sẽ có dạng:

```text
<<<<<<< HEAD
code của bạn
=======
code từ develop
>>>>>>> develop
```

Bạn cần chọn phần code đúng hoặc kết hợp hai phần.

Sau khi sửa xong:

```bash
git add .
git commit -m "chore: resolve merge conflict"
git push
```

Với team mới, nên dùng `merge` thay vì `rebase` vì dễ hiểu hơn.

---

## 13. Chia task cho 2 người

Một cách chia hợp lý:

### Backend Developer 1

- Authentication
- User
- Role
- JWT
- Password reset
- Verified links

### Backend Developer 2

- Organization
- Admin approval
- Credential
- CSV import
- Audit log

Sau đó có thể chia tiếp theo module hoặc sprint.

---

## 14. Quy trình release

Luồng chuẩn:

```text
feature/*
→ Pull Request
→ develop
→ QA test
→ Pull Request
→ main
→ production
```

Khi code trên `develop` đã ổn định và QA kiểm tra xong:

```text
develop → Pull Request → main
```

Không merge vào `main` khi chưa test.

---

## 15. Quy trình hằng ngày

Mỗi lần nhận task:

```bash
git switch develop
git pull origin develop
git switch -c feature/ten-task
```

Sau khi code xong:

```bash
git status
git add .
git commit -m "feat(module): describe change"
git push -u origin feature/ten-task
```

Sau đó:

```text
Tạo Pull Request
→ người còn lại review
→ merge vào develop
→ QA test
```

---

## 16. Quy tắc quan trọng

- Không push trực tiếp vào `main`.
- Không push trực tiếp vào `develop`.
- Mỗi task dùng một branch riêng.
- Luôn `git pull origin develop` trước khi tạo branch.
- Không commit file `.env`.
- Không commit access key, password hoặc dữ liệu thật.
- Mỗi Pull Request chỉ nên xử lý một task chính.
- Không sửa file không liên quan tới task.
- Luôn chạy test trước khi tạo Pull Request.

---

## 17. Tóm tắt quy trình

```text
Nhận task
→ cập nhật develop
→ tạo branch riêng
→ code
→ test
→ commit
→ push
→ tạo Pull Request
→ người còn lại review
→ merge vào develop
→ QA test
→ merge vào main khi release
```