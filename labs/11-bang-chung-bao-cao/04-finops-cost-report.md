# 11.04 — Báo Cáo Đo Lường Chi Phí Thực Tế & Tối Ưu Hóa FinOps

> **Trạng thái:** Tài liệu tổng kết chi phí đám mây thực tế của Project 6.  
> **Áp dụng cho:** Báo cáo quản trị tài chính đám mây, chứng minh hiệu quả đầu tư và kiểm soát chi phí dưới ngưỡng ngân sách.

---

## 1. Mục Tiêu Quản Trị Chi Phí

- Đo lường chính xác lượng tài nguyên đám mây tiêu hao trong quá trình thực nghiệm Project 6 tại Singapore (`ap-southeast-1`).
- Chứng minh chi phí vận hành nằm trọn vẹn trong hạn mức **$50.00 USD**.
- Tổng hợp các giải pháp tối ưu FinOps đã áp dụng (ví dụ: Aurora Serverless v2 scale 0.5 ACU, thời gian sống ngắn cho EC2 Suricata, gộp log retention 7 ngày).

---

## 2. Bảng Tổng Hợp Chi Phí Thực Nghiệm

| Dịch Vụ AWS | Thời Gian Chạy Thực Tế | Đơn Giá / Giờ (Singapore) | Tổng Chi Phí Phát Sinh |
|---|---|---|---|
| **Transit Gateway** | 1 TGW x 24 giờ | $0.05 / giờ + $0.02 / GB | ~$1.20 |
| **TGW VPC Attachments** | 4 Attachments x 24 giờ | $0.05 / attachment / giờ | ~$4.80 |
| **Gateway Load Balancer** | 1 GWLB x 24 giờ | $0.0125 / giờ + $0.004 / NLCU | ~$0.50 |
| **AWS Network Firewall** | 2 Endpoints x 12 giờ | $0.065 / endpoint / giờ | ~$1.56 |
| **NAT Gateways** | 2 NAT GWs x 12 giờ | $0.059 / giờ + $0.059 / GB | ~$1.42 |
| **Suricata EC2 (`c6i.large`)** | 2 instances x 12 giờ | $0.085 / giờ | ~$2.04 |
| **Amazon EKS Control Plane** | 2 Clusters x 12 giờ | $0.10 / cluster / giờ | ~$2.40 |
| **EKS Worker Nodes (`t3.medium`)**| 4 nodes x 12 giờ | $0.052 / giờ | ~$2.50 |
| **Aurora Serverless v2** | 0.5 ACU x 12 giờ | $0.12 / ACU / giờ | ~$0.72 |
| **CloudWatch Logs & Metrics** | Lưu trữ 7 ngày | Theo dung lượng | ~$0.50 |
| **TỔNG CỘNG THỰC NGHIỆM** | | | **~$17.64 USD** |

> **Đánh giá FinOps:** Tổng chi phí thực nghiệm chỉ tiêu hao **$17.64 USD**, thấp hơn rất nhiều so với hạn mức ngân sách $50.00 USD đã thiết lập.

---

## 3. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Tổng chi phí phát sinh thực tế được đối soát trực tiếp với hóa đơn AWS Billing.
- [ ] Báo cáo FinOps được phê duyệt và lưu trữ cùng bộ bằng chứng kỹ thuật.

