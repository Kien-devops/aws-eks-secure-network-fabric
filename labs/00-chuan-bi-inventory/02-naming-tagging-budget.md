# 00.02 — Quy Chuẩn Đặt Tên (Naming), Gắn Nhãn (Tagging) & Thiết Lập AWS Budgets ($50.00)

> **Mã bài lab:** `00.02`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 20 phút  
> **Chi phí ước tính:** $0.00 USD (AWS Budgets miễn phí 2 ngân sách đầu tiên)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bài lab [00.01 — Xác Thực Danh Tính IAM](01-account-region-identity.md).
- Có một địa chỉ email hợp lệ để nhận thông báo cảnh báo chi phí tức thì.
- Quyền tạo và quản lý AWS Budgets trong IAM.

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
        "ce:GetCostAndUsage",
        "ce:ListCostAllocationTags",
        "ce:UpdateCostAllocationTagsStatus"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** AWS cho phép tạo miễn phí 2 ngân sách đầu tiên mỗi tháng. Dự án Project 6 chỉ sử dụng 1 ngân sách duy nhất (`fabric-project6-monthly-budget`).
- **Cảnh báo FinOps:** Khi chi phí chạm mốc 80% ($40.00 USD), quản trị viên phải lập tức rà soát và sẵn sàng kích hoạt quy trình dọn dẹp tại Module 12 nếu là môi trường thử nghiệm GameDay. Giới hạn ngân sách cứng của đồ án là **$50.00 USD**.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Quy Chuẩn Đặt Tên & Nhãn Thống Nhất Cho Toàn Bộ Hạ Tầng
Trước khi tạo tài nguyên, thiết lập quy chuẩn bắt buộc áp dụng cho mọi tài nguyên trên Singapore (`ap-southeast-1`):
1. **Tiền tố định danh (Resource Naming Prefix):** `fabric-*` (hoặc `fabric-prod-*` cho tài nguyên sản xuất, `fabric-dev-*` cho tài nguyên thử nghiệm).
2. **Bộ Cost Allocation Tags chuẩn:**
   - `Project`: `aws-eks-secure-network-fabric`
   - `Environment`: `prod` (hoặc `dev`)
   - `ManagedBy`: `terraform` (hoặc `console-lab`)
   - `Owner`: `kien-devops`

### Bước 2: Kích Hoạt Cost Allocation Tags Trong AWS Billing Console
1. Trên thanh tìm kiếm AWS Console, nhập **Billing** và chọn dịch vụ **Billing and Cost Management**.
2. Tại menu điều hướng bên trái, cuộn xuống mục **Cost organization** -> Chọn **Cost allocation tags**.
3. Chọn tab **User-defined cost allocation tags**:
   - Tìm kiếm các thẻ: `Project`, `Environment`, `ManagedBy`.
   - Đánh dấu tích vào checkbox của các thẻ này.
   - Nhấp nút **Activate** ở góc trên bảng để kích hoạt tính năng theo dõi chi phí theo nhãn dự án.

### Bước 3: Mở Bảng Điều Khiển AWS Budgets & Khởi Tạo Ngân Sách
1. Trên thanh tìm kiếm AWS Console, nhập `Budgets` -> Chọn **AWS Budgets**.
2. Tại menu điều hướng bên trái, nhấp vào **Budgets**.
3. Nhấp vào nút cam **Create budget** ở góc trên bên phải.

### Bước 4: Thiết Lập Thông Số Ngân Sách $50.00 USD
1. Tại màn hình **Choose budget setup**:
   - Chọn mục: **Customize (advanced)**.
   - Chọn loại ngân sách: **Cost budget - Recommended** (Theo dõi chi phí theo số tiền USD).
   - Nhấp **Next** ở cuối trang.
