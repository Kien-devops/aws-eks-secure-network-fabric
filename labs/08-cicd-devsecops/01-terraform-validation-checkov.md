# 08.01 — Tự Động Hóa Kiểm Thử Terraform & Quét An Ninh Hạ Tầng Với Checkov

> **Mã bài lab:** `08.01`  
> **Trạng thái:** `DRAFT`  
> **Thời gian dự kiến:** 30 phút  
> **Chi phí ước tính:** $0.00 USD (Chạy cục bộ hoặc trong GitHub Actions / AWS CodePipeline)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã cài đặt Terraform CLI v1.5+ và Python 3.9+ trên máy trạm.
- Mã nguồn IaC của dự án đã sẵn sàng trong thư mục `terraform/`.

> **Gate artifact:** repo hiện chưa có `terraform/`; bài chưa chạy được. Hoàn thiện IaC và mapping tài nguyên live/import plan trong nhiệm vụ riêng. Không chạy apply/import trong bài kiểm tra tĩnh; validate thư mục rỗng không chứng minh hạ tầng an toàn.
- Đã cài đặt công cụ quét tĩnh an ninh `checkov`.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Bài lab thực hiện kiểm thử tĩnh mã nguồn IaC cục bộ và kiểm tra kết quả trên AWS Security Hub / CodePipeline (nếu tích hợp CI/CD):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "securityhub:BatchImportFindings",
        "securityhub:GetFindings"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD.
- **Cảnh báo Shift-Left Security:** Bất kỳ lỗi vi phạm an ninh nghiêm trọng nào (mở SSH ra 0.0.0.0/0, thiếu mã hóa KMS, thiếu VPC Flow Logs) phải được chặn đứng ngay từ bước Pull Request trước khi lệnh `terraform apply` được thực thi trên môi trường AWS thực tế.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console & Terminal (Console Walkthrough)

### Bước 1: Kiểm Tra Định Dạng & Tính Hợp Lệ Cú Pháp Terraform
1. Mở terminal tại thư mục gốc repository `aws-eks-secure-network-fabric`.
2. Chuyển vào thư mục chứa mã nguồn hạ tầng:
   ```bash
   cd terraform/
   ```
3. Chạy lệnh kiểm tra định dạng mã nguồn theo chuẩn HashiCorp:
   ```bash
   terraform fmt -check -recursive
   ```
   *(Nếu có file chưa đúng chuẩn thụt lề, chạy `terraform fmt -recursive` để tự động sửa).*
4. Khởi tạo Terraform không cần backend từ xa để kiểm tra cú pháp:
   ```bash
   terraform init -backend=false
   terraform validate
   ```
   Xác nhận màn hình trả về: **`Success! The configuration is valid.`**

---

### Bước 2: Cài Đặt & Chạy Bộ Quét An Ninh Checkov
1. Cài đặt Checkov bằng `pip`:
   ```bash
   pip install checkov
   ```
2. Chạy quét toàn bộ module Terraform với bộ kiểm tra nghiêm ngặt cho AWS EKS và Networking:
   ```bash
   checkov -d . \
     --framework terraform \
     --check CKV_AWS_20,CKV_AWS_23,CKV_AWS_24,CKV_AWS_130,CKV_AWS_158,CKV_AWS_260 \
     --compact \
     --output cli
   ```
3. **Danh mục các quy tắc an ninh cốt lõi cần đạt PASSED:**
   - **`CKV_AWS_23`:** Đảm bảo Security Group không mở cổng SSH (22) ra toàn bộ thế giới `0.0.0.0/0`.
   - **`CKV_AWS_158`:** Đảm bảo EKS Cluster bật tính năng Secret Envelope Encryption với AWS KMS.
   - **`CKV_AWS_130`:** Đảm bảo tất cả VPCs đều kích hoạt VPC Flow Logs.
   - **`CKV_AWS_260`:** Đảm bảo Ingress Security Group không mở tất cả các cổng (`-1` protocol).

---

### Bước 3: Xuất Báo Cáo Định Dạng JUnit XML & JSON Cho CI/CD Pipeline
1. Chạy xuất báo cáo kết quả quét định dạng JSON để lưu trữ làm bằng chứng:
   ```bash
   checkov -d . \
     --framework terraform \
     --output json \
     --output-file-path ../evidence/08-devsecops/
   ```
2. Đổi tên file báo cáo thành `evidence/08-devsecops/01-checkov-report.json`.

---

### Bước 4: Quan Sát Trạng Thái Tích Hợp Trên AWS Security Hub Console (Tùy Chọn)
1. Đăng nhập **AWS Management Console**, chọn Region Singapore `ap-southeast-1`.
2. Mở dịch vụ **AWS Security Hub** -> Chọn **Findings**.
3. Lọc theo Provider: `Checkov` hoặc `IaC Scanner` (nếu pipeline đẩy kết quả lên Security Hub qua API `BatchImportFindings`).
4. Xác nhận không có finding nào ở mức độ `CRITICAL` hoặc `HIGH`.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra kết quả tổng kết của Checkov:
```bash
# Kiểm tra số lượng lỗi FAILED trong báo cáo JSON
jq '{passed: .summary.passed, failed: .summary.failed, skipped: .summary.skipped}' evidence/08-devsecops/01-checkov-report.json
```
**Kết quả kỳ vọng:** `failed: 0`.

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Nếu Checkov phát hiện lỗi vi phạm an ninh:
1. Đọc kỹ file và dòng code gây lỗi trong log Checkov.
2. Sửa trực tiếp mã Terraform (ví dụ: đóng cổng 22, bật KMS encryption block).
3. Chạy lại `checkov` cho đến khi toàn bộ checks đạt `PASSED`.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/08-devsecops/01-checkov-report.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Lệnh `terraform validate` trả về `Success! The configuration is valid.`
- [ ] Báo cáo Checkov không còn bất kỳ lỗi nào ở mức độ `CRITICAL` hoặc `HIGH` (`failed: 0`).
- [ ] Quy chuẩn đặt tên `fabric-*` và mã hóa KMS được kiểm tra đầy đủ.
