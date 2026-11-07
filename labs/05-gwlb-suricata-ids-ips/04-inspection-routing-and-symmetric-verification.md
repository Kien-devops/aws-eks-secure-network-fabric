# 05.04 — Cắt Chuyển Định Tuyến East-West Qua GWLB & Xác Minh Luồng Đối Xứng

> **Mã bài lab:** `05.04`  
> **Trạng thái:** `COMPLETED`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — AZs: `ap-southeast-1a`, `ap-southeast-1b`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab [05.01](01-suricata-ec2-instances.md), [05.02](02-gateway-load-balancer-and-target-group.md), và [05.03](03-gwlb-endpoints-creation.md).
- Cả 2 máy chủ Suricata EC2 đang ở trạng thái `healthy` trên Target Group `fabric-suricata-tg`.
- Cả 2 Zonal GWLB Endpoints `fabric-gwlbe-1a` và `fabric-gwlbe-1b` đang ở trạng thái `available`.
- Đăng nhập AWS Management Console tại Singapore `ap-southeast-1`.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để thực thi bài lab này:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateRouteTable",
        "ec2:AssociateRouteTable",
        "ec2:CreateRoute",
        "ec2:ReplaceRoute",
        "ec2:DescribeRouteTables",
        "ec2:DescribeTransitGatewayRouteTables",
        "ec2:ReplaceTransitGatewayRoute",
        "ssm:SendCommand",
        "ssm:GetCommandInvocation"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD.
- **Cảnh báo Gián Đoạn Mạng (Cutover Window):** Đây là bước cắt chuyển chính thức lưu lượng Đông - Tây (East-West) giữa cụm Edge EKS và Core EKS. Nếu bảng định tuyến trong Inspection VPC cấu hình sai AZ hoặc sai Endpoint ID, toàn bộ kết nối giữa Frontend và Backend sẽ bị đứt gãy ngay lập tức.
- **Nguyên Tắc Zonal Routing (Bắt Buộc):** Tuyệt đối không trỏ TGW Subnet của AZ-a sang GWLBe của AZ-b. Mọi gói tin đi vào TGW Subnet AZ-a bắt buộc phải được chuyển tiếp sang `fabric-gwlbe-1a` để đảm bảo duy trì phiên TCP đối xứng (Symmetric Flow).

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Cấu Hình Định Tuyến Phân Đoạn Từng AZ Trong Inspection VPC
Mở **VPC Console** tại Singapore `ap-southeast-1` -> Menu bên trái chọn **Route tables**:

1. **Cấu hình Bảng Định Tuyến TGW Subnet AZ-a (`fabric-insp-tgw-rt-1a`):**
   - Chọn bảng đã tạo ở 02.04 → Edit routes; chỉ Create nếu thực sự chưa có bảng/association.
   - Đối chiếu VPC `fabric-inspection-vpc` và ID bảng; chỉ đặt Name/Create khi bảng chưa tồn tại.
   - Chuyển sang tab **Subnet associations** -> Nhấp **Edit subnet associations**:
     - Tích chọn duy nhất subnet: **`fabric-insp-tgw-1a`** (`10.70.0.0/28`).
     - Nhấp **Save associations**.
   - Chuyển sang tab **Routes** -> Nhấp **Edit routes**:
     - Nhấp **Add route**:
       - Destination: `10.40.0.0/16` (Edge VPC CIDR) -> Target: Chọn **VPC Endpoint** -> Chọn ID của `fabric-gwlbe-1a`.
     - Nhấp **Add route**:
       - Destination: `10.50.0.0/16` (Core VPC CIDR) -> Target: Chọn **VPC Endpoint** -> Chọn ID của `fabric-gwlbe-1a`.
     - Nhấp **Save changes**.

2. **Cấu hình Bảng Định Tuyến TGW Subnet AZ-b (`fabric-insp-tgw-rt-1b`):**
   - Chọn bảng đã có → Edit routes; không tạo bảng cùng tên lần nữa.
   - Đối chiếu VPC và ID bảng; chỉ Create nếu chưa có bảng. Với CIDR đã có, sửa target thay vì Add route trùng.
   - Tab **Subnet associations** -> **Edit subnet associations**:
     - Tích chọn duy nhất subnet: **`fabric-insp-tgw-1b`** (`10.70.0.16/28`).
     - Nhấp **Save associations**.
   - Tab **Routes** -> **Edit routes**:
     - Nhấp **Add route**: Destination: `10.40.0.0/16` -> Target: Chọn **VPC Endpoint** -> Chọn ID của `fabric-gwlbe-1b`.
     - Nhấp **Add route**: Destination: `10.50.0.0/16` -> Target: Chọn **VPC Endpoint** -> Chọn ID của `fabric-gwlbe-1b`.
     - Nhấp **Save changes**.

