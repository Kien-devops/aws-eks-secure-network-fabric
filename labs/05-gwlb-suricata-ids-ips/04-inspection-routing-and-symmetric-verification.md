# 05.04 — Cắt Chuyển Định Tuyến East-West Qua GWLB & Xác Minh Luồng Đối Xứng

> **Mã bài lab:** `05.04`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
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
   - Nhấp nút cam **Create route table**.
   - **Name:** Nhập `fabric-insp-tgw-rt-1a`.
   - **VPC:** Chọn `fabric-inspection-vpc`.
   - Nhấp **Create route table**.
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
   - Nhấp **Create route table**.
   - **Name:** Nhập `fabric-insp-tgw-rt-1b` | **VPC:** Chọn `fabric-inspection-vpc`.
   - Nhấp **Create route table**.
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
   - Tìm dòng có CIDR `10.50.0.0/16` (trước đó đang trỏ tạm sang `fabric-core-tgw-attachment`).
   - Xóa route cũ hoặc nhấp vào route -> Đổi Target sang: **`fabric-insp-tgw-attachment`**.
   - Lưu lại. Xác nhận route `10.50.0.0/16` hiển thị Target là `fabric-insp-tgw-attachment` với trạng thái `active`.

2. **Cắt chuyển trên bảng `fabric-tgw-core-rt`:**
   - Chọn `fabric-tgw-core-rt` -> Tab **Routes**.
   - Tìm dòng có CIDR `10.40.0.0/16` (trước đó trỏ tạm sang `fabric-edge-tgw-attachment`).
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
     curl -vk https://core.fabric.internal/api/v1/orders/health
   ```
4. **Quan sát kết quả (Runtime Evidence):**
   - Nếu gói tin request đi vào qua AZ-a, toàn bộ các gói tin `SYN`, `SYN-ACK`, `ACK`, và `TLS Handshake` của phiên kết nối đó **CHỈ XUẤT HIỆN TRÊN MÁY `fabric-suricata-1a`**, hoàn toàn không bị phân mảnh hay nhảy sang máy `fabric-suricata-1b`.
   - Điều này chứng minh tính năng **TGW Appliance Mode** và **Zonal GWLBe Chaining** đã hoạt động hoàn hảo, bảo toàn tính đối xứng 100%.

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

# 2. Kiểm tra log sự kiện Suricata eve.json ghi nhận luồng HTTP/TLS vừa inspect
SURICATA_1A_ID=$(aws ec2 describe-instances --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-suricata-1a" --query 'Reservations[0].Instances[0].InstanceId' --output text)
aws ssm send-command --region ap-southeast-1 \
  --instance-ids $SURICATA_1A_ID \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["tail -n 10 /var/log/suricata/eve.json | jq ."]' \
  --output text
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Nếu xảy ra sự cố mất kết nối mạng sau khi cắt chuyển, lập tức hoàn tác route TGW về kết nối trực tiếp:
```bash
# Lấy ID của attachments
CORE_ATT_ID=$(aws ec2 describe-transit-gateway-vpc-attachments --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-core-tgw-attachment" --query 'TransitGatewayVpcAttachments[0].TransitGatewayAttachmentId' --output text)
EDGE_ATT_ID=$(aws ec2 describe-transit-gateway-vpc-attachments --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-edge-tgw-attachment" --query 'TransitGatewayVpcAttachments[0].TransitGatewayAttachmentId' --output text)

# Rollback TGW routes
aws ec2 replace-transit-gateway-route --region ap-southeast-1 --transit-gateway-route-table-id $EDGE_RT_ID --destination-cidr-block 10.50.0.0/16 --transit-gateway-attachment-id $CORE_ATT_ID
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/05-gwlb/04-symmetric-tcpdump-trace.log`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Edge EKS gọi sang Core EKS thành công qua cổng 443 thông qua điểm cuối GWLBe và máy chủ Suricata.
- [ ] Ghi nhận `tcpdump` chứng minh 100% Request và Response của cùng 1 flow đi qua cùng 1 Suricata appliance trong cùng AZ.
- [ ] Bảng định tuyến TGW trỏ `10.50.0.0/16` và `10.40.0.0/16` sang `fabric-insp-tgw-attachment`.
- [ ] Suricata ghi nhận chi tiết bản ghi phân tích gói tin trong file `/var/log/suricata/eve.json`.
