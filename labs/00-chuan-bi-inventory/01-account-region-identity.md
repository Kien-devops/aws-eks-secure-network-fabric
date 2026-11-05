# 00.01 — Xác Thực Danh Tính IAM, Region Singapore & Quyền Hạn Triển Khai

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Thiết lập phiên làm việc an toàn, khóa cứng vùng hoạt động tại Singapore (`ap-southeast-1`), kiểm tra quyền hạn trước khi thao tác mạng nâng cao.

---

## 1. Mục Tiêu & Nguyên Tắc An Toàn

- **Mục tiêu:**
  - Xác thực phiên đăng nhập AWS Console đang ở đúng Region Singapore (`ap-southeast-1`).
  - Đảm bảo tài khoản thực thi có đầy đủ các quyền: VPC, EC2, Transit Gateway, Gateway Load Balancer, AWS Network Firewall, EKS, KMS, WAFv2.
  - Kiểm tra trạng thái MFA (Multi-Factor Authentication) của IAM User / IAM Role.
- **Nguyên tắc cốt lõi:**
  - **Single-Region Lock:** Tuyệt đối không chuyển sang các Region khác trong suốt dự án. Mọi tài nguyên mạng phải được neo chắc chắn tại `ap-southeast-1`.
  - **Least Privilege Awareness:** Nhận diện rõ vai trò IAM đang đảm nhận, tránh dùng root account khi thực hành.

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Khóa Cứng Vùng Hoạt Động (Region Selector)
1. Đăng nhập vào **AWS Management Console**.
2. Nhìn lên thanh điều hướng trên cùng bên phải, nhấp vào menu thả xuống chọn Region.
3. Chọn chính xác: **Asia Pacific (Singapore) `ap-southeast-1`**.
4. Xác nhận thanh URL hiển thị tham số `region=ap-southeast-1`.

---

### Bước 2: Kiểm Tra Danh Tính IAM Đang Đăng Nhập
1. Trên thanh tìm kiếm của AWS Console, gõ **IAM** -> Chọn dịch vụ **IAM**.
2. Tại bảng điều khiển IAM bên trái, nhấp vào **Users** (hoặc **Roles** nếu đăng nhập qua SSO/Federation).
3. Nhấp vào tên người dùng/role của bạn:
   - Kiểm tra tab **Permissions**: Xác nhận có policy AdministratorAccess hoặc chính sách mạng chuyên sâu.
   - Kiểm tra tab **Security credentials**: Xác nhận trạng thái **Multi-factor authentication (MFA)** đã được bật (`Assigned`).

---

## 3. Xác Minh Bằng AWS CLI (Qua MCP `aws-api-mcp/call_aws`)

Chạy lệnh xác thực danh tính và vùng làm việc:
```bash
aws sts get-caller-identity --region ap-southeast-1 --output table
aws configure get region
```

> [!NOTE]
> Khi xuất báo cáo hoặc lưu evidence, hãy đảm bảo **Account ID đã được che giấu** (thay bằng `123456789012` hoặc `***`).

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] AWS Console hiển thị đúng vùng `ap-southeast-1` (Singapore).
- [ ] Lệnh `sts get-caller-identity` trả về ARN hợp lệ với `UserId` rõ ràng.
- [ ] MFA đang hoạt động trên danh tính đăng nhập.
