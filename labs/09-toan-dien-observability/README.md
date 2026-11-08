# Module 09: Hệ Thống Giám Sát & Quan Sát Mạng Toàn Diện (Network Observability)

Module này cung cấp các đặc tả tài nguyên hợp nhất và tập trung hóa dữ liệu giám sát mạng từ VPC Flow Logs, Transit Gateway, Suricata IDS/IPS, AWS Network Firewall và AWS WAFv2 về CloudWatch Logs, kèm theo thư viện truy vấn Insights và kiểm chứng đường truyền logic bằng AWS VPC Reachability Analyzer.

---

## 1. Thứ Tự Phụ Thuộc (Dependency Tree)

```text
09.01 (Khởi tạo 8 CloudWatch Log Groups tập trung với Retention 7 ngày)
  │
  ├──> 09.02 (Cấu hình CloudWatch Unified Agent đẩy Suricata eve.json)
  │      │
  │      └──> 09.03 (Xây dựng thư viện Saved Queries trên CloudWatch Insights)
  │
  └──> 09.04 (Kiểm chứng đường truyền logic 13 chặng qua VPC Reachability Analyzer)
```

---

## 2. Danh Mục Tài Nguyên (Resource Catalog)

| Tài Nguyên | Loại Resource | Số Lượng | Ghi Chú Kỹ Thuật |
| :--- | :--- | :---: | :--- |
| **CloudWatch Log Groups** | `AWS::Logs::LogGroup` | 8 | Retention: 7 days, Standard log class |
| **CloudWatch Agent** | `Linux::Daemon` | 2 | Chạy trên 2 Suricata EC2 instances (`fabric-suricata-1a/b`) |
| **Saved Queries** | `AWS::Logs::QueryDefinition` | 4 | VPC Rejects, Suricata Alerts, NFW Drops, WAF Blocked IPs |
| **Network Insights Path** | `AWS::EC2::NetworkInsightsPath` | 1 | `fabric-edge-to-core-path` (TCP 443) |
| **Network Analysis** | `AWS::EC2::NetworkInsightsAnalysis` | 1 | Xác minh 13 chặng logic (`NetworkPathFound: true`) |

---

## 3. Danh Sách 4 Bài Lab Đặc Tả Chi Tiết

| Mã Lab | Tên Đặc Tả & Nội Dung Trọng Tâm | Trạng Thái | File Đặc Tả |
|---|---|:---:|---|
| **09.01** | **CloudWatch Log Groups Tập Trung:** Danh mục 8 log groups với thời hạn lưu trữ 7 ngày. | `RUNTIME_PASS` | [01-centralized-cloudwatch-log-groups.md](01-centralized-cloudwatch-log-groups.md) |
| **09.02** | **Suricata EVE Log Aggregation:** Thu thập nhật ký L7 IDS/IPS qua CloudWatch Unified Agent. | `RUNTIME_PASS` | [02-suricata-eve-log-aggregation.md](02-suricata-eve-log-aggregation.md) |
| **09.03** | **CloudWatch Insights Queries:** Thư viện 4 câu truy vấn chuẩn hóa phục vụ phân tích sự cố mạng. | `RUNTIME_PASS` | [03-cloudwatch-insights-queries.md](03-cloudwatch-insights-queries.md) |
| **09.04** | **VPC Reachability Analyzer:** Chứng minh bằng toán học đường truyền logic 13 chặng xuyên qua GWLB. | `RUNTIME_PASS` | [04-vpc-reachability-analyzer.md](04-vpc-reachability-analyzer.md) |
