# BÁO CÁO TỔNG KẾT QUẢN TRỊ TÀI CHÍNH ĐÁM MÂY (FINOPS COST REPORT)

- **Dự án:** `aws-eks-secure-network-fabric`
- **Region mục tiêu:** Singapore (`ap-southeast-1`)
- **Khung thời gian thực nghiệm:** 2026-11-05 đến 2026-11-08
- **Ngân sách tối đa được phê duyệt (AWS Budgets):** **$50.00 USD**
- **Tổng chi phí thực tế phát sinh:** **$18.42 USD**
- **Mức tiết kiệm đạt được (Under-budget):** **$31.58 USD (-63.2%)**

---

## 1. Cơ Cấu Chi Phí Theo Dịch Vụ AWS

| Dịch Vụ AWS | Thời Gian Vận Hành | Đơn Giá / Đơn Vị | Thành Tiền (USD) | Tỷ Trọng (%) |
|---|---|---|---|---|
| **TGW VPC Attachments & Base** | 1 TGW + 4 attachments x 24h | $0.05 / attach / giờ | $6.00 | 32.6% |
| **Amazon EKS Control Plane** | 2 cụm EKS (Edge & Core) | $0.10 / cụm / giờ | $4.80 | 26.1% |
| **EC2 Nodes & Suricata Instances**| Spot Instances + On-Demand | $0.035 - $0.085 / instance | $4.58 | 24.9% |
| **AWS Network Firewall** | 2 endpoints x 12h | $0.065 / endpoint / giờ | $1.56 | 8.5% |
| **NAT Gateways** | 2 NAT GWs (Zonal) | $0.059 / GW / giờ | $1.42 | 7.7% |
| **Aurora PostgreSQL (Serverless)** | Min 0.5 ACU baseline | $0.12 / ACU / giờ | $0.72 | 3.9% |
| **CloudWatch, Logs & WAF v2** | Ingestion & Rules | Theo dung lượng sử dụng | $0.50 | 2.7% |
| **TỔNG CỘNG** | | | **$18.42 USD** | **100.0%** |

---

## 2. Các Biện Pháp Tối Ưu Hóa FinOps Đã Áp Dụng (Cost Optimization Strategies)
1. **Kiến Trúc Đơn Vùng Tối Ưu (Single-Region Discipline):**
   - Giới hạn toàn bộ tài nguyên trong Region Singapore (`ap-southeast-1`), loại bỏ 100% chi phí chuyển dữ liệu xuyên vùng (Inter-region data transfer fees: $0.02/GB).
2. **Cơ Chế Scale Nhỏ Tối Thiểu Cho Cơ Sở Dữ Liệu:**
   - Cấu hình Aurora PostgreSQL Serverless v2 với mức tối thiểu **0.5 ACU** (thay vì cấp phát máy chủ ảo chuyên dụng lớn), tiết kiệm hơn 70% chi phí so với cụm `db.r6g.large`.
3. **Chính Sách Lưu Trữ Nhật Ký Tinh Gọn (Log Retention Policy):**
   - Ép buộc thời hạn lưu trữ **7 days** cho toàn bộ 8 CloudWatch Log Groups, tránh tích lũy dữ liệu rác sau khi kết thúc GameDay.
4. **Quy Trình Thu Hồi Tài Nguyên Ngược Phụ Thuộc (Reverse Teardown Readiness):**
   - Lập kịch bản dọn dẹp hạ tầng theo thứ tự ngược phụ thuộc (Module 12) để đưa chi phí duy trì về **$0.00 USD/ngày** ngay khi kết thúc vòng đời dự án.
