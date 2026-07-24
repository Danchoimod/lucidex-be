# FE Integration Guide: Admin Organizations List & Filtering

Tài liệu này hướng dẫn chi tiết dành cho **Frontend (FE)** khi tích hợp API danh sách Tổ chức (Organizations List), lọc theo loại tổ chức (**Issuer / Verifier**), lọc theo trạng thái (**Pending Review / Approved / Rejected**) và thực hiện phân trang.

---

## 1. Thông tin Endpoint API

* **URL:** `/api/v1/admin/organizations/list` (hoặc `/api/v1/admin/organizations`)
* **Method:** `GET`
* **Xác thực (Auth):** Yêu cầu Admin Header Access Token:
  ```http
  Authorization: Bearer <access_token>
  ```

---

## 2. Query Parameters (Tham số yêu cầu)

| Tham số | Kiểu dữ liệu | Mặc định | Mô tả |
|---|---|---|---|
| `type` | `string` | `null` | Lọc theo loại tổ chức. Giá trị: `issuer` hoặc `verifier`. Nếu bỏ trống sẽ lấy cả 2. |
| `status` | `string` | `pending_review` | Lọc theo trạng thái. Giá trị: `pending_review`, `approved`, `rejected`. Nếu truyền `status=` rỗng hoặc tùy chỉnh để lấy tất cả. |

---

## 3. Cấu trúc Response (JSON)

HTTP Status: `200 OK`

```json
{
  "success": true,
  "data": [
    {
      "id": "678e1f77bcf86cd799439011",
      "type": "issuer",
      "status": "pending_review",
      "name": "Đại học Bách Khoa",
      "tax_code": "0101234567",
      "address": "268 Lý Thường Kiệt, Q.10, TP.HCM",
      "legal_rep_name": "Nguyễn Văn A",
      "contact_email": "contact@hcmut.edu.vn",
      "contact_phone": "0901234567",
      "registrant_name": "Trần Văn B",
      "registrant_title": "Trưởng phòng CNTT",
      "documents": [
        {
          "id": "doc_123",
          "name": "Giấy phép hoạt động.pdf",
          "url": "https://storage.lucidex.io/docs/doc_123.pdf",
          "uploaded_at": "2026-07-20T10:00:00Z"
        }
      ],
      "rejection_reason": null,
      "reviewed_by": null,
      "reviewed_at": null,
      "created_at": "2026-07-22T08:30:00Z"
    }
  ],
  "message": "Organizations retrieved successfully.",
  "error_code": null
}
```

---

## 4. Hướng dẫn Phân trang & Chuyển Tab trên Frontend

### A. Chuyển Tab **Issuer** vs **Verifier**
Để phân tách màn hình hoặc Tab giữa **Trường học / Tổ chức cấp bằng (Issuer)** và **Đơn vị xác thực (Verifier)**:

- **Danh sách Issuer chờ duyệt:**
  `GET /api/v1/admin/organizations/list?type=issuer&status=pending_review`
- **Danh sách Verifier chờ duyệt:**
  `GET /api/v1/admin/organizations/list?type=verifier&status=pending_review`
- **Danh sách Issuer đã duyệt:**
  `GET /api/v1/admin/organizations/list?type=issuer&status=approved`

### B. Xử lý Phân trang phía Client (Client-side Pagination)
Do API trả về danh sách được sắp xếp theo thời gian đăng ký từ **cũ nhất đến mới nhất** (`created_at` tăng dần):
1. FE gọi API tương ứng với Tab đang chọn (ví dụ `type=issuer&status=pending_review`).
2. FE lưu toàn bộ mảng `data` vào State.
3. FE thực hiện cắt trang hiển thị (`slice((page - 1) * pageSize, page * pageSize)`).

---

## 5. TypeScript Interfaces cho Frontend

```typescript
export type OrganizationType = 'issuer' | 'verifier';
export type OrganizationStatus = 'pending_review' | 'approved' | 'rejected';

export interface OrganizationDocument {
  id: string;
  name: string;
  url: string;
  uploaded_at: string;
}

export interface Organization {
  id: string;
  type: OrganizationType;
  status: OrganizationStatus;
  name: string;
  tax_code: string;
  address: string;
  legal_rep_name: string;
  contact_email: string;
  contact_phone: string;
  registrant_name: str;
  registrant_title?: string | null;
  documents: OrganizationDocument[];
  rejection_reason?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  created_at: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string | null;
  error_code?: string | null;
}
```

---

## 6. Code Ví dụ Frontend (React + Axios)

```tsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

export const AdminOrganizationList = () => {
  const [activeType, setActiveType] = useState<'issuer' | 'verifier'>('issuer');
  const [activeStatus, setActiveStatus] = useState<string>('pending_review');
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 10;

  useEffect(() => {
    const fetchOrganizations = async () => {
      try {
        const response = await axios.get<ApiResponse<Organization[]>>(
          `/api/v1/admin/organizations/list`,
          {
            params: {
              type: activeType,
              status: activeStatus,
            },
            headers: {
              Authorization: `Bearer ${localStorage.getItem('admin_access_token')}`,
            },
          }
        );
        if (response.data.success) {
          setOrganizations(response.data.data);
          setCurrentPage(1); // Reset về trang 1 khi đổi tab
        }
      } catch (error) {
        console.error('Lỗi khi tải danh sách tổ chức:', error);
      }
    };

    fetchOrganizations();
  }, [activeType, activeStatus]);

  // Phân trang trên Client
  const paginatedData = organizations.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );
  const totalPages = Math.ceil(organizations.length / pageSize);

  return (
    <div className="p-6">
      {/* Tab chọn loại Tổ chức */}
      <div className="flex gap-4 mb-4">
        <button
          className={activeType === 'issuer' ? 'font-bold underline' : ''}
          onClick={() => setActiveType('issuer')}
        >
          Issuer (Cơ sở đào tạo)
        </button>
        <button
          className={activeType === 'verifier' ? 'font-bold underline' : ''}
          onClick={() => setActiveType('verifier')}
        >
          Verifier (Đơn vị xác thực)
        </button>
      </div>

      {/* Tab lọc Trạng thái */}
      <div className="flex gap-2 mb-6">
        {['pending_review', 'approved', 'rejected'].map((status) => (
          <button
            key={status}
            className={`px-3 py-1 border rounded ${activeStatus === status ? 'bg-blue-600 text-white' : ''}`}
            onClick={() => setActiveStatus(status)}
          >
            {status}
          </button>
        ))}
      </div>

      {/* Bảng danh sách */}
      <table className="w-full border-collapse border">
        <thead>
          <tr className="bg-gray-100">
            <th className="border p-2">Tên tổ chức</th>
            <th className="border p-2">Mã số thuế</th>
            <th className="border p-2">Email liên hệ</th>
            <th className="border p-2">Ngày đăng ký</th>
          </tr>
        </thead>
        <tbody>
          {paginatedData.map((org) => (
            <tr key={org.id}>
              <td className="border p-2">{org.name}</td>
              <td className="border p-2">{org.tax_code}</td>
              <td className="border p-2">{org.contact_email}</td>
              <td className="border p-2">{new Date(org.created_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Điều hướng phân trang */}
      <div className="flex justify-between items-center mt-4">
        <button
          disabled={currentPage === 1}
          onClick={() => setCurrentPage((p) => p - 1)}
        >
          Trang trước
        </button>
        <span>Trang {currentPage} / {totalPages || 1}</span>
        <button
          disabled={currentPage >= totalPages}
          onClick={() => setCurrentPage((p) => p + 1)}
        >
          Trang sau
        </button>
      </div>
    </div>
  );
};
```
