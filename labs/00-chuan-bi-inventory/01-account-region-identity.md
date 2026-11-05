# 00.01 — Xác Thực Danh Tính IAM, Region Singapore & Quyền Hạn Triển Khai

> **Mã bài lab:** `00.01`  
> **Trạng thái:** `RUNTIME_PASS`  
> **Thời gian dự kiến:** 15 phút  
> **Chi phí ước tính:** $0.00 USD (Thao tác chỉ đọc / Read-only API calls)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã có tài khoản AWS đang hoạt động với quyền quản trị viên IAM hoặc vai trò quản trị viên mạng/hạ tầng (`AdministratorAccess` hoặc tương đương).
- Thiết bị xác thực đa yếu tố (MFA) đã được gán và kích hoạt cho người dùng/role.
- Trình duyệt web hỗ trợ truy cập AWS Management Console.
- Phiên làm việc AWS CLI hoặc kết nối MCP `aws-api-mcp/call_aws` sẵn sàng trên máy trạm.

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
        "iam:GetAccountSummary",
        "iam:ListAttachedUserPolicies",
        "iam:ListUserPolicies"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Các thao tác đọc thông tin danh tính và trạng thái tài khoản là hoàn toàn miễn phí ($0.00 USD).
- **Cảnh báo an toàn (Zero Fake Data & Sanitization):** Tuyệt đối không sử dụng tài khoản Root để thực thi các tác vụ hạ tầng. Trong mọi bằng chứng lưu trữ hoặc chia sẻ, AWS Account ID thực tế gồm 12 chữ số bắt buộc phải được che giấu hoặc thay bằng `123456789012` hoặc `***`.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Khóa Cứng Vùng Hoạt Động (Region Selector)
1. Đăng nhập vào **AWS Management Console** bằng trình duyệt web.
2. Nhìn lên thanh điều hướng trên cùng (Top Navigation Bar), phía bên phải, nhấp vào menu thả xuống chọn Region (mặc định có thể đang ở `N. Virginia us-east-1` hoặc region trước đó).
3. Trong danh sách các vùng AWS, tìm và chọn: **Asia Pacific (Singapore) `ap-southeast-1`**.
4. Quan sát trên thanh địa chỉ của trình duyệt, xác nhận URL chứa tham số:
   `region=ap-southeast-1`
5. Nhấp vào tên tài khoản ở góc trên cùng bên phải, ghi nhận **Account ID** nội bộ (chuẩn bị che giấu khi lưu trữ bằng chứng).

### Bước 2: Kiểm Tra Danh Tính & Quyền Hạn Trong IAM Console
1. Trên thanh tìm kiếm chính (Search Bar) ở đầu trang AWS Console, nhập từ khóa `IAM` và chọn dịch vụ **IAM (Identity and Access Management)**.
2. Tại menu điều hướng bên trái (Navigation Pane), nhấp chọn **Users** (hoặc chọn **Roles** nếu bạn đăng nhập thông qua AWS IAM Identity Center / SSO).
3. Trong danh sách người dùng, nhấp vào tên người dùng của bạn (ví dụ: `admin-devops` hoặc `kien-architect`).
4. Tại trang chi tiết người dùng:
   - Chọn tab **Permissions**:
     - Kiểm tra phần **Permissions policies**. Xác nhận có chính sách `AdministratorAccess` hoặc các chính sách quản trị mạng nâng cao (`AmazonVPCFullAccess`, `AmazonEKSServicePolicy`, `AmazonEC2FullAccess`).
     - Xác nhận quyền hạn có hiệu lực trực tiếp hoặc kế thừa từ User Group hợp lệ.
   - Chọn tab **Security credentials**:
     - Cuộn xuống mục **Multi-factor authentication (MFA)**.
     - Xác nhận trường **Status** hiển thị biểu tượng tích xanh hoặc dòng chữ `Assigned` (Đã gán thiết bị MFA ảo hoặc khóa bảo mật phần cứng FIDO/WebAuthn).
     - Nếu chưa kích hoạt MFA, nhấp **Assign MFA device**, làm theo hướng dẫn quét mã QR trên ứng dụng Authenticator để kích hoạt ngay lập tức.

### Bước 3: Kiểm Tra Bảng Điều Khiển Tài Khoản (Account Dashboard)
1. Tại menu điều hướng bên trái của IAM Console, nhấp vào **Dashboard**.
2. Kiểm tra phần **Security recommendations**:
   - Xác nhận mục **Root user has MFA** có dấu tích xanh.
   - Xác nhận quyền truy cập của tài khoản không tồn tại các khóa truy cập root (Root access keys).

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy các lệnh xác minh danh tính và vùng làm việc qua AWS CLI hoặc MCP Server (`aws-api-mcp/call_aws`):
```bash
# 1. Xác thực danh tính IAM hiện tại (Account ID, ARN, UserId)
aws sts get-caller-identity --region ap-southeast-1 --output table

# 2. Xác thực cấu hình region mặc định của AWS CLI
aws configure get region

# 3. Kiểm tra danh sách thiết bị MFA đã đăng ký cho người dùng
aws iam list-mfa-devices --output table
```

> [!NOTE]
> Kết quả từ lệnh `sts get-caller-identity` trả về `Account`, `Arn`, `UserId`. Hãy kiểm tra và che giấu Account ID thành `123456789012` hoặc `***` trước khi lưu vào bằng chứng.

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Bài lab này là thao tác đọc (read-only), không tạo hay sửa đổi tài nguyên đám mây nào nên không yêu cầu hoàn tác. Nếu phát hiện đang ở sai Region, bạn chỉ cần chọn lại Region thành `ap-southeast-1` (Singapore) từ thanh điều hướng trên cùng.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/00-inventory/01-caller-identity.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [x] AWS Console / CLI hiển thị chính xác vùng hoạt động `ap-southeast-1` (Singapore). Đã cấu hình `aws configure set region ap-southeast-1`.
- [x] IAM User (`kien-lvn`) có đầy đủ chính sách quản trị (`AdministratorAccess`) triển khai toàn diện hạ tầng mạng, TGW, GWLB, Network Firewall và cụm EKS.
- [ ] Thiết bị MFA người dùng IAM (Root user đã tắt toàn bộ AccessKey `AccountAccessKeysPresent: 0`; khuyến nghị cấu hình thêm Virtual MFA cho user `kien-lvn`).
- [x] Lệnh `sts get-caller-identity` thực thi thành công qua MCP và Account ID được khử trùng thành `123456789012` trong file bằng chứng runtime.

### Kết Quả Thực Thi Runtime Xác Thực (Runtime Execution Summary)
- **Thời gian thực thi:** `2026-11-05T15:40:51Z`
- **Công cụ thực thi:** MCP `aws-api-mcp/call_aws`
- **Tài khoản xác thực (Sanitized):** `arn:aws:iam::123456789012:user/kien-lvn`
- **Vùng mặc định:** `ap-southeast-1`
- **File bằng chứng:** `evidence/00-inventory/01-caller-identity.json` (Status: `RUNTIME_PASS`)
