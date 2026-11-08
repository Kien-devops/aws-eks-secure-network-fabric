# 09.03 — Đặc Tả Thư Viện Truy Vấn CloudWatch Logs Insights Phân Tích Sự Cố Mạng

> **Mã bài lab:** `09.03`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/09-observability/saved-queries.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả thư viện 4 câu truy vấn phân tích chuyên sâu được định nghĩa và lưu trữ sẵn trên CloudWatch Logs Insights nhằm phục vụ tự động hóa điều tra sự cố mạng, phát hiện tấn công L7, rà soát vi phạm egress và xác định nguyên nhân gói tin bị REJECT.

---

## 2. Tài Nguyên (Resources)

| Tên Query Definition | Loại Resource | Target Log Groups | Mục Đích Điều Tra |
| :--- | :--- | :--- | :--- |
| `fabric-vpc-flow-top-rejects` | `AWS::Logs::QueryDefinition` | 4 VPC Flow Logs (`/aws/vpc/fabric-*`) | Thống kê Top IP/Port bị REJECT ở tầng mạng L3/L4 |
| `fabric-suricata-ids-alerts` | `AWS::Logs::QueryDefinition` | `/aws/suricata/fabric-inspection-eve` | Liệt kê các chữ ký cảnh báo an ninh từ Suricata IDS/IPS |
| `fabric-nfw-egress-blocked-domains` | `AWS::Logs::QueryDefinition` | `/aws/network-firewall/fabric-egress-alerts` | Thống kê các tên miền bị Network Firewall chặn |
| `fabric-waf-top-blocked-ips` | `AWS::Logs::QueryDefinition` | `aws-waf-logs-fabric-edge-waf` | Thống kê Top client IPs và Rules kích hoạt chặn WAF L7 |

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-insights-queries` | Query Definitions |
| `Project` | `aws-eks-secure-network-fabric` | Query Definitions |
| `Environment` | `prod` | Query Definitions |
| `Folder` | `Fabric-Network-Ops` | Thư mục tổ chức truy vấn |
| `ManagedBy` | `manual` | Quản trị thư viện truy vấn |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Danh Mục Câu Truy Vấn Chuẩn Hóa

```sql
-- 1. Top Gói Tin Bị REJECT Trên Toàn Bộ VPC
fields @timestamp, srcAddr, dstAddr, srcPort, dstPort, protocol, action
| filter action = "REJECT"
| stats count(*) as rejectedCount by srcAddr, dstAddr, dstPort
| sort rejectedCount desc
| limit 20

-- 2. Cảnh Báo An Ninh Tấn Công Từ Suricata EVE
fields @timestamp, src_ip, dest_ip, dest_port, alert.signature, alert.category, alert.severity
| filter event_type = "alert"
| sort @timestamp desc
| limit 50

-- 3. Danh Sách Tên Miền Bị AWS Network Firewall Chặn
fields @timestamp, event.src_ip, event.dest_ip, event.dest_port, event.http.hostname, event.alert.signature
| filter event.alert.action = "drop" or event.alert.action = "blocked"
| stats count(*) as dropCount by event.http.hostname, event.src_ip
| sort dropCount desc
| limit 20

-- 4. Top Địa Chỉ IP Bị Chặn Bởi AWS WAF v2 Ingress
fields @timestamp, httpRequest.clientIp, httpRequest.country, terminatingRuleId, httpRequest.uri
| filter action = "BLOCK"
| stats count(*) as blockCount by httpRequest.clientIp, httpRequest.country, terminatingRuleId
| sort blockCount desc
| limit 20
```

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `09.01`: Các Log Groups mục tiêu đã được khởi tạo.
- Phụ thuộc vào dữ liệu nhật ký thực tế phát sinh từ `02.05`, `06.03`, `07.04`, và `09.02`.
- Là công cụ điều tra chính được sử dụng xuyên suốt kịch bản diễn tập GameDay tại [Module 10](../10-gameday-su-co-mang/README.md).

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Danh Sách Saved Queries** | `aws logs describe-query-definitions --query 'queryDefinitions[?contains(name, "fabric")].name'` | Hiển thị đủ 4 tên query đã lưu. |
| **Thực Thi Query Trực Tiếp** | Chạy `aws logs start-query` và `aws logs get-query-results` | Trả về trạng thái `Complete` kèm số bản ghi quét hợp lệ. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo chi phí quét dữ liệu:** CloudWatch Logs Insights tính phí $0.005 cho mỗi GB dữ liệu quét. Luôn giới hạn phạm vi thời gian (1 hour hoặc 3 hours) thay vì quét All Time.
- **Quy trình Rollback:**
  ```bash
  # Xóa Query Definition
  aws logs delete-query-definition --region ap-southeast-1 --query-definition-id <QueryDefId>
  ```
