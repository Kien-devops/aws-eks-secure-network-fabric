# 00.03 — Quy Chuẩn Thu Thập Bằng Chứng (Evidence) & Khử Trùng Dữ Liệu (Sanitization)

> **Trạng thái:** Hướng dẫn quy chuẩn an ninh và vệ sinh bằng chứng kỹ thuật.  
> **Áp dụng cho:** Toàn bộ quá trình thu thập log, xuất kết quả lệnh CLI, chụp màn hình và lưu trữ tài liệu trong Project 6.

---

## 1. Mục Tiêu & Tôn Chỉ Bằng Chứng

- **Mục tiêu:**
  - Thiết lập tiêu chuẩn **Zero Fake Data**: Mọi bảng log, kết quả lệnh `describe`, latency và packet trace phải là dữ liệu thực tế thu thập từ môi trường runtime có gắn dấu thời gian (Timestamp ISO 8601).
  - Áp dụng quy chuẩn **Sanitization 100%**: Loại bỏ triệt để mọi thông tin nhạy cảm trước khi commit lên GitHub hoặc lưu trữ lâu dài.

---

## 2. Danh Mục Dữ Liệu Bắt Buộc Khử Trùng (Redaction Checklist)

| Loại Thông Tin | Mẫu Dữ Liệu Thực Tế | Mẫu Dữ Liệu Sau Khi Khử Trùng (Redacted) |
|---|---|---|
| **AWS Account ID** | `112233445566` | `123456789012` hoặc `***` |
| **IAM Access Key ID** | `AKIAIOSFODNN7EXAMPLE` | `AKIA***REDACTED***` |
| **Secret Access Key** | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` | `***REDACTED_SECRET_KEY***` |
| **KMS Key ID / Secret ARN**| `arn:aws:kms:ap-southeast-1:112233445566:key/abc-123` | `arn:aws:kms:ap-southeast-1:123456789012:key/fabric-cmk` |
| **Database Credentials** | `postgres://admin:SuperSecretPass123@...` | `postgres://admin:***REDACTED_DB_PASS***@...` |
| **JWT Secrets / Tokens** | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` | `eyJhbGciOiJIUzI1Ni...[REDACTED_JWT_TOKEN]` |

---

## 3. Quy Trình Thu Thập Bằng Chứng 3 Bước

1. **Bước 1: Trích xuất trực tiếp:**
   Chạy lệnh AWS CLI / kubectl kèm định dạng xuất chuẩn (JSON hoặc Table):
   ```bash
   aws ec2 describe-vpcs --region ap-southeast-1 --output json > raw-vpcs.json
   ```
2. **Bước 2: Chạy khử trùng dữ liệu:**
   Thay thế các chuỗi Account ID hoặc Secret bằng regex an toàn trước khi lưu vào thư mục `evidence/`.
3. **Bước 3: Đối soát chất lượng:**
   Đảm bảo file log giữ nguyên cấu trúc JSON/Table hợp lệ, có timestamp rõ ràng chứng minh thời điểm thực thi.

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Không có chuỗi khóa bí mật, mật khẩu cơ sở dữ liệu hay token nào tồn tại trong git commits.
- [ ] Mọi log output đều có timestamp thực tế từ Region Singapore `ap-southeast-1`.
