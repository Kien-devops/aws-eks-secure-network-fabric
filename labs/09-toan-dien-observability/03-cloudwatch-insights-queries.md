# 09.03 — Xây Dựng Thư Viện Truy Vấn CloudWatch Logs Insights Phân Tích Sự Cố Mạng

> **Trạng thái:** Hướng dẫn thực hành phân tích telemetry nâng cao trên AWS Management Console.  
> **Áp dụng cho:** Điều tra sự cố mạng, tìm kiếm gói tin bị REJECT, phân tích tấn công IDS và kiểm tra lưu lượng Egress.

---

## 1. Mục Tiêu Kỹ Thuật

- Khai thác công cụ **CloudWatch Logs Insights** để truy vấn nhanh hàng triệu bản ghi nhật ký mạng trong vài giây.
- Xây dựng 4 mẫu truy vấn (Saved Queries) chuẩn SRE phục vụ vận hành và GameDay:
  1. Truy vấn các gói tin bị từ chối (`REJECT`) trên VPC Flow Logs.
  2. Truy vấn cảnh báo phát hiện tấn công từ Suricata EVE Logs.
  3. Truy vấn các tên miền bị chặn bởi AWS Network Firewall.
  4. Truy vấn các địa chỉ IP bị AWS WAF chặn đứng.

---

## 2. Thư Viện Truy Vấn Chi Tiết

### Mẫu 1: Tìm Kiếm Gói Tin Bị REJECT Trên Toàn Bộ VPCs
Áp dụng cho 4 Log Groups: `/aws/vpc/fabric-*-flow`:
```sql
fields @timestamp, srcAddr, dstAddr, srcPort, dstPort, protocol, action
| filter action = "REJECT"
| stats count(*) as rejectedCount by srcAddr, dstAddr, dstPort
| sort rejectedCount desc
| limit 20
```

---

### Mẫu 2: Phân Tích Cảnh Báo An Ninh Từ Suricata EVE
Áp dụng cho Log Group: `/aws/suricata/fabric-inspection-eve`:
```sql
fields @timestamp, src_ip, dest_ip, dest_port, alert.signature, alert.category, alert.severity
| filter event_type = "alert"
| sort @timestamp desc
| limit 50
```

---

### Mẫu 3: Danh Sách Tên Miền Bị AWS Network Firewall Chặn (Egress Drop)
Áp dụng cho Log Group: `/aws/network-firewall/fabric-egress-alerts`:
```sql
fields @timestamp, event.src_ip, event.dest_ip, event.dest_port, event.http.hostname, event.alert.signature
| filter event.alert.action = "drop" or event.alert.action = "blocked"
| stats count(*) as dropCount by event.http.hostname, event.src_ip
| sort dropCount desc
| limit 20
```

---

### Mẫu 4: Top IP Tấn Công Bị Chặn Bởi AWS WAF v2
Áp dụng cho Log Group WAF Ingress:
```sql
fields @timestamp, httpRequest.clientIp, httpRequest.country, terminatingRuleId, httpRequest.uri
| filter action = "BLOCK"
| stats count(*) as blockCount by httpRequest.clientIp, terminatingRuleId
| sort blockCount desc
| limit 20
```

---

## 3. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Cả 4 mẫu truy vấn được lưu lại vào mục **Saved queries** trong CloudWatch Logs Insights.
- [ ] Thời gian trả lời truy vấn dưới 3 giây đối với tập dữ liệu thực nghiệm.

