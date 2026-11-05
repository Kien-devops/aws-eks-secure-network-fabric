#!/usr/bin/env python3
"""Refactor Module 00 files to standard 7-section format and fix all issues."""

from pathlib import Path

BASE = Path("E:/repo/project6/aws-eks-secure-network-fabric/labs/00-chuan-bi-inventory")

# 01-account-region-identity.md
f1 = BASE / "01-account-region-identity.md"
f1.write_text("""# 00.01 — Xác Thực Danh Tính IAM, Region Singapore & Quyền Hạn Triển Khai

> **Mã bài lab:** `00.01`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 15 phút  
> **Chi phí ước tính:** $0.00 USD (Read-only API calls)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Tài khoản AWS có quyền AdministratorAccess hoặc nhóm quyền tương đương cho VPC, EC2, EKS, TGW, GWLB, Network Firewall.
- Thiết bị xác thực đa yếu tố (MFA) đã được gán và kích hoạt cho người dùng/role.
- Phiên làm việc AWS CLI hoặc kết nối MCP `aws-api-mcp/call_aws` sẵn sàng.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để thực thi bài lab này:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "iam:GetUser",
        "iam:ListMFADevices",
        "iam:GetAccountSummary"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Các lệnh gọi API trong bài lab này (`sts:GetCallerIdentity`, `iam:ListMFADevices`) hoàn toàn miễn phí.
- **Cảnh báo an toàn:** Tuyệt đối không sử dụng tài khoản root cho các bước triển khai tiếp theo. Đảm bảo mọi bằng chứng xuất ra phải che giấu AWS Account ID.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Khóa Cứng Vùng Hoạt Động (Region Selector)
1. Đăng nhập vào **AWS Management Console**.
2. Nhìn lên thanh điều hướng trên cùng bên phải, nhấp vào menu thả xuống chọn Region.
3. Chọn chính xác: **Asia Pacific (Singapore) `ap-southeast-1`**.
4. Xác nhận thanh URL hiển thị tham số `region=ap-southeast-1`.

### Bước 2: Kiểm Tra Danh Tính IAM Đang Đăng Nhập
1. Trên thanh tìm kiếm của AWS Console, gõ **IAM** -> Chọn dịch vụ **IAM**.
2. Tại bảng điều khiển IAM bên trái, nhấp vào **Users** (hoặc **Roles** nếu đăng nhập qua SSO/Federation).
3. Nhấp vào tên người dùng/role của bạn:
   - Kiểm tra tab **Permissions**: Xác nhận có policy AdministratorAccess hoặc chính sách mạng chuyên sâu.
   - Kiểm tra tab **Security credentials**: Xác nhận trạng thái **Multi-factor authentication (MFA)** đã được gán (`Assigned`).

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy các lệnh xác minh danh tính và vùng làm việc qua AWS CLI hoặc MCP Server (`aws-api-mcp/call_aws`):
```bash
# 1. Xác thực danh tính IAM
aws sts get-caller-identity --region ap-southeast-1 --output table

# 2. Xác thực cấu hình region mặc định
aws configure get region

# 3. Kiểm tra trạng thái MFA
aws iam list-mfa-devices --output table
```

> [!NOTE]
> Kết quả từ lệnh `sts get-caller-identity` trả về `Account`, `Arn`, `UserId`. Hãy kiểm tra và che giấu Account ID thành `123456789012` hoặc `***` trước khi lưu vào bằng chứng.

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Bài lab này là thao tác đọc (read-only), không tạo hay sửa đổi tài nguyên đám mây nào nên không yêu cầu hoàn tác. Nếu sai Region, người dùng chỉ cần chuyển lại selector sang `ap-southeast-1`.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/00-inventory/01-caller-identity.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] AWS Console hiển thị đúng vùng `ap-southeast-1` (Singapore).
- [ ] Lệnh `sts get-caller-identity` trả về ARN hợp lệ với `UserId` rõ ràng.
- [ ] MFA đang hoạt động trên danh tính đăng nhập.
- [ ] Account ID được che giấu trong toàn bộ file bằng chứng xuất ra.
""", encoding="utf-8")