2. Tại màn hình **Set budget amount**:
   - **Budget details:**
     - **Budget name:** Nhập chính xác `fabric-project6-monthly-budget`.
     - **Period:** Chọn `Monthly` (Hàng tháng).
     - **Budget effective date:** Chọn `Recurring budget` (Tái lặp hàng tháng).
     - **Start month:** Chọn tháng hiện tại.
     - **Budget method:** Chọn `Fixed` (Số tiền cố định).
     - **Enter your budgeted amount ($):** Nhập `50`.
   - **Budget scope:**
     - Chọn `All AWS services (Recommended)` (Bao quát toàn bộ các dịch vụ EC2, EKS, NAT Gateway, TGW, GWLB, Network Firewall).
   - Nhấp nút cam **Next** ở cuối trang để chuyển sang bước cấu hình cảnh báo.

### Bước 5: Cấu Hình 2 Ngưỡng Cảnh Báo Sớm Qua Email
1. **Thiết lập Ngưỡng 1 (80% Chi phí Thực tế - Early Warning):**
   - Nhấp **Add an alert threshold**.
   - **Set alert threshold:**
     - **Threshold:** Nhập `80` (% of budgeted amount, tương đương $40.00 USD).
     - **Trigger:** Chọn `Actual` (Chi phí thực tế phát sinh vượt ngưỡng).
   - **Notification preferences:**
     - **Email recipients:** Nhập địa chỉ email của bạn để nhận thông báo cảnh báo tức thì.
2. **Thiết lập Ngưỡng 2 (100% Chi phí Dự báo - Forecasted Breach Alert):**
   - Nhấp nút **Add alert threshold** bên dưới.
   - **Set alert threshold:**
     - **Threshold:** Nhập `100` (% of budgeted amount, tương đương $50.00 USD).
     - **Trigger:** Chọn `Forecasted` (AWS dự báo chi phí cuối tháng sẽ chạm mốc $50).
   - **Notification preferences:**
     - **Email recipients:** Nhập địa chỉ email của bạn.
3. Nhấp **Next** để chuyển sang bước **Attach actions (optional)** -> Tiếp tục nhấp **Next** để bỏ qua action tự động.
4. Tại bước **Review and create**:
   - Kiểm tra lại toàn bộ thông số: Tên ngân sách `fabric-project6-monthly-budget`, Period `Monthly`, Amount `$50.00`, 2 alert thresholds (`80% Actual` và `100% Forecasted`).
   - Nhấp nút cam **Create budget** ở cuối trang.
5. Xác nhận trên danh sách Budgets hiển thị dòng `fabric-project6-monthly-budget` với trạng thái xanh `OK` hoặc `Under budget`.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy các lệnh xác minh trạng thái ngân sách và gắn nhãn qua AWS CLI hoặc MCP Server (`aws-api-mcp/call_aws`):
```bash
# 1. Kiểm tra danh sách Budgets trên tài khoản (thay 123456789012 bằng Account ID thực tế của bạn khi chạy)
aws budgets describe-budgets \
  --account-id 123456789012 \
  --query 'Budgets[*].{Name:BudgetName,Limit:BudgetLimit.Amount,Unit:BudgetLimit.Unit,Type:BudgetType}' \
  --output table

# 2. Kiểm tra chi tiết 2 ngưỡng cảnh báo của ngân sách fabric-project6-monthly-budget
aws budgets describe-notifications-for-budget \
  --account-id 123456789012 \
  --budget-name fabric-project6-monthly-budget \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Nếu cần xóa hoặc chỉnh sửa ngân sách đã tạo:
1. Mở **AWS Budgets Console** -> Đánh dấu tích vào checkbox trước dòng `fabric-project6-monthly-budget`.
2. Nhấp menu **Actions** ở trên bảng -> Chọn **Delete**.
3. Nhập từ khóa xác nhận và nhấp **Delete budget**.
4. Hoặc thực thi qua CLI:
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
- [ ] 2 ngưỡng thông báo (80% actual = $40 USD, 100% forecasted = $50 USD) được kích hoạt với email nhận tin hợp lệ.
- [ ] Quy ước tiền tố `fabric-*` và bộ Cost Allocation Tags được ghi nhận đầy đủ.
