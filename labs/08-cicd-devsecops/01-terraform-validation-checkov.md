# 08.01 — Tự Động Hóa Kiểm Thử Terraform & Quét An Ninh Hạ Tầng Với Checkov

> **Trạng thái:** Hướng dẫn triển khai kiểm thử tĩnh (Static Analysis) cho mã nguồn hạ tầng Terraform.  
> **Áp dụng cho:** Đảm bảo toàn bộ mã IaC tuân thủ các chính sách bảo mật đám mây nghiêm ngặt trước khi thực hiện apply.

---

## 1. Mục Tiêu Kỹ Thuật

- Tự động hóa kiểm tra định dạng và tính hợp lệ cú pháp (`terraform fmt -check`, `terraform validate`).
- Tích hợp công cụ quét an ninh **Checkov** (hoặc tfsec) để phát hiện các lỗi cấu hình nguy hiểm:
  - Security Group mở port SSH (22) hoặc RDP (3389) ra `0.0.0.0/0`.
  - Thiếu mã hóa dữ liệu KMS cho EKS Secrets hoặc Aurora Storage.
  - Thiếu cấu hình VPC Flow Logs trên các VPCs.
  - Subnet công khai bị bật tự động gán Public IP ngoài ý muốn.
- Thiết lập cơ chế chặn (Hard Gate): Nếu có bất kỳ lỗi **FAILED** nào ở mức độ HIGH hoặc CRITICAL, pipeline sẽ dừng lại lập tức.

---

## 2. Các Bước Thực Hiện Chi Tiết

### Bước 1: Kiểm Tra Cú Pháp & Quy Chuẩn Terraform
Chạy trong thư mục `terraform/` của repo hạ tầng:
```bash
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
```

---

### Bước 2: Chạy Quét An Ninh Checkov
Cài đặt và chạy Checkov quét toàn bộ thư mục Terraform:
```bash
# Cài đặt checkov
pip install checkov

# Chạy quét với bộ quy tắc AWS
checkov -d terraform/ \
  --framework terraform \
  --check CKV_AWS_20,CKV_AWS_23,CKV_AWS_24,CKV_AWS_130,CKV_AWS_158 \
  --compact \
  --output cli
```

Các quy tắc quan trọng cần đạt trạng thái **PASSED**:
- `CKV_AWS_23`: Đảm bảo Security Group không mở cổng 22 ra Internet.
- `CKV_AWS_158`: Đảm bảo KMS encryption được bật trên EKS Cluster.
- `CKV_AWS_130`: Đảm bảo VPC Flow Logs được bật trên toàn bộ VPCs.

---

## 3. Xác Minh (Verification)

Kiểm tra kết quả tổng kết của Checkov:
```text
Passed checks: 45, Failed checks: 0, Skipped checks: 0
Status: PASSED
```

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] `terraform validate` trả về `Success! The configuration is valid.`
- [ ] Báo cáo Checkov không còn lỗi vi phạm an ninh nghiêm trọng nào tồn tại.

