# 10.05 — GameDay Kịch Bản 5: Mất Tuyến Đường Về Tại Cổng Ra Tập Trung (NAT Return-Path Loss)

> **Mã bài lab:** `10.05`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã triển khai hoàn tất phân hệ Centralized Egress Firewall tại [Module 06](../06-centralized-egress-firewall/04-egress-routing-and-domain-filtering-test.md).
- Bảng định tuyến `fabric-egress-public-rt` đang cấu hình đầy đủ các tuyến đường quay về cho Edge (`10.40.0.0/16`) và Core (`10.50.0.0/16`).
- Các Pod trong Core EKS có thể kết nối ra ngoài Internet (ví dụ tải image từ Docker Registry hoặc GitHub API) qua cổng NAT Gateway tập trung.
- Đang mở phiên AWS Management Console tại Singapore (`ap-southeast-1`).

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để tiêm lỗi và khôi phục bảng định tuyến VPC:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateRoute",
        "ec2:DeleteRoute",
        "ec2:ReplaceRoute",
        "ec2:DescribeRouteTables",
        "logs:StartQuery",
        "logs:GetQueryResults"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Thao tác trên Route Tables không phát sinh chi phí ($0.00 USD).
- **Hiện tượng Blackhole một chiều (One-Way Traffic Drop):** Trong mô hình mạng tập trung với NAT Gateway và Tường lửa, một trong những lỗi khó chẩn đoán nhất là khi gói tin chiều đi (Outbound) đi ra Internet hoàn toàn bình thường, nhưng gói tin phản hồi (Return traffic) bị rơi vào "hố đen" (Blackhole) tại subnet của NAT Gateway vì thiếu route chỉ đường quay về mạng nội bộ. Việc nắm vững cách bắt lỗi bằng VPC Flow Logs là kỹ năng tối quan trọng của SRE và Network Architect.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Kiểm Tra Trạng Thái Định Tuyến Chuẩn Ban Đầu (Baseline Check)
1. Mở **VPC Console** tại Region Singapore (`ap-southeast-1`).
2. Tại menu bên trái, chọn **Route tables**.
3. Tìm và chọn bảng định tuyến: `fabric-egress-public-rt`.
4. Mở tab **Routes**:
   - Đảm bảo có route: `10.50.0.0/16` trỏ về Network Firewall Endpoint (`vpce-xxxxxxxxxxxxxxxxx`) hoặc Transit Gateway.
5. Từ một Pod trong Core EKS, kiểm tra kết nối ra ngoài Internet:
   ```bash
   kubectl exec -it deploy/order -n default -- curl -m 5 -Iv https://registry-1.docker.io
   ```
   *Kết quả:* Kết nối TLS thành công (HTTP 200 hoặc 401 Unauthorized từ Docker Hub).

---

### Bước 2: Tiêm Lỗi — Xóa Tuyến Đường Quay Về Của Mạng Core (Fault Injection)
1. Trên bảng định tuyến **`fabric-egress-public-rt`**, chọn tab **Routes**.
2. Nhấp nút **Edit routes** ở góc trên bên phải bảng.
3. Tìm dòng có Destination: **`10.50.0.0/16`**.
4. Nhấp nút **Remove** (Xóa) ở bên phải dòng này.
5. Ghi lại mốc thời gian chính xác lúc bấm lưu: **$T_{fault}$** (Ví dụ: `11:00:00 UTC`).
6. Nhấp nút màu cam **Save changes**.
7. Xác nhận bảng `fabric-egress-public-rt` hiện chỉ còn tuyến `0.0.0.0/0 -> igw` và `10.60.0.0/16 -> local`.

---

### Bước 3: Quan Sát Hiện Tượng "Hố Đen" & Điều Tra Bằng VPC Flow Logs
1. **Kiểm tra truy cập Internet từ Core Pod:**
   ```bash
   kubectl exec -it deploy/order -n default -- curl -m 5 -Iv https://registry-1.docker.io
   ```
   - **Hiện tượng thực tế:** Lệnh `curl` bị treo hoàn toàn và báo lỗi:
     `curl: (28) Failed to connect to registry-1.docker.io port 443: Connection timed out`.
2. **Phân tích cơ chế kỹ thuật (Root Cause Analysis):**
   - **Chiều đi:** Core Pod (`10.50.10.x`) -> TGW -> Inspection Subnet -> Network Firewall -> NAT Gateway -> IGW -> Internet (Gói tin SYN gửi đi thành công).
   - **Chiều về:** Server Internet gửi lại gói `SYN-ACK` về IP công khai của NAT Gateway.
   - NAT Gateway thực hiện DNAT chuyển địa chỉ đích thành `10.50.10.x`.
   - NAT Gateway tra cứu bảng định tuyến của Public Subnet (`fabric-egress-public-rt`) để tìm đường về `10.50.10.x`. Do route `10.50.0.0/16` đã bị xóa, bảng chỉ có route `0.0.0.0/0 -> igw`. NAT Gateway không thể định tuyến gói tin RFC1918 ngược ra Internet Gateway -> **Gói tin bị drop tại chỗ!**