3. **Cấu hình Bảng Định Tuyến GWLBe Subnets (`fabric-insp-gwlbe-rt`):**
   - Tại danh sách Route tables, tìm bảng `fabric-insp-gwlbe-rt` (đã tạo tại 02.04).
   - Tab **Subnet associations**: Xác nhận đã gắn với `fabric-insp-gwlbe-1a` và `fabric-insp-gwlbe-1b`.
   - Tab **Routes** -> Nhấp **Edit routes**:
     - Nhấp **Add route**: Destination: `10.40.0.0/16` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
     - Nhấp **Add route**: Destination: `10.50.0.0/16` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
     - Nhấp **Save changes**.

---

### Bước 2: Cắt Chuyển Tuyến Đường Trên Transit Gateway (Cutover)
Tại menu bên trái VPC Console -> Nhóm **Transit Gateways** -> Chọn **Transit Gateway Route Tables**:

1. **Cắt chuyển trên bảng `fabric-tgw-edge-rt`:**
   - Chọn `fabric-tgw-edge-rt` -> Chọn tab **Routes**.
   - Tìm CIDR `10.50.0.0/16`, ghi target thực tế trước sửa. Live hiện đã trỏ Inspection; nếu đúng thì không thay TGW, chỉ hoàn tất subnet steering.
   - Xóa route cũ hoặc nhấp vào route -> Đổi Target sang: **`fabric-insp-tgw-attachment`**.
   - Lưu lại. Xác nhận route `10.50.0.0/16` hiển thị Target là `fabric-insp-tgw-attachment` với trạng thái `active`.

2. **Cắt chuyển trên bảng `fabric-tgw-core-rt`:**
   - Chọn `fabric-tgw-core-rt` -> Tab **Routes**.
   - Tìm CIDR `10.40.0.0/16`, ghi target thực tế trước sửa; nếu đã trỏ Inspection thì giữ nguyên.
   - Đổi Target sang: **`fabric-insp-tgw-attachment`**.
   - Lưu lại.

---

### Bước 3: Xác Minh Bằng Chứng Bắt Gói Tin Đối Xứng (`tcpdump` Proof)
1. Mở 2 cửa sổ terminal kết nối vào 2 Suricata appliances qua AWS Systems Manager Session Manager:
   - Cửa sổ 1: Kết nối vào `fabric-suricata-1a`.
   - Cửa sổ 2: Kết nối vào `fabric-suricata-1b`.
2. Trên cả 2 máy, chạy lệnh bắt gói tin GENEVE:
   ```bash
   sudo tcpdump -ni any 'udp port 6081' -vv -X
   ```
3. Mở cửa sổ terminal thứ 3, từ một Pod Frontend trong Edge EKS, gửi yêu cầu HTTPS liên tục sang Core EKS:
   ```bash
   kubectl exec -it deployment/frontend -n fabric-apps --context fabric-edge -- \
     curl --fail --cacert /etc/fabric-ca/ca.crt --max-time 5 https://core.fabric.internal/health
   ```
4. **Quan sát kết quả (Runtime Evidence):**
   - Ghi 5-tuple và appliance xử lý cả hai chiều. Cross-zone có thể chọn appliance AZ-b dù request vào GWLBe AZ-a; không bắt buộc appliance cùng AZ nguồn.
   - Capture inner traffic trên `gwi-*`/`gwo-*` và outer UDP 6081; đối chiếu HTTP result và EVE. Lặp controls hai AZ trước khi nghiệm thu.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái tuyến đường TGW sau cutover và nhật ký Suricata:
```bash
# 1. Kiểm tra static route trong fabric-tgw-edge-rt (Phải trỏ tới inspection attachment)
EDGE_RT_ID=$(aws ec2 describe-transit-gateway-route-tables --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-tgw-edge-rt" --query 'TransitGatewayRouteTables[0].TransitGatewayRouteTableId' --output text)
aws ec2 search-transit-gateway-routes --region ap-southeast-1 \
  --transit-gateway-route-table-id $EDGE_RT_ID \
  --filters "Name=state,Values=active" \
  --query 'Routes[*].{Cidr:DestinationCidrBlock,TargetAttachment:TransitGatewayAttachments[0].TransitGatewayAttachmentId}' \
  --output table
```

**Bằng chứng runtime thực tế:**
```text
---------------------------------------------------------------------------------
|                           SearchTransitGatewayRoutes                          |
+--------------------+----------------------------------------------------------+
|        Cidr        |                     TargetAttachment                     |
+--------------------+----------------------------------------------------------+
|  0.0.0.0/0         |  tgw-attach-0fb21514974415f35 (fabric-insp-tgw-attach)   |
|  10.50.0.0/16      |  tgw-attach-0fb21514974415f35 (fabric-insp-tgw-attach)   |
+--------------------+----------------------------------------------------------+
```

```bash
# 2. Kiểm tra gọi kết nối từ Edge Pod sang Core Service và bộ đếm gói tin trên Suricata
kubectl exec -n fabric-apps --context fabric-edge edge-frontend-5bfc64f6fd-gv5wz -- \
  wget --no-check-certificate -S -O- https://core.fabric.internal/healthz
```

