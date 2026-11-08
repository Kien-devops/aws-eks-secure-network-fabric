# Lab 00.02: Quy Chuẩn Định Danh, Gắn Thẻ & Thiết Lập AWS Budgets ($50.00)

**Mã tài liệu:** `LAB-00-02`
**Trạng thái:** `RUNTIME_PASS`
**Vùng áp dụng:** `ap-southeast-1` (Singapore)

---

## 1. Mục Tiêu (Objective)
Thiết lập chuẩn định danh, gắn thẻ chi phí (Cost Allocation Tags) và kích hoạt AWS Budget khống chế trần chi phí $50.00 USD với 2 ngưỡng cảnh báo sớm.

---

## 2. Tài Nguyên (Resources)

| Tên Mong Muốn (Name) | Loại Tài Nguyên | Phạm Vi / Vùng | Tham Chiếu Runtime (Sanitized) |
| :--- | :--- | :--- | :--- |
| `fabric-project6-monthly-budget` | AWS Budget (Cost) | Global / Account | `arn:aws:budgets::123456789012:budget/fabric-project6-monthly-budget` |
| `fabric-*` | Tiền tố tài nguyên (Prefix) | `ap-southeast-1` | Quy ước áp dụng cho toàn bộ VPCs, EKS, TGW, GWLB, NFW |

---

## 3. Thẻ Định Danh (Tags)

| Khóa (Key) | Giá Trị (Value) | Trạng Thái Cost Allocation | Mục Đích |
| :--- | :--- | :--- | :--- |
| `Name` | `fabric-*` | Active | Định danh tài nguyên logic |
| `Project` | `aws-eks-secure-network-fabric` | Active | Phân tách ranh giới chi phí dự án |
| `Environment` | `prod` | Active | Tách biệt chi phí môi trường |
| `ManagedBy` | `manual` | Active | Quản lý triển khai thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)
- **Hạn Mức Ngân Sách:** `$50.00 USD` (Fixed, Monthly Recurring).
- **Phạm vi dịch vụ:** Toàn bộ dịch vụ AWS phát sinh trong tài khoản (EC2, NAT Gateway, EKS, Network Firewall, TGW, GWLB).
- **Ngưỡng Cảnh Báo 1:** 80% Chi phí thực tế (`$40.00 USD` - Actual) → Gửi cảnh báo sớm qua Email.
- **Ngưỡng Cảnh Báo 2:** 100% Chi phí dự báo (`$50.00 USD` - Forecasted) → Kích hoạt chuẩn bị dọn dẹp.

---

## 5. Phụ Thuộc (Dependencies)
- Hoàn thành xác thực IAM tại [Lab 00.01](01-account-region-identity.md).

---

## 6. Kiểm Tra Đạt (Verification)
- [x] Lệnh `aws budgets describe-budgets --account-id 123456789012` trả về ngân sách `$50.00 USD`.
- [x] Lệnh `aws budgets describe-notifications-for-budget` xác nhận 2 ngưỡng cảnh báo 80% và 100%.
- [x] Bằng chứng runtime đã thu thập: [`evidence/00-inventory/02-budget-status.json`](../../evidence/00-inventory/02-budget-status.json).

---

## 7. Cảnh Báo An Toàn & Rollback Plan
- **Cảnh báo FinOps:** Khi chạm mốc $40 USD (80%), kỹ sư phải chuẩn bị kế hoạch Teardown tại Module 12 để tránh phát sinh chi phí ngoài ý muốn.
- **Kế hoạch khôi phục (Rollback):**
  ```bash
  aws budgets delete-budget --account-id 123456789012 --budget-name fabric-project6-monthly-budget
  ```