3. **Mở CloudWatch Logs Insights điều tra:**
   - Mở dịch vụ **CloudWatch** -> **Logs Insights**.
   - Chọn Log Group: `/aws/vpc/fabric-egress-flow`.
   - Chạy query kiểm tra lưu lượng outbound vs inbound:
     ```sql
     fields @timestamp, srcAddr, dstAddr, srcPort, dstPort, action, protocol
     | filter srcAddr = "10.50.10.x" or dstAddr = "10.50.10.x"
     | sort @timestamp desc
     | limit 20
     ```
   - *Phát hiện:* Bản ghi lưu lượng outbound có trạng thái `ACCEPT`, nhưng hoàn toàn không có bất kỳ gói tin inbound nào có destination `10.50.10.x` quay trở lại.
   - Ghi lại mốc thời gian phát hiện: **$T_{detect}$**.

---

### Bước 4: Khắc Phục Sự Cố — Tái Tạo Tuyến Đường Về (Remediation)
1. Quay lại trang chi tiết bảng định tuyến **`fabric-egress-public-rt`**.
2. Chọn tab **Routes** -> Nhấp **Edit routes**.
3. Nhấp nút **Add route**:
   - **Destination:** Nhập `10.50.0.0/16`
   - **Target:** Chọn **`VPC Endpoint`** -> Chọn Endpoint của AWS Network Firewall trong cùng AZ (`vpce-xxxxxxxxxxxxxxxxx` thuộc `fabric-egress-nfw`).
4. Ghi lại timestamp: **$T_{mitigate}$**.
5. Nhấp nút cam **Save changes**.

---

### Bước 5: Kiểm Chứng Phục Hồi Hoàn Toàn (Verification)
1. Thực hiện lại lệnh kết nối từ Core Pod:
   ```bash
   kubectl exec -it deploy/order -n default -- curl -m 5 -Iv https://registry-1.docker.io
   ```
   *Kết quả phục hồi:* Bắt tay TLS thành công, kết nối đạt trạng thái `Connected to registry-1.docker.io`.
2. Ghi lại mốc thời gian phục hồi hoàn toàn: **$T_{recover}$**.
3. Tính toán các chỉ số GameDay:
   - $MTTD = T_{detect} - T_{fault}$
   - $MTTR = T_{recover} - T_{fault}$

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra bảng định tuyến Public Subnet qua AWS CLI để xác nhận tuyến đường về đã hiện diện:

```bash
RT_ID=$(aws ec2 describe-route-tables \
  --region ap-southeast-1 \
  --filters "Name=tag:Name,Values=fabric-egress-public-rt" \
  --query 'RouteTables[0].RouteTableId' \
  --output text)

aws ec2 describe-route-tables \
  --region ap-southeast-1 \
  --route-table-ids "$RT_ID" \
  --query 'RouteTables[0].Routes[*].{Destination:DestinationCidrBlock,GatewayId:GatewayId,VpcEndpointId:VpcEndpointId,State:State}' \
  --output table
```

**Kỳ vọng kết quả mẫu:**
```text
--------------------------------------------------------------------------------------
|                                DescribeRouteTables                                 |
+------------------+---------------------+----------------------------+----------+
|   Destination    |      GatewayId      |       VpcEndpointId        |  State   |
+------------------+---------------------+----------------------------+----------+
|  0.0.0.0/0       |  igw-0123456789...  |  None                      |  active  |
|  10.50.0.0/16    |  None               |  vpce-0123456789abcdef0    |  active  |
|  10.40.0.0/16    |  None               |  vpce-0123456789abcdef0    |  active  |
|  10.60.0.0/16    |  local              |  None                      |  active  |
+------------------+---------------------+----------------------------+----------+
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Lệnh khẩn cấp một dòng qua AWS CLI để khôi phục tuyến đường về nếu giao diện Console bị treo:

```bash
NFW_VPCE_ID=$(aws ec2 describe-vpc-endpoints \
  --region ap-southeast-1 \
  --filters "Name=tag:Name,Values=*fabric-egress-nfw*" \
  --query 'VpcEndpoints[0].VpcEndpointId' \
  --output text)

aws ec2 create-route \
  --region ap-southeast-1 \
  --route-table-id "$RT_ID" \
  --destination-cidr-block "10.50.0.0/16" \
  --vpc-endpoint-id "$NFW_VPCE_ID"
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

- `evidence/10-gameday/gameday-05-nat-return-loss-timeline.json`: Ghi nhận timeline $T_{fault}, T_{detect}, T_{recover}$.
- `evidence/10-gameday/gameday-05-flowlogs-one-way-traffic.json`: Bằng chứng Flow Logs thể hiện luồng gói tin một chiều bị ngắt.
- `evidence/10-gameday/gameday-05-restored-routes.json`: Cấu hình route table sau khi khôi phục an toàn.

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Thực hiện xóa route quay về `10.50.0.0/16` và quan sát được lỗi kết nối timeout từ Core Pod.
- [ ] Giải thích và chứng minh được cơ chế Blackhole tại NAT Gateway bằng VPC Flow Logs.
- [ ] Bổ sung lại route trỏ qua Network Firewall Endpoint trên AWS Console thành công.
- [ ] Lưu lượng Egress Internet từ Core EKS phục hồi thông suốt hoàn toàn (MTTR < 10 phút).
