# 09.03 — Xây Dựng Thư Viện Truy Vấn CloudWatch Logs Insights Phân Tích Sự Cố Mạng

> **Mã bài lab:** `09.03`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 35 phút  
> **Chi phí ước tính:** ~$0.05 USD (Chi phí quét dữ liệu CloudWatch Insights)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn tất tạo 8 Log Groups tập trung tại [Lab 09.01](01-centralized-cloudwatch-log-groups.md).
- VPC Flow Logs, Suricata EVE Logs, AWS Network Firewall, và AWS WAF đang hoạt động và đã phát sinh bản ghi nhật ký.
- Tài khoản IAM có quyền truy vấn và lưu trữ cấu hình Saved Queries trong CloudWatch Logs.
- Trình duyệt đang mở tại CloudWatch Console khu vực Singapore (`ap-southeast-1`).

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để xây dựng và thực thi các câu truy vấn Insights:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:StartQuery",
        "logs:StopQuery",
        "logs:GetQueryResults",
        "logs:DescribeQueries",
        "logs:DescribeLogGroups",
        "logs:PutQueryDefinition",
        "logs:DescribeQueryDefinitions",
        "logs:DeleteQueryDefinition"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Cơ chế tính cước CloudWatch Logs Insights:** AWS tính phí **$0.005 cho mỗi GB** dữ liệu nhật ký được quét qua câu truy vấn.
- **Tối ưu hóa FinOps:**
  - Luôn chọn phạm vi thời gian (Time window) hẹp và chính xác (ví dụ: `1 hour`, `3 hours`, hoặc thời điểm diễn ra GameDay), tránh chọn `1 week` hoặc `All time` trên các Log Group dung lượng lớn.
  - Luôn sử dụng lệnh `limit` trong câu truy vấn để giảm tải xử lý phía máy trạm.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Điều Hướng Đến Giao Diện CloudWatch Logs Insights
1. Đăng nhập vào **AWS Management Console** -> Chọn Region Singapore (`ap-southeast-1`).
2. Mở dịch vụ **CloudWatch**.
3. Tại thanh điều hướng bên trái, mở rộng mục **Logs** -> Nhấp vào **Logs Insights**.

---

### Bước 2: Tạo & Lưu Truy Vấn 1 — Top Gói Tin Bị REJECT Trên Toàn Bộ VPC
1. Tại ô **Select log group(s)** ở đầu màn hình, nhấp chuột để chọn đồng thời 4 Log Groups:
   - `/aws/vpc/fabric-edge-flow`
   - `/aws/vpc/fabric-core-flow`
   - `/aws/vpc/fabric-inspection-flow`
   - `/aws/vpc/fabric-egress-flow`
2. Đặt khung thời gian (Time range) ở góc trên bên phải: Chọn **`1 hour`**.
3. Trong khung soạn thảo câu truy vấn, xóa code mặc định và dán nội dung:
   ```sql
   fields @timestamp, srcAddr, dstAddr, srcPort, dstPort, protocol, action
   | filter action = "REJECT"
   | stats count(*) as rejectedCount by srcAddr, dstAddr, dstPort
   | sort rejectedCount desc
   | limit 20
   ```
4. Nhấp nút xanh dương **Run query** để chạy kiểm tra. Quan sát kết quả dạng bảng ở khung bên dưới.
5. **Lưu truy vấn (Save Query):**
   - Nhấp vào nút **Save** ở phía trên khung soạn thảo.
   - Hộp thoại *Save query* hiện ra:
     - **Query name:** `fabric-vpc-flow-top-rejects`
     - **Folder:** Chọn `Default` (hoặc tạo folder mới `Fabric-Network-Ops`)
   - Nhấp **Save**.

---

### Bước 3: Tạo & Lưu Truy Vấn 2 — Cảnh Báo An Ninh Tấn Công Từ Suricata EVE
1. Nhấp nút dấu x để xóa các Log Groups đang chọn.
2. Tại ô **Select log group(s)**, chọn duy nhất:
   - `/aws/suricata/fabric-inspection-eve`
3. Trong khung soạn thảo, dán câu truy vấn phân tích cảnh báo an ninh:
   ```sql
   fields @timestamp, src_ip, dest_ip, dest_port, alert.signature, alert.category, alert.severity
   | filter event_type = "alert"
   | sort @timestamp desc
   | limit 50
   ```
4. Nhấp **Run query** để kiểm tra.
5. Nhấp **Save**:
   - **Query name:** `fabric-suricata-ids-alerts`
   - **Folder:** `Fabric-Network-Ops`
   - Nhấp **Save**.

---

### Bước 4: Tạo & Lưu Truy Vấn 3 — Danh Sách Tên Miền Bị AWS Network Firewall Chặn (Egress Drops)
1. Đổi Log Group được chọn sang:
   - `/aws/network-firewall/fabric-egress-alerts`