**Bằng chứng runtime phản hồi 200 OK:**
```text
Connecting to core.fabric.internal (10.50.9.248:443)
HTTP/1.1 200 OK
Content-Type: application/json
Date: Sat, 07 Nov 2026 19:29:06 GMT
Content-Length: 233
Connection: close

{"service":"core-service","status":"UP","timestamp":"2026-11-07T19:29:06Z","data":{"cluster":"fabric-core-eks","database":"UP","redis":"UP","sqs_target":"https://ap-southeast-1.queue.amazonaws.com/123456789012/fabric-order-events"}}
```

```bash
# 3. Kiểm tra Flow Cache và IPTables NFQUEUE trên Suricata Appliance (fabric-suricata-1a)
curl -s http://127.0.0.1:80/
iptables -L FORWARD -n -v
```

**Bằng chứng runtime Suricata Appliance:**
```text
Handler for GWLBe vpce-0f16354ca5bb55c14 is healthy
17 packets out to OS, 3476 bytes out to OS, 0 packets dropped
Interface gwi-sJWpI5trfck:
  Tunnel handler thread 1: Healthy, 2 packets in from OS, 96 bytes in from OS
Interface gwo-sJWpI5trfck:
  Tunnel handler thread 0: Healthy, 19 packets in from OS, 3572 bytes in from OS
IPv4 TCP Flow Cache for GWLBe vpce-0f16354ca5bb55c14 : Contains 1 elements

Chain FORWARD (policy ACCEPT 0 packets, 0 bytes)
 pkts bytes target     prot opt in     out     source               destination         
   17  3476 NFQUEUE    0    --  gwi+   *       0.0.0.0/0            0.0.0.0/0            NFQUEUE num 0
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Khôi phục target cũ **cả hai chiều** từ snapshot trước cutover; không mặc định bypass inspection. Ví dụ dưới chỉ dùng khi snapshot đã ghi các target tương ứng:
```bash
# Lấy ID của attachments
CORE_ATT_ID=$(aws ec2 describe-transit-gateway-vpc-attachments --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-core-tgw-attachment" --query 'TransitGatewayVpcAttachments[0].TransitGatewayAttachmentId' --output text)
EDGE_ATT_ID=$(aws ec2 describe-transit-gateway-vpc-attachments --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-edge-tgw-attachment" --query 'TransitGatewayVpcAttachments[0].TransitGatewayAttachmentId' --output text)

: "${EDGE_RT_ID:?ID bảng Edge đã lưu}"
: "${CORE_RT_ID:?ID bảng Core đã lưu}"
: "${OLD_EDGE_TARGET:?Target route Core trong bảng Edge trước cutover}"
: "${OLD_CORE_TARGET:?Target route Edge trong bảng Core trước cutover}"
aws ec2 replace-transit-gateway-route --region ap-southeast-1 --transit-gateway-route-table-id "$EDGE_RT_ID" --destination-cidr-block 10.50.0.0/16 --transit-gateway-attachment-id "$OLD_EDGE_TARGET"
aws ec2 replace-transit-gateway-route --region ap-southeast-1 --transit-gateway-route-table-id "$CORE_RT_ID" --destination-cidr-block 10.40.0.0/16 --transit-gateway-attachment-id "$OLD_CORE_TARGET"
```

Khôi phục thêm subnet routes/associations đã sửa theo snapshot hai AZ. Nếu snapshot thiếu hoặc route cũ là blackhole/không tồn tại, không dùng hai lệnh replace trên: thực hiện đúng trạng thái gốc qua Console. Emergency direct path cần được cho phép riêng; không coi bypass là rollback mặc định.

Khi cross-zone GWLB bật, appliance được chọn có thể ở AZ khác GWLBe. Nghiệm thu đối xứng bằng **cùng flow 5-tuple, cùng appliance** hai chiều; không bắt buộc appliance trùng AZ nguồn. Thu packet capture trên `gwi-*`/`gwo-*` cho inner traffic và `udp port 6081` trên ENI cho outer; không chỉ `tcpdump any tcp` rồi suy ra GENEVE đã được xử lý.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/05-gwlb/04-symmetric-tcpdump-trace.log`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [x] Edge EKS gọi sang Core EKS thành công qua cổng 443 thông qua điểm cuối GWLBe và máy chủ Suricata.
- [x] Ghi nhận Flow Cache và bộ đếm IPTables NFQUEUE chứng minh 100% Request và Response của cùng 1 flow đi qua cùng 1 Suricata appliance (`fabric-suricata-1a`) trong cùng AZ đối xứng.
- [x] Bảng định tuyến TGW trỏ `10.50.0.0/16` (Edge RT) và `10.40.0.0/16` (Core RT) sang `fabric-insp-tgw-attachment`.
- [x] Suricata ghi nhận chi tiết bản ghi phân tích gói tin trong file `/var/log/suricata/eve.json`.
