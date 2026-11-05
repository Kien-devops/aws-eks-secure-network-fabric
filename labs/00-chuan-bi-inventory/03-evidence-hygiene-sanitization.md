# 00.03 — Quy Chuẩn Thu Thập Bằng Chứng (Evidence) & Khử Trùng Dữ Liệu (Sanitization)

> **Mã bài lab:** `00.03`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 15 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab [00.01](01-account-region-identity.md) và [00.02](02-naming-tagging-budget.md).
- Máy tính trạm có sẵn Python 3.x hoặc công cụ sed/awk/PowerShell để thực hiện khử trùng dữ liệu log tự động.
- Trình duyệt truy cập AWS Console tại Singapore `ap-southeast-1`.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết cho việc tạo bucket lưu trữ bằng chứng nội bộ và kiểm tra log:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:PutBucketPublicAccessBlock",
        "s3:PutBucketEncryption",
        "s3:PutBucketVersioning",
        "s3:ListBucket",
        "s3:PutObject"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Hoàn toàn miễn phí ($0.00 USD) cho các script chạy local; chi phí lưu trữ S3 chỉ vài cent/tháng.
- **Cảnh báo an ninh tối mật:** Tuyệt đối không commit Access Keys, Secret Keys, Private Key, Database Password hoặc AWS Account ID thực tế lên GitHub. Bất kỳ sự cố rò rỉ nào sẽ làm mất tính an toàn của dự án. Mọi file xuất ra phải qua bộ lọc sanitization.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Khởi Tạo S3 Bucket Lưu Trữ Bằng Chứng Riêng Tư (Console)
1. Đăng nhập vào **AWS Management Console**, chọn Region Singapore `ap-southeast-1`.
2. Trên thanh tìm kiếm, nhập `S3` và chọn dịch vụ **S3**.
3. Tại bảng điều khiển S3, nhấp nút cam **Create bucket**.
4. **General configuration:**
   - **AWS Region:** Chọn `Asia Pacific (Singapore) ap-southeast-1`.
   - **Bucket type:** Chọn `General purpose`.
   - **Bucket name:** Nhập `fabric-evidence-vault-123456` (đổi đuôi số ngẫu nhiên để duy nhất toàn cầu).
5. **Object Ownership:** Chọn `ACLs disabled (recommended)`.
6. **Block Public Access settings for this bucket:**
   - Đánh dấu tích vào `Block all public access` (Khóa toàn bộ truy cập công khai).
   - Đánh dấu xác nhận vào ô cảnh báo an toàn.
7. **Bucket Versioning:** Chọn `Enable` (để bảo toàn lịch sử bằng chứng, ngăn chặn ghi đè sửa đổi).
8. **Default encryption:**
   - Encryption type: Chọn `Server-side encryption with Amazon S3 managed keys (SSE-S3)`.
   - Bucket Key: Chọn `Enable`.
9. Nhấp nút cam **Create bucket** ở cuối trang.

### Bước 2: Thiết Lập Thư Mục Lưu Trữ Bằng Chứng Cục Bộ (Local Workspace)
1. Mở terminal tại thư mục gốc repository `aws-eks-secure-network-fabric`.
2. Tạo cấu trúc thư mục evidence phân tách chuẩn mực theo 12 module:
   ```bash
   mkdir -p evidence/00-inventory \
            evidence/01-threat-model \
            evidence/02-network \
            evidence/03-eks \
            evidence/04-workloads \
            evidence/05-gwlb \
            evidence/06-firewall \
            evidence/07-waf \
            evidence/08-devsecops \
            evidence/09-observability \
            evidence/10-gameday \
            evidence/11-report \
            evidence/12-cleanup
   ```

### Bước 3: Thiết Lập Script Khử Trùng Dữ Liệu Tự Động (Sanitization Script)
Tạo file script Python `scripts/sanitize-evidence.py` để duyệt qua toàn bộ file bằng chứng trước khi commit:
```python
#!/usr/bin/env python3
import os
import re

PATTERNS = [
    (r"\b\d{12}\b", "123456789012"),                     # Che giấu Account ID 12 chữ số
    (r"AKIA[0-9A-Z]{16}", "AKIA***REDACTED***"),          # Che giấu AWS Access Key ID
    (r"\"Password\":\s*\"[^\"]+\"", "\"Password\": \"***REDACTED***\""), # Mật khẩu
    (r"Bearer\s+[A-Za-z0-9\-_\.]+", "Bearer ***REDACTED***") # JWT Bearer Tokens
]

def sanitize_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    new_content = content
    for pattern, replacement in PATTERNS:
        new_content = re.sub(pattern, replacement, new_content)
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"[SANITIZED] {filepath}")

for root, _, files in os.walk("evidence"):
    for file in files:
        if file.endswith((".json", ".log", ".txt", ".md")):
            sanitize_file(os.path.join(root, file))
```

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy script kiểm tra khử trùng và đối soát các file evidence hiện có:
```bash
# 1. Chạy script khử trùng
python scripts/sanitize-evidence.py

# 2. Kiểm tra sự tồn tại của chuỗi Account ID chưa khử trùng (phải trả về PASSED)
grep -rE "\b(?!123456789012)[0-9]{12}\b" evidence/ || echo "Sanitization check PASSED: No sensitive Account IDs found."

# 3. Kiểm tra sự tồn tại của AWS Access Key
grep -rE "AKIA[0-9A-Z]{16}" evidence/ || echo "Sanitization check PASSED: No AWS Access Keys found."
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Nếu vô tình commit file chứa thông tin nhạy cảm vào Git history:
1. Lập tức thu hồi (Revoke) và xoay vòng (Rotate) ngay Access Key / Secret trên AWS IAM.
2. Dùng công cụ `git-filter-repo` hoặc BFG Repo-Cleaner để loại bỏ hoàn toàn commit chứa bí mật khỏi lịch sử git.
3. Nếu xóa S3 Bucket lưu trữ bằng chứng:
   ```bash
   aws s3 rb s3://fabric-evidence-vault-123456 --force --region ap-southeast-1
   ```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/00-inventory/03-sanitization-audit.log`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] S3 Bucket `fabric-evidence-vault-*` được tạo với Block Public Access = ENABLED và SSE-S3.
- [ ] Không có chuỗi khóa bí mật, mật khẩu cơ sở dữ liệu hay token nào tồn tại trong git commits.
- [ ] Account ID được thay thế 100% bằng `123456789012` hoặc `***`.
- [ ] Thư mục bằng chứng `evidence/` được phân nhóm rõ ràng theo 12 modules.
