# 11.04 — Báo Cáo Đo Lường Chi Phí Thực Tế & Tối Ưu Hóa FinOps

> **Mã bài lab:** `11.04`
> **Trạng thái:** `RUNTIME_PASS`
> **Thời gian dự kiến:** 30 phút
> **Chi phí ước tính:** $0.00 USD (Static Documentation / Read-Only Cost Explorer API)
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)

---

## 1. Mục Tiêu (Objective)

Đặc tả báo cáo phân tích chi phí thực tế và kiểm chứng các chiến lược tối ưu hóa FinOps trên toàn bộ hạ tầng AWS EKS Secure Network Fabric. Đảm bảo tổng mức tiêu hao trong toàn bộ chu kỳ thực nghiệm và diễn tập sự cố nằm dưới hạn mức ngân sách $50.00 USD ($17.64 - $18.42 USD thực tế).

---

## 2. Tài Nguyên (Resources)

| Tên Resource / Dịch Vụ | Loại Resource | Đơn Vị Tính Cước | Chi Phí Thực Tế (USD) | Tỷ Trọng (%) |
| :--- | :--- | :--- | :--- | :--- |
| `fabric-tgw` Attachments | TGW VPC Attachments | $0.05 / attachment / giờ | $4.80 | 27.2% |
| `fabric-edge` & `fabric-core` | EKS Control Plane | $0.10 / cụm / giờ | $2.40 | 13.6% |
| `fabric-suricata-1a/1b` | EC2 (`c6i.large`) | $0.085 / instance / giờ | $2.04 | 11.6% |
| EKS Managed Node Groups | EC2 (`t3.medium`) | $0.052 / instance / giờ | $2.50 | 14.2% |
| `fabric-egress-nfw` | Network Firewall Endpoints | $0.065 / endpoint / giờ | $1.56 | 8.8% |
| NAT Gateways (1a, 1b) | VPC NAT Gateway | $0.059 / gateway / giờ | $1.42 | 8.0% |
| `fabric-tgw` Base | Transit Gateway Base | $0.05 / giờ | $1.20 | 6.8% |
| `fabric-aurora-cluster` | Aurora Serverless v2 | $0.12 / ACU / giờ (0.5 ACU) | $0.72 | 4.1% |
| `fabric-gwlb` | Gateway Load Balancer | $0.0125 / giờ | $0.50 | 2.8% |
| CloudWatch & WAF v2 | Ingestion & Rule charge | Dung lượng GB + Rule / web ACL | $0.50 | 2.9% |
| **TỔNG CỘNG** | | | **~$17.64 USD** | **100.0%** |

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-*` | Tài nguyên phân bổ chi phí |
| `Project` | `aws-eks-secure-network-fabric` | Bắt buộc để lọc Cost Allocation Tag trên AWS Billing |
| `Environment` | `prod` | Phân vùng môi trường đối soát chi phí |
| `ManagedBy` | `manual` | Quản lý vòng đời tài nguyên thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Ngân Sách AWS Budgets Cấu Hình
* **Tên ngân sách:** `fabric-monthly-budget`
* **Hạn mức trần (Limit):** $50.00 USD / tháng
* **Ngưỡng cảnh báo (Alerts):**
  - Cảnh báo 80% ($40.00 USD) thực tế -> Gửi SNS / Email thông báo.
  - Cảnh báo 100% dự báo (Forecasted) -> Kích hoạt quy trình rà soát teardown.

### 4.2 4 Chiến Lược Tối Ưu FinOps Đã Triển Khai
1. **Kiến Trúc Đơn Vùng (Single-Region Discipline):** Triển khai toàn bộ tại Singapore (`ap-southeast-1`), loại bỏ 100% cước phí Inter-region Data Transfer ($0.02/GB).
2. **Cơ Chế Scale Tối Thiểu Database:** Aurora PostgreSQL Serverless v2 chạy ở baseline 0.5 ACU khi không có tải, tiết kiệm >70% so với instance tĩnh `db.r6g.large`.
3. **Chính Sách Lưu Nhật Ký Tinh Gọn (Log Retention Policy):** Cấu hình thời hạn lưu trữ 7 ngày (`RetentionInDays: 7`) cho 8 CloudWatch Log Groups, tránh tích lũy chi phí lưu trữ log rác.
4. **Quy Trình Thu Hồi Tài Nguyên Ngược Phụ Thuộc (Reverse Teardown):** Lập quy trình dọn dẹp theo thứ tự đảo ngược các tài nguyên tính cước cao (NAT, NFW, EKS) đưa chi phí duy trì về $0.00 USD/ngày.

---

## 5. Phụ Thuộc (Dependencies)

* [Lab 00.02](../00-chuan-bi-inventory/02-naming-tagging-budget.md): Đã cấu hình thẻ `Project` và kích hoạt Cost Allocation Tag.
* AWS Cost Explorer đã bật và thu thập dữ liệu chi phí tối thiểu 24 giờ.

---

## 6. Kiểm Tra Đạt (Verification)

| Hạng Mục | Lệnh Kiểm Tra / Metric | Kỳ Vọng Đạt |
| :--- | :--- | :--- |
| **Hạn Mức Ngân Sách** | Truy vấn AWS Cost Explorer tổng chi phí | Tổng thực tế $\le \$50.00$ USD (thực tế $\approx \$17.64 - \$18.42$) |
| **Tuân Thủ Thẻ Tag** | Kiểm tra tỷ lệ tài nguyên có tag `Project` | 100% tài nguyên tính phí được gán tag phân bổ chi phí |
| **Chính Sách Log Retention** | `aws logs describe-log-groups --query 'logGroups[?retentionInDays!=`7`]'` | 0 Log Groups vượt quá thời hạn 7 ngày |
| **Báo Cáo Hoàn Chỉnh** | Kiểm tra file `FINOPS-COST-REPORT.md` | Có bảng phân rã chi phí chi tiết theo dịch vụ và tỷ trọng |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

> [!TIP]
> Luôn kiểm tra dự báo chi phí (Forecasted Spend) trong AWS Budgets hàng tuần để ngăn ngừa tình trạng chi phí phát sinh ngoài ý muốn (Cost Spikes).

### Kế Hoạch Quản Lý Báo Cáo
Tệp báo cáo `FINOPS-COST-REPORT.md` và `cost-explorer-daily.json` được cập nhật định kỳ khi kết thúc mỗi đợt GameDay hoặc trước khi thực hiện dọn dẹp hạ tầng tại Module 12.