2. Dán câu truy vấn đối soát vi phạm chính sách Egress domain:
   ```sql
   fields @timestamp, event.src_ip, event.dest_ip, event.dest_port, event.http.hostname, event.alert.signature
   | filter event.alert.action = "drop" or event.alert.action = "blocked"
   | stats count(*) as dropCount by event.http.hostname, event.src_ip
   | sort dropCount desc
   | limit 20
   ```
3. Nhấp **Run query**.
4. Nhấp **Save**:
   - **Query name:** `fabric-nfw-egress-blocked-domains`
   - **Folder:** `Fabric-Network-Ops`
   - Nhấp **Save**.

---

### Bước 5: Tạo & Lưu Truy Vấn 4 — Top Địa Chỉ IP Bị Chặn Bởi AWS WAF v2 Ingress
1. Đổi Log Group được chọn sang:
   - `aws-waf-logs-fabric-edge-waf`
2. Dán câu truy vấn điều tra nguồn tấn công L7:
   ```sql
   fields @timestamp, httpRequest.clientIp, httpRequest.country, terminatingRuleId, httpRequest.uri
   | filter action = "BLOCK"
   | stats count(*) as blockCount by httpRequest.clientIp, httpRequest.country, terminatingRuleId
   | sort blockCount desc
   | limit 20
   ```
3. Nhấp **Run query**.
4. Nhấp **Save**:
   - **Query name:** `fabric-waf-top-blocked-ips`
   - **Folder:** `Fabric-Network-Ops`
   - Nhấp **Save**.

---

### Bước 6: Kiểm Tra Quản Lý Thư Viện Queries (Queries Tab)
1. Trên giao diện Logs Insights, nhấp vào tab **Queries** ở cột bên phải.
2. Mở thư mục `Fabric-Network-Ops`.
3. Xác nhận đầy đủ 4 truy vấn đã được lưu:
   - `fabric-vpc-flow-top-rejects`
   - `fabric-suricata-ids-alerts`
   - `fabric-nfw-egress-blocked-domains`
   - `fabric-waf-top-blocked-ips`
4. Thử nhấp vào một query bất kỳ để tải nhanh cấu hình lên khung soạn thảo.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Liệt kê toàn bộ các Query Definitions đã lưu trong tài khoản AWS:

```bash
aws logs describe-query-definitions \
  --region ap-southeast-1 \
  --query 'queryDefinitions[?contains(name, `fabric`)].{Name:name,QueryString:queryString,LogGroups:logGroupNames}' \
  --output table
```

Chạy thử nghiệm một câu truy vấn qua CLI và lấy kết quả:
```bash
# 1. Khởi động query
QUERY_ID=$(aws logs start-query \
  --region ap-southeast-1 \
  --log-group-name "/aws/vpc/fabric-edge-flow" \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, srcAddr, dstAddr, action | filter action = "REJECT" | limit 5' \
  --query 'queryId' \
  --output text)

echo "Query Started: ID=$QUERY_ID"
sleep 5

# 2. Lấy kết quả truy vấn
aws logs get-query-results \
  --region ap-southeast-1 \
  --query-id "$QUERY_ID" \
  --query '{Status:status,RecordsScanned:statistics.recordsScanned,BytesScanned:statistics.bytesScanned,Results:results}'
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Khi cần dọn dẹp các Saved Queries đã tạo:
1. Mở CloudWatch Logs Insights Console -> Tab **Queries**.
2. Tìm thư mục `Fabric-Network-Ops` -> Nhấp biểu tượng 3 dấu chấm cạnh tên từng Query -> Chọn **Delete**.
3. Hoặc xóa qua AWS CLI bằng lệnh:
   ```bash
   QUERY_DEF_ID=$(aws logs describe-query-definitions --region ap-southeast-1 --query 'queryDefinitions[?name==`fabric-vpc-flow-top-rejects`].queryDefinitionId' --output text)
   [ -n "$QUERY_DEF_ID" ] && aws logs delete-query-definition --region ap-southeast-1 --query-definition-id "$QUERY_DEF_ID"
   ```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

- `evidence/09-observability/saved-queries.json`: Xuất danh sách các câu truy vấn đã lưu.
- `evidence/09-observability/sample-query-execution-results.json`: Kết quả thực tế từ lệnh `get-query-results`.

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Tạo và lưu thành công 4 câu truy vấn Saved Queries trong CloudWatch Logs Insights.
- [ ] Cú pháp truy vấn chuẩn xác, có tính năng gom nhóm thống kê (`stats count(*)`) và giới hạn số bản ghi (`limit`).
- [ ] Lệnh CLI `describe-query-definitions` liệt kê đầy đủ 4 định nghĩa truy vấn.
- [ ] Các truy vấn quét đúng log groups tương ứng của từng phân hệ (VPC, Suricata, Network Firewall, WAF).