# 02-naming-tagging-budget.md
f2 = BASE / "02-naming-tagging-budget.md"
f2.write_text("""# 00.02 — Quy Chuẩn Đặt Tên (Naming), Gắn Nhãn (Tagging) & Thiết Lập AWS Budgets ($50.00)

> **Mã bài lab:** `00.02`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 20 phút  
> **Chi phí ước tính:** $0.00 USD (AWS Budgets miễn phí 2 ngân sách đầu tiên)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bài lab [00.01 — Xác Thực Danh Tính IAM](01-account-region-identity.md).
- Email nhận thông báo cảnh báo chi phí khả dụng.
- Quyền tạo AWS Budgets trong IAM.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để thực thi bài lab này:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "budgets:ViewBudget",
        "budgets:ModifyBudget",
        "ce:GetCostAndUsage"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** AWS cho phép tạo miễn phí 2 ngân sách đầu tiên mỗi tháng. Dự án Project 6 chỉ sử dụng 1 ngân sách duy nhất (`fabric-project6-monthly-budget`).
- **Cảnh báo FinOps:** Khi chi phí chạm mốc 80% ($40 USD), quản trị viên phải lập tức rà soát và sẵn sàng kích hoạt quy trình dọn dẹp tại Module 12 nếu là môi trường thử nghiệm GameDay.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Mở Bảng Điều Khiển AWS Budgets
1. Trên thanh tìm kiếm Console, nhập **Budgets** -> Chọn dịch vụ **AWS Budgets**.
2. Tại menu bên trái, nhấp vào **Budgets** -> Nhấp nút cam **Create budget**.

### Bước 2: Thiết Lập Thông Số Ngân Sách ($50.00 USD)
1. Chọn **Customize (advanced)** -> Chọn **Cost budget - Recommended** -> Nhấp **Next**.
2. **Budget details:**
   - **Budget name:** Nhập `fabric-project6-monthly-budget`.
   - **Period:** Chọn `Monthly`.
   - **Budget effective date:** Chọn `Recurring budget`.
   - **Budget method:** Chọn `Fixed`.
   - **Enter your budgeted amount ($):** Nhập `50`.
3. **Budget scope:** Chọn `All AWS services`.
4. Nhấp **Next** sang bước cấu hình cảnh báo (Alerts).

### Bước 3: Cấu Hình 2 Ngưỡng Cảnh Báo Sớm
1. **Ngưỡng 1 (80% Thực tế):**
   - Threshold: `80` % of budgeted amount ($40.00).
   - Trigger: `Actual`.
   - Email recipients: Nhập email quản trị viên.
2. **Ngưỡng 2 (100% Dự báo):**
   - Nhấp **Add alert threshold**.
   - Threshold: `100` % of budgeted amount ($50.00).
   - Trigger: `Forecasted`.
   - Email recipients: Nhập email quản trị viên.
3. Nhấp **Next** -> Xem lại tổng quan và nhấp **Create budget**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy các lệnh xác minh trạng thái ngân sách và gắn nhãn qua AWS CLI hoặc MCP Server (`aws-api-mcp/call_aws`):
```bash
# 1. Kiểm tra danh sách Budgets trên tài khoản (thay 123456789012 bằng Account ID thực tế của bạn khi chạy)
aws budgets describe-budgets \
  --account-id 123456789012 \
  --query 'Budgets[*].{Name:BudgetName,Limit:BudgetLimit.Amount,Unit:BudgetLimit.Unit,Type:BudgetType}' \
  --output table

# 2. Kiểm tra chi tiết cảnh báo của ngân sách fabric-project6-monthly-budget
aws budgets describe-notifications-for-budget \
  --account-id 123456789012 \
  --budget-name fabric-project6-monthly-budget \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Nếu cần xóa hoặc chỉnh sửa ngân sách đã tạo:
1. Truy cập **AWS Budgets Console** -> Chọn checkbox trước `fabric-project6-monthly-budget`.
2. Nhấp menu **Actions** -> Chọn **Delete** -> Xác nhận xóa.
3. Hoặc chạy CLI:
   ```bash
   aws budgets delete-budget --account-id 123456789012 --budget-name fabric-project6-monthly-budget
   ```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/00-inventory/02-budget-status.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Ngân sách `fabric-project6-monthly-budget` ở trạng thái Active với giới hạn $50.00 USD.
- [ ] 2 ngưỡng thông báo (80% actual, 100% forecasted) được kích hoạt với email nhận tin hợp lệ.
- [ ] Quy ước tiền tố `fabric-*` và bộ Cost Allocation Tags được ghi nhận đầy đủ.
""", encoding="utf-8")

