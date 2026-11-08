# Lab 00.01: Xác Thực Danh Tính IAM & Vùng Hoạt Động (Identity & Region)

**Mã tài liệu:** `LAB-00-01`
**Trạng thái:** `RUNTIME_PASS`
**Vùng áp dụng:** `ap-southeast-1` (Singapore)

---

## 1. Mục Tiêu (Objective)
Xác thực danh tính IAM có đầy đủ quyền triển khai hạ tầng mạng đa VPC, EKS và dịch vụ bảo mật; khóa cứng vùng hoạt động tại Singapore (`ap-southeast-1`).

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Tài Nguyên | Phạm Vi / Vùng | Tham Chiếu Runtime (Snapshot) |
| :--- | :--- | :--- | :--- |
| `kien-lvn` | IAM User / Caller Identity | Global / IAM | `arn:aws:iam::123456789012:user/kien-lvn` |
| `ap-southeast-1` | AWS Target Region | Singapore | `ap-southeast-1a`, `ap-southeast-1b` |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Khóa (Key) | Giá Trị (Value) | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-*` | Toàn bộ tài nguyên của dự án |
| `Project` | `aws-eks-secure-network-fabric` | Toàn bộ tài nguyên của dự án |
| `Environment` | `prod` | Toàn bộ tài nguyên của dự án |
| `ManagedBy` | `manual` | Quản trị thiết lập nền tảng thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)
- **Target Region:** `ap-southeast-1` (Asia Pacific - Singapore).
- **IAM Policies Bắt Buộc:** `AdministratorAccess` hoặc tập hợp (`AmazonVPCFullAccess`, `AmazonEKSServicePolicy`, `AmazonEC2FullAccess`, `AWSNetworkFirewallFullAccess`).
- **Xác Thực Đa Yếu Tố (MFA):** Bắt buộc kích hoạt cho tài khoản thực thi tác vụ.
- **Tiêu chuẩn khử trùng (Sanitization):** Thay thế 100% AWS Account ID 12 số bằng `123456789012`.

---

## 5. Phụ Thuộc (Dependencies)
- Tài khoản AWS đang hoạt động và quyền truy cập dòng lệnh (AWS CLI v2 / MCP).

---

## 6. Kiểm Tra Đạt (Verification)
- [x] Lệnh `aws sts get-caller-identity --region ap-southeast-1` trả về đúng IAM ARN đã khử trùng.
- [x] Lệnh `aws configure get region` trả về `ap-southeast-1`.
- [x] Bằng chứng runtime đã thu thập: [`evidence/00-inventory/01-caller-identity.json`](../../evidence/00-inventory/01-caller-identity.json).

---

## 7. Cảnh Báo An Toàn & Rollback Plan
- **Cảnh báo an toàn:** Không dùng tài khoản Root để thực thi các tác vụ triển khai hạ tầng.
- **Kế hoạch khôi phục (Rollback):** Thao tác chỉ đọc (Read-only), không yêu cầu rollback tài nguyên.
