# Module 09: Hệ Thống Giám Sát & Quan Sát Mạng Toàn Diện (Network Observability)

## 1. Mục Tiêu Kỹ Thuật
- **Mục tiêu:**
  - Hợp nhất và tập trung hóa toàn bộ dữ liệu giám sát mạng từ 5 nguồn telemetry khác nhau:
    1. **VPC Flow Logs:** Ghi nhận toàn bộ lưu lượng `ACCEPT` và `REJECT` trên cả 4 VPCs.
    2. **Transit Gateway Flow Logs:** Ghi nhận lưu lượng phân đoạn giữa các Route Tables.
    3. **AWS Network Firewall Alert/Flow Logs:** Ghi nhận chi tiết gói tin bị chặn (Drop/Alert).
    4. **Suricata EVE Logs (`eve.json`):** Nhật ký kiểm tra sâu gói tin IDS/IPS, TLS SNI, DNS query.
    5. **ALB Access Logs & AWS WAF Logs:** Nhật ký truy cập từ người dùng ngoài Internet.
  - Sử dụng **AWS VPC Reachability Analyzer** để phân tích đường truyền logic và xác thực các đường định tuyến phức tạp mà không cần gửi gói tin thực nghiệm.

---

## 2. Kiến Trúc Thu Thập Telemetry Mạng

```text
+-----------------------+      +---------------------------+      +--------------------------+
| VPC Flow Logs (4 VPCs)|      | AWS Network Firewall Logs |      | Suricata eve.json (EC2)  |
+-----------------------+      +---------------------------+      +--------------------------+
           |                                 |                                 |
           +---------------------------------+---------------------------------+
                                             |
                                             v
                           [ CloudWatch Logs / Amazon S3 ]
                                             |
                                             v
                       [ Amazon Athena / CloudWatch Insights ]
                                             |
                                             v
                     [ VPC Reachability Analyzer Đường Dẫn Mạng ]
```

---

## 3. Các Bước Thực Hiện Chi Tiết

### Bước 1: Tập Trung Hóa Log Vào CloudWatch Log Groups
Khởi tạo các Log Groups chuyên biệt:
- `/aws/vpc/fabric-edge-flow`
- `/aws/vpc/fabric-core-flow`
- `/aws/vpc/fabric-inspection-flow`
- `/aws/vpc/fabric-egress-flow`
- `/aws/network-firewall/fabric-egress-alerts`
- `/aws/suricata/fabric-inspection-eve`

### Bước 2: Thiết Lập Truy Vấn CloudWatch Logs Insights
Cấu hình mẫu truy vấn để phân tích nhanh các gói tin bị REJECT:
```sql
fields @timestamp, srcAddr, dstAddr, srcPort, dstPort, protocol, action
| filter action = "REJECT"
| sort @timestamp desc
| limit 50
```

### Bước 3: Sử Dụng AWS VPC Reachability Analyzer
Tạo đường dẫn phân tích (Path Analysis) để kiểm chứng tính thông suốt:
- **Source:** Network Interface của Frontend Pod (Edge VPC).
- **Destination:** Network Interface của Core Internal NLB (Core VPC).
- Chạy phân tích (Run Analysis) và đối soát từng bước nhảy (Hops).

---

## 4. Xác Minh (Verification)
Chạy câu lệnh kiểm tra kết quả Reachability Analyzer qua AWS MCP:
```bash
aws ec2 get-reachability-analyzer-path-analysis \
  --analysis-id <analysis-id> \
  --region ap-southeast-1 \
  --query 'Analysis.{Status:Status,PathFound:IsPathFound}' \
  --output table
```
> Kết quả mong đợi: `Status: SUCCEEDED`, `IsPathFound: true`.

---

## 5. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Toàn bộ 5 luồng log được thu thập liên tục và có thể truy vấn bằng CloudWatch Insights.
- [ ] Nhật ký `eve.json` của Suricata ghi nhận chi tiết các phiên kiểm tra GENEVE.
- [ ] AWS VPC Reachability Analyzer xác nhận đường truyền logic giữa Edge và Core thông suốt qua GWLB.

