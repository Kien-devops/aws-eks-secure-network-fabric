# 03.01 — Đặc Tả Khóa Mã Hóa AWS KMS Customer Managed Key Cho EKS Secrets

> **Mã bài lab:** `03.01`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/03-eks/01-kms-keys.json`

---

## 1. Mục Tiêu (Objective)

Khởi tạo 2 khóa mã hóa đối xứng AWS KMS Customer Managed Key (CMK) riêng biệt cho 2 cụm EKS (Edge và Core) tại Singapore kèm tính năng tự động xoay khóa hàng năm nhằm phục vụ mã hóa phong bì (Envelope Encryption) cho Kubernetes Secrets tại tầng lưu trữ etcd.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Vị Trí / Khu Vực | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `alias/fabric-edge-eks-secrets` | `AWS::KMS::Key` & `Alias` | `ap-southeast-1` | Key ID: `042b4054-bf6d-4741-8eb8-c28d745a05b8`<br>ARN: `arn:aws:kms:ap-southeast-1:123456789012:key/042b4054-bf6d-4741-8eb8-c28d745a05b8` |
| `alias/fabric-core-eks-secrets` | `AWS::KMS::Key` & `Alias` | `ap-southeast-1` | Key ID: `e5634732-898f-4b32-b81a-5dc578596ebb`<br>ARN: `arn:aws:kms:ap-southeast-1:123456789012:key/e5634732-898f-4b32-b81a-5dc578596ebb` |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `alias/fabric-edge-eks-secrets` / `alias/fabric-core-eks-secrets` | Khóa Edge KMS và Core KMS |
| `Project` | `aws-eks-secure-network-fabric` | Khóa Edge KMS và Core KMS |
| `Environment` | `prod` | Khóa Edge KMS và Core KMS |
| `ManagedBy` | `manual` | Quản trị cấu hình khóa thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Thuộc Tính Kỹ Thuật Khóa KMS

| Thuộc Tính | Giá Trị Cấu Hình | Lý Do Thiết Kế |
| :--- | :--- | :--- |
| **Key Spec** | `SYMMETRIC_DEFAULT` (AES-256-GCM) | Chuẩn mã hóa bắt buộc cho EKS Secret Envelope Encryption. |
| **Key Usage** | `ENCRYPT_DECRYPT` | Mã hóa và giải mã dữ liệu Secrets etcd. |
| **Origin** | `AWS_KMS` | Key material do AWS KMS tự sinh và bảo vệ an toàn trong FIPS 140-2 HSM. |
| **Regionality** | Single-Region (`ap-southeast-1`) | Giữ toàn bộ dữ liệu và khóa mã hóa tại Singapore, tránh rủi ro phân mảnh. |
| **Automatic Key Rotation** | `true` (365 ngày) | Tuân thủ tiêu chuẩn tuân thủ bảo mật CIS AWS Foundations Benchmark. |

### 4.2 Key Policy Requirements

Key Policy của mỗi khóa bắt buộc cấp quyền cho root account và dịch vụ EKS:
- **Actions cho EKS Service:** `kms:Encrypt`, `kms:Decrypt`, `kms:ReEncrypt*`, `kms:GenerateDataKey*`, `kms:DescribeKey`.
- **Principal:** IAM Role thực thi EKS Cluster và IAM Users/Roles quản trị viên.

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `00.01` (xác thực tài khoản và vùng `ap-southeast-1`).
- Là điều kiện tiên quyết bắt buộc trước bài lab `03.02` (EKS Cluster khởi tạo cần truyền KMS Key ARN để bật envelope encryption).

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng thái 2 Khóa** | `aws kms describe-key --key-id alias/fabric-edge-eks-secrets` và `alias/fabric-core-eks-secrets` | `KeyState: Enabled`, `KeySpec: SYMMETRIC_DEFAULT`. |
| **Key Rotation** | `aws kms get-key-rotation-status --key-id <KeyId>` | `KeyRotationEnabled: true`. |
| **KMS Aliases** | `aws kms list-aliases --query "Aliases[?starts_with(AliasName, 'alias/fabric-')]"` | Hiển thị cả 2 alias trỏ đúng về TargetKeyId tương ứng. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo mất dữ liệu:** Không xóa hoặc hủy quyền khóa KMS khi cụm EKS đang chạy. Nếu khóa bị vô hiệu hóa hoặc xóa, etcd sẽ không thể giải mã Secret, dẫn đến Pods sụp đổ và cluster hỏng hoàn toàn.
- **Quy trình Rollback:**
  ```bash
  # Lên lịch xóa khóa với thời gian chờ an toàn 7 ngày
  aws kms schedule-key-deletion --region ap-southeast-1 --key-id 042b4054-bf6d-4741-8eb8-c28d745a05b8 --pending-window-in-days 7
  aws kms schedule-key-deletion --region ap-southeast-1 --key-id e5634732-898f-4b32-b81a-5dc578596ebb --pending-window-in-days 7
  ```
