# Lab 00.03: Quy Chuẩn Bằng Chứng (Evidence) & Khử Trùng Dữ Liệu (Sanitization)

**Mã tài liệu:** `LAB-00-03`
**Trạng thái:** `RUNTIME_PASS`
**Vùng áp dụng:** `ap-southeast-1` (Singapore)

---

## 1. Mục Tiêu (Objective)
Thiết lập quy trình thu thập bằng chứng runtime thực tế (Zero Fake Data) và tự động khử trùng thông tin nhạy cảm (Account ID, Access Keys, Passwords, JWT tokens) trước khi lưu trữ.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Tài Nguyên | Phạm Vi / Vùng | Tham Chiếu Runtime (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-evidence-vault-*` | Amazon S3 Bucket | `ap-southeast-1` | S3 Vault lưu trữ bằng chứng kiểm toán độc lập |
| `evidence/` | Thư mục bằng chứng cục bộ | Local Workspace | Phân nhóm theo 13 module (00-inventory đến 12-cleanup) |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Khóa (Key) | Giá Trị (Value) | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-evidence-vault-*` | S3 Vault & tài nguyên quản trị |
| `Project` | `aws-eks-secure-network-fabric` | S3 Vault & tài nguyên quản trị |
| `Environment` | `prod` | S3 Vault |
| `ManagedBy` | `manual` | Quản trị lưu trữ bằng chứng kiểm toán thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)
- **S3 Bucket Bảo Mật:**
  - `BlockPublicAccess`: Enabled (Khóa 100% quyền truy cập công khai).
  - `Versioning`: Enabled (Chống sửa đổi, bảo toàn bằng chứng gốc).
  - `ServerSideEncryption`: SSE-S3 hoặc KMS (`aws:kms`).
- **Quy Tắc Khử Trùng (Sanitization Rules):**
  - Account ID 12 chữ số → Thay bằng `123456789012` hoặc `***`.
  - Access Key ID (`AKIA...`) → Thay bằng `AKIA***REDACTED***`.
  - Passwords, Secret tokens, JWT Bearer → Thay bằng `***REDACTED***`.

---

## 5. Phụ Thuộc (Dependencies)
- Hoàn thành thiết lập định danh và ngân sách tại [Lab 00.02](02-naming-tagging-budget.md).

---

## 6. Kiểm Tra Đạt (Verification)
- [x] Script `scripts/sanitize-evidence.py` quét sạch toàn bộ thư mục `evidence/`.
- [x] Lệnh kiểm toán không phát hiện Account ID thật hoặc Access Keys chưa khử trùng.
- [x] Bằng chứng runtime đã thu thập: [`evidence/00-inventory/03-sanitization-audit.log`](../../evidence/00-inventory/03-sanitization-audit.log).

---

## 7. Cảnh Báo An Toàn & Rollback Plan
- **Cảnh báo rò rỉ:** Nếu phát hiện Access Key bị commit lên Git, phải lập tức revoke trên IAM và xoay vòng key mới ngay lập tức.
- **Kế hoạch khôi phục (Rollback):**
  ```bash
  aws s3 rb s3://fabric-evidence-vault-apse1-123456789012 --force --region ap-southeast-1
  ```