# 03-evidence-hygiene-sanitization.md
f3 = BASE / "03-evidence-hygiene-sanitization.md"
f3.write_text("""# 00.03 — Quy Chuẩn Thu Thập Bằng Chứng (Evidence) & Khử Trùng Dữ Liệu (Sanitization)

> **Mã bài lab:** `00.03`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 15 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab [00.01](01-account-region-identity.md) và [00.02](02-naming-tagging-budget.md).
- Máy tính trạm có sẵn Python 3.x hoặc công cụ sed/awk để thực hiện khử trùng dữ liệu log tự động.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Bài lab này là quy trình chuẩn hóa và kiểm toán dữ liệu cục bộ, không yêu cầu phân quyền IAM đặc thù trên AWS.

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Hoàn toàn miễn phí ($0.00 USD).
- **Cảnh báo an ninh tối mật:** Tuyệt đối không commit Access Keys, Secret Keys, Private Key, Database Password hoặc AWS Account ID thực tế lên GitHub. Bất kỳ sự cố rò rỉ nào sẽ làm mất tính an toàn của dự án.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Thiết Lập Thư Mục Lưu Trữ Bằng Chứng
1. Mở terminal tại thư mục gốc repository `aws-eks-secure-network-fabric`.
2. Tạo cấu trúc thư mục evidence phân tách theo từng module:
   ```bash
   mkdir -p evidence/00-inventory evidence/02-network evidence/03-eks evidence/05-gwlb evidence/06-firewall evidence/10-gameday
   ```

### Bước 2: Thiết Lập Quy Trình Khử Trùng Tự Động (Sanitization Script)
Tạo script `scripts/sanitize-evidence.py` để tự động duyệt qua toàn bộ file JSON/TXT/LOG trong thư mục `evidence/` và thay thế:
- Account ID 12 chữ số thực tế -> `123456789012`
- Access Keys `AKIA...` -> `AKIA***REDACTED***`
- Secrets/Passwords -> `***REDACTED***`

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy script kiểm tra khử trùng và đối soát các file evidence hiện có:
```bash
# 1. Kiểm tra sự tồn tại của chuỗi Account ID chưa khử trùng
grep -rE "\b(?!123456789012\b)[0-9]{12}\b" evidence/ || echo "Sanitization check PASSED: No sensitive Account IDs found."

# 2. Kiểm tra sự tồn tại của AWS Access Key
grep -rE "AKIA[0-9A-Z]{16}" evidence/ || echo "Sanitization check PASSED: No AWS Access Keys found."
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Nếu vô tình commit file chứa thông tin nhạy cảm vào Git history:
1. Lập tức thu hồi (Revoke) và xoay vòng (Rotate) ngay Access Key / Secret trên AWS IAM.
2. Dùng công cụ `git-filter-repo` hoặc BFG Repo-Cleaner để loại bỏ hoàn toàn commit chứa bí mật khỏi lịch sử git.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/00-inventory/03-sanitization-audit.log`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Không có chuỗi khóa bí mật, mật khẩu cơ sở dữ liệu hay token nào tồn tại trong git commits.
- [ ] Account ID được thay thế 100% bằng `123456789012` hoặc `***`.
- [ ] Thư mục bằng chứng `evidence/` được phân nhóm rõ ràng theo từng module.
""", encoding="utf-8")

print("Module 00 rewritten successfully.")
