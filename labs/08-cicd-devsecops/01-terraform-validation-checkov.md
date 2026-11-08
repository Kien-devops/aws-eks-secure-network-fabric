# 08.01 — Đặc Tả Kiểm Thử Terraform & Quét An Ninh Hạ Tầng Với Checkov

> **Mã bài lab:** `08.01`
> **Trạng thái tài liệu:** `READY_TO_RUN`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/08-devsecops/01-checkov-report.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả quy trình kiểm thử tĩnh tự động hóa định dạng cú pháp HCL và phân tích an ninh mã nguồn hạ tầng (SAST IaC) bằng Checkov trước khi hợp nhất Pull Request, đảm bảo tuân thủ các chuẩn mã hóa KMS, không mở cổng SSH và kích hoạt VPC Flow Logs.

*Lưu ý phạm vi kiến trúc:* Bài lab này thuần túy kiểm tra an ninh tĩnh (Static IaC Code Analysis & Linting), **tuyệt đối không thực thi `terraform apply`** hay triển khai tự động lên hạ tầng đám mây. Toàn bộ tài nguyên AWS Cloud trên thực tế trong dự án này được tạo và quản trị thủ công 100% qua AWS Console/CLI (`ManagedBy=manual`).

---

## 2. Tài Nguyên (Resources)

| Tên Tài Nguyên | Loại Resource | Phạm Vi Áp Dụng | Mô Tả Kỹ Thuật |
| :--- | :--- | :--- | :--- |
| `terraform/` | `IaC::HCL` | Repository Workspace | Mã nguồn định nghĩa VPC, TGW, EKS, GWLB, NFW |
| `checkov` | `Security::SAST` | CI/CD Runner / CLI | Bộ quét lỗ hổng cấu hình tĩnh IaC |
| `01-checkov-report.json` | `Artifact::Evidence` | `evidence/08-devsecops/` | Báo cáo kết quả quét định dạng JSON |

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-*` | Toàn bộ tài nguyên quản trị |
| `Project` | `aws-eks-secure-network-fabric` | Quy chuẩn gán thẻ bắt buộc |
| `Environment` | `prod` | Phân vùng môi trường chính thức |
| `ManagedBy` | `manual` | Quản lý quy trình kiểm định thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Quy Trình Kiểm Thử Cú Pháp HCL

- **Format Check:** `terraform fmt -check -recursive` (Bảo đảm tính đồng nhất định dạng mã).
- **Validation:** `terraform init -backend=false && terraform validate` (Kiểm tra cú pháp tham chiếu biến, type và schema).

### 4.2 Bộ Quy Tắc An Ninh Trọng Yếu (Checkov Policy Baseline)

| Mã Checkov | Tên Quy Tắc | Yêu Cầu An Ninh Cốt Lõi | Hành Vi Ngắt Pipeline |
| :--- | :--- | :--- | :---: |
| **`CKV_AWS_23`** | SG SSH 0.0.0.0/0 | Cấm mở cổng 22 ra toàn thế giới. | `FAIL` |
| **`CKV_AWS_158`** | EKS Secrets Encryption | Bắt buộc bật KMS envelope encryption cho etcd secrets. | `FAIL` |
| **`CKV_AWS_130`** | VPC Flow Logs Enabled | Toàn bộ VPCs bắt buộc phải cấu hình nạp Flow Logs. | `FAIL` |
| **`CKV_AWS_260`** | Ingress All Traffic Drop | Cấm mở toàn bộ cổng (`-1` all traffic) trên ingress SG. | `FAIL` |

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào mã nguồn Terraform tại thư mục `terraform/`.
- Là rào chắn kiểm soát chất lượng (Quality Gate) bắt buộc trước khi triển khai pipeline CI/CD tại `08.04`.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Cú pháp Terraform** | `terraform validate` | `Success! The configuration is valid.` |
| **Báo cáo Checkov** | Phân tích tệp JSON báo cáo Checkov | `summary.failed: 0` (Không có lỗi CRITICAL hoặc HIGH). |
| **Tự Động Hóa CI** | Chạy workflow kiểm thử trong GitHub Actions | Bước `Checkov Scan` đạt tick xanh `passed`. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo Shift-Left:** Bất kỳ thay đổi hạ tầng nào vi phạm baseline bảo mật đều bị chặn ngay tại bước Pull Request, ngăn chặn hoàn toàn rủi ro cấu hình sai lọt vào môi trường AWS thực tế.
- **Quy trình Rollback:**
  ```bash
  # Hoàn tác commit gây lỗi trong nhánh feature
  git reset --hard HEAD~1
  ```
