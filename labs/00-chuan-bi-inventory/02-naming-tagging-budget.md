# 00.02 — Quy Chuẩn Đặt Tên (Naming), Gắn Nhãn (Tagging) & Thiết Lập AWS Budgets ($50.00)

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Quản trị FinOps, thiết lập cảnh báo ngân sách tự động và chuẩn hóa định danh tài nguyên trên Project 6.

---

## 1. Mục Tiêu & Nguyên Tắc FinOps

- **Mục tiêu:**
  - Thiết lập ngân sách kiểm soát chi phí **AWS Budgets** ở mức **$50.00 USD** tại Region Singapore.
  - Cấu hình 2 ngưỡng cảnh báo sớm: 80% ($40 USD) và 100% ($50 USD) gửi email thông báo.
  - Thống nhất quy ước đặt tên (Naming Convention) tiền tố `fabric-*` và hệ thống Tag chuẩn doanh nghiệp.
- **Nguyên tắc cốt lõi:**
  - **No Tag, No Deploy:** Mọi tài nguyên tạo ra (VPC, Subnet, TGW, Route Table, EC2, EKS, ALB) đều phải mang bộ Tag định danh bắt buộc để theo dõi chi phí và quản lý vòng đời.

---

## 2. Quy Chuẩn Naming & Tagging

### Bảng Quy Ước Tiền Tố (Prefix)
- Tài nguyên mạng nền tảng: `fabric-tgw`, `fabric-edge-vpc`, `fabric-core-vpc`, `fabric-inspection-vpc`, `fabric-egress-vpc`.
- Cụm tường lửa & cân bằng tải: `fabric-gwlb`, `fabric-gwlb-endpoint-1a`, `fabric-egress-nfw`, `fabric-edge-alb`.
- Cụm Kubernetes: `fabric-edge-eks`, `fabric-core-eks`.

### Bộ Tag Bắt Buộc (Cost Allocation Tags)
| Tag Key | Giá Trị Chuẩn (Value) | Mục Đích |
|---|---|---|
| `Project` | `aws-eks-secure-network-fabric` | Phân nhóm chi phí tổng thể của Project 6 |
| `Environment` | `dev` / `prod` | Phân biệt môi trường thực nghiệm và sản xuất |
| `ManagedBy` | `Console-to-IaC` | Định danh phương thức quản trị và bàn giao |
| `Region` | `ap-southeast-1` | Khẳng định phạm vi địa lý Singapore |

---

## 3. Các Bước Tạo Ngân Sách AWS Budgets Trên Console

### Bước 1: Mở Bảng Điều Khiển AWS Budgets
1. Trên thanh tìm kiếm Console, nhập **Budgets** -> Chọn dịch vụ **AWS Budgets** (hoặc truy cập qua Billing and Cost Management).
2. Tại menu bên trái, nhấp vào **Budgets** -> Nhấp nút cam **Create budget**.

### Bước 2: Thiết Lập Thông Số Ngân Sách
1. Tại mục **Budget setup**: Chọn **Customize (advanced)** -> Chọn **Cost budget - Recommended** -> Nhấp **Next**.
2. **Budget details:**
   - **Budget name:** Nhập `fabric-project6-monthly-budget`.
   - **Period:** Chọn `Monthly`.
   - **Budget effective date:** Chọn `Recurring budget`.
   - **Budget method:** Chọn `Fixed`.
   - **Enter your budgeted amount ($):** Nhập `50`.
3. **Budget scope:** Chọn `All AWS services`.
4. Nhấp **Next**.

### Bước 3: Cấu Hình Ngưỡng Cảnh Báo (Alert Thresholds)
1. Nhấp **Add an alert threshold**:
   - **Alert 1 (Ngưỡng 80%):**
     - **Threshold:** Nhập `80` (% of budgeted amount).
     - **Trigger:** Chọn `Actual`.
     - **Email recipients:** Nhập địa chỉ email nhận thông báo của bạn.
2. Nhấp **Add an alert threshold** lần 2:
   - **Alert 2 (Ngưỡng 100%):**
     - **Threshold:** Nhập `100` (% of budgeted amount).
     - **Trigger:** Chọn `Forecasted` (Dự báo đạt tới ngân sách).
     - **Email recipients:** Nhập email của bạn.
3. Nhấp **Next** -> Nhấp **Create budget**.

---

## 4. Xác Minh (Verification)

Chạy lệnh kiểm tra ngân sách qua AWS CLI:
```bash
aws budgets describe-budgets \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --region ap-southeast-1 \
  --query 'Budgets[*].{Name:BudgetName,Limit:BudgetLimit.Amount,Unit:BudgetLimit.Unit,Type:BudgetType}' \
  --output table
```

---

## 5. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Ngân sách `fabric-project6-monthly-budget` ở trạng thái hoạt động với hạn mức đúng $50.00.
- [ ] Cả 2 ngưỡng cảnh báo (80% actual và 100% forecasted) được kích hoạt gửi email.
