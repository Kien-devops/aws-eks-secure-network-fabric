# 02.03 — Khởi Tạo TGW VPC Attachments (Appliance Mode) & 4 Route Tables

> **Mã bài lab:** `02.03`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 40 phút  
> **Chi phí ước tính:** ~$0.28 USD/giờ (4 attachments x $0.07 USD/giờ)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — AZs: `ap-southeast-1a`, `ap-southeast-1b`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bài lab [02.01](01-four-vpcs-and-subnets.md) và [02.02](02-transit-gateway-setup.md).
- Transit Gateway `fabric-tgw` đang ở trạng thái `available`.
- 4 VPCs và 26 subnets đã sẵn sàng, đặc biệt là các Subnet TGW chuyên dụng (`/28`).

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
        "ec2:CreateTransitGatewayVpcAttachment",
        "ec2:DescribeTransitGatewayVpcAttachments",
        "ec2:CreateTransitGatewayRouteTable",
        "ec2:DescribeTransitGatewayRouteTables",
        "ec2:AssociateTransitGatewayRouteTable",
        "ec2:CreateTransitGatewayRoute",
        "ec2:SearchTransitGatewayRoutes",
        "ec2:CreateTags",
        "ec2:DeleteTransitGatewayVpcAttachment",
        "ec2:DeleteTransitGatewayRouteTable"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Mỗi TGW Attachment tính phí $0.07 USD/giờ. 4 Attachments sẽ tiêu tốn ~$6.72 USD/ngày.
- **Cảnh báo tính đối xứng (Appliance Mode):** Cực kỳ quan trọng: Khi gắn Attachment cho **Inspection VPC** (`fabric-insp-tgw-attachment`) và **Egress VPC** (`fabric-egress-tgw-attachment`), bạn **BẮT BUỘC PHẢI BẬT** tùy chọn `ApplianceModeSupport = enable`. Nếu không bật, TGW sẽ băm luồng (flow hashing) không đối xứng, khiến gói tin phản hồi bị drop trên Suricata hoặc AWS Network Firewall.
- **Lưu ý chu trình DAG (Tránh vòng lặp):** Trong bài lab này, tuyến Edge<->Core ban đầu sẽ được định tuyến trực tiếp tạm thời để kiểm tra thông mạng IP cơ bản. Tuyến đường này sẽ chính thức chuyển sang trỏ vào Inspection Attachment tại Module 05 sau khi GWLB và Suricata đã kiểm tra sức khỏe đạt 100%.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Khởi Tạo 4 Transit Gateway VPC Attachments
Truy cập **VPC Console** tại Singapore `ap-southeast-1`:
1. Tại menu bên trái, cuộn xuống nhóm **Transit Gateways** -> Chọn **Transit Gateway Attachments**.
2. Nhấp nút cam **Create transit gateway attachment** ở góc trên bên phải.

3. **Tạo Attachment 1 — Edge VPC Attachment:**
   - **Transit gateway ID:** Chọn `fabric-tgw`.
   - **Attachment type:** Chọn **VPC**.
   - **Attachment name tag:** Nhập `fabric-edge-tgw-attachment`.
   - **DNS support:** Chọn **Enable**.
   - **IPv6 support:** Để mặc định **Disable**.
   - **Appliance mode support:** Chọn **Disable** (Edge EKS không chứa thiết bị kiểm tra trạng thái tập trung).
   - **VPC ID:** Chọn `fabric-edge-vpc`.
   - **Subnet IDs:**
     - Tại `ap-southeast-1a`: Chọn subnet `fabric-edge-tgw-1a` (`10.40.250.0/28`).
     - Tại `ap-southeast-1b`: Chọn subnet `fabric-edge-tgw-1b` (`10.40.250.16/28`).
   - **Tags:** Key: `Project` | Value: `aws-eks-secure-network-fabric`.
   - Nhấp **Create transit gateway attachment**.

4. **Tạo Attachment 2 — Core VPC Attachment:**
   - Nhấp **Create transit gateway attachment**.
   - **Transit gateway ID:** Chọn `fabric-tgw`.
   - **Attachment type:** Chọn **VPC**.
   - **Attachment name tag:** Nhập `fabric-core-tgw-attachment`.
   - **DNS support:** Chọn **Enable**.
   - **Appliance mode support:** Chọn **Disable**.
   - **VPC ID:** Chọn `fabric-core-vpc`.
   - **Subnet IDs:**
     - Tại `ap-southeast-1a`: Chọn subnet `fabric-core-tgw-1a` (`10.50.250.0/28`).
     - Tại `ap-southeast-1b`: Chọn subnet `fabric-core-tgw-1b` (`10.50.250.16/28`).
   - Nhấp **Create transit gateway attachment**.

5. **Tạo Attachment 3 — Inspection VPC Attachment (Bắt Buộc Appliance Mode):**
   - Nhấp **Create transit gateway attachment**.
   - **Transit gateway ID:** Chọn `fabric-tgw`.
   - **Attachment type:** Chọn **VPC**.
   - **Attachment name tag:** Nhập `fabric-insp-tgw-attachment`.
   - **DNS support:** Chọn **Enable**.
   - **Appliance mode support:** Chọn **Enable** *(BẮT BUỘC: Giúp duy trì AZ affinity cho luồng kiểm tra GWLB/Suricata)*.
   - **VPC ID:** Chọn `fabric-inspection-vpc`.
   - **Subnet IDs:**
     - Tại `ap-southeast-1a`: Chọn subnet `fabric-insp-tgw-1a` (`10.70.0.0/28`).
     - Tại `ap-southeast-1b`: Chọn subnet `fabric-insp-tgw-1b` (`10.70.0.16/28`).
   - Nhấp **Create transit gateway attachment**.

6. **Tạo Attachment 4 — Centralized Egress VPC Attachment (Bắt Buộc Appliance Mode):**
   - Nhấp **Create transit gateway attachment**.
   - **Transit gateway ID:** Chọn `fabric-tgw`.
   - **Attachment type:** Chọn **VPC**.
   - **Attachment name tag:** Nhập `fabric-egress-tgw-attachment`.
   - **DNS support:** Chọn **Enable**.
   - **Appliance mode support:** Chọn **Enable** *(BẮT BUỘC: Đảm bảo luồng ra và luồng về của NAT/Firewall cùng một AZ)*.
   - **VPC ID:** Chọn `fabric-egress-vpc`.
   - **Subnet IDs:**
     - Tại `ap-southeast-1a`: Chọn subnet `fabric-egress-tgw-1a` (`10.80.0.0/28`).
     - Tại `ap-southeast-1b`: Chọn subnet `fabric-egress-tgw-1b` (`10.80.0.16/28`).
   - Nhấp **Create transit gateway attachment**.
7. Chờ cả 4 attachments chuyển trạng thái từ `pending` sang **`available`** (mất khoảng 2-3 phút).

### Bước 2: Khởi Tạo 4 Bảng Định Tuyến TGW (Route Tables)
Tại menu bên trái VPC Console -> Nhóm **Transit Gateways** -> Chọn **Transit Gateway Route Tables**:
1. Nhấp nút cam **Create transit gateway route table**.
   - **Name tag:** Nhập `fabric-tgw-edge-rt`.
   - **Transit gateway ID:** Chọn `fabric-tgw`.
   - Nhấp **Create transit gateway route table**.
2. Lặp lại tạo tiếp 3 bảng:
   - Name tag: `fabric-tgw-core-rt` | Transit gateway ID: `fabric-tgw`.
   - Name tag: `fabric-tgw-inspection-rt` | Transit gateway ID: `fabric-tgw`.
   - Name tag: `fabric-tgw-egress-rt` | Transit gateway ID: `fabric-tgw`.

### Bước 3: Cấu Hình Association (Liên Kết Attachment Vào Route Table)
Tại danh sách **Transit Gateway Route Tables**:
1. **Liên kết Edge:**
   - Chọn checkbox trước `fabric-tgw-edge-rt` -> Chọn tab **Associations** ở nửa dưới màn hình.
   - Nhấp nút **Create association**.
   - Tại mục **Choose attachment to associate**, chọn `fabric-edge-tgw-attachment`.
   - Nhấp **Create association**.
2. **Liên kết Core:**
   - Chọn `fabric-tgw-core-rt` -> Tab **Associations** -> Nhấp **Create association**.
   - Chọn attachment `fabric-core-tgw-attachment` -> Nhấp **Create association**.
3. **Liên kết Inspection:**
   - Chọn `fabric-tgw-inspection-rt` -> Tab **Associations** -> Nhấp **Create association**.
   - Chọn attachment `fabric-insp-tgw-attachment` -> Nhấp **Create association**.
4. **Liên kết Egress:**
   - Chọn `fabric-tgw-egress-rt` -> Tab **Associations** -> Nhấp **Create association**.
   - Chọn attachment `fabric-egress-tgw-attachment` -> Nhấp **Create association**.

### Bước 4: Cấu Hình Các Tuyến Định Tuyến Tĩnh (Static Routes)
Tại danh sách **Transit Gateway Route Tables**:

1. **Cấu hình trên `fabric-tgw-edge-rt`:**
   - Chọn `fabric-tgw-edge-rt` -> Chọn tab **Routes** -> Nhấp nút **Create static route**.
     - CIDR: Nhập `0.0.0.0/0` -> Choose attachment: Chọn `fabric-egress-tgw-attachment` -> Nhấp **Create static route**.
   - Tiếp tục nhấp **Create static route**:
     - CIDR: Nhập `10.50.0.0/16` -> Choose attachment: Chọn `fabric-core-tgw-attachment` (tuyến tạm thời, sẽ cutover sang Inspection tại Module 05) -> Nhấp **Create static route**.

2. **Cấu hình trên `fabric-tgw-core-rt`:**
   - Chọn `fabric-tgw-core-rt` -> Tab **Routes** -> Nhấp **Create static route**:
     - CIDR: Nhập `0.0.0.0/0` -> Choose attachment: Chọn `fabric-egress-tgw-attachment` -> Nhấp **Create static route**.
   - Tiếp tục nhấp **Create static route**:
     - CIDR: Nhập `10.40.0.0/16` -> Choose attachment: Chọn `fabric-edge-tgw-attachment` (tuyến tạm thời, sẽ cutover sang Inspection tại Module 05) -> Nhấp **Create static route**.

3. **Cấu hình trên `fabric-tgw-inspection-rt`:**
   - Chọn `fabric-tgw-inspection-rt` -> Tab **Routes** -> Nhấp **Create static route**:
     - CIDR: Nhập `10.40.0.0/16` -> Choose attachment: Chọn `fabric-edge-tgw-attachment` -> Nhấp **Create static route**.
   - Tiếp tục nhấp **Create static route**:
     - CIDR: Nhập `10.50.0.0/16` -> Choose attachment: Chọn `fabric-core-tgw-attachment` -> Nhấp **Create static route**.

4. **Cấu hình trên `fabric-tgw-egress-rt`:**
   - Chọn `fabric-tgw-egress-rt` -> Tab **Routes** -> Nhấp **Create static route**:
     - CIDR: Nhập `10.40.0.0/16` -> Choose attachment: Chọn `fabric-edge-tgw-attachment` -> Nhấp **Create static route**.
   - Tiếp tục nhấp **Create static route**:
     - CIDR: Nhập `10.50.0.0/16` -> Choose attachment: Chọn `fabric-core-tgw-attachment` -> Nhấp **Create static route**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy các lệnh xác minh trạng thái Attachment và cờ Appliance Mode:
```bash
# 1. Kiểm tra 4 attachments và cờ Appliance Mode
aws ec2 describe-transit-gateway-vpc-attachments --region ap-southeast-1 \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query 'TransitGatewayVpcAttachments[*].{Name:Tags[?Key==`Name`].Value | [0],Id:TransitGatewayAttachmentId,State:State,ApplianceMode:Options.ApplianceModeSupport}' \
  --output table

# 2. Kiểm tra 4 TGW Route Tables
aws ec2 describe-transit-gateway-route-tables --region ap-southeast-1 \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query 'TransitGatewayRouteTables[*].{Name:Tags[?Key==`Name`].Value | [0],Id:TransitGatewayRouteTableId,State:State}' \
  --output table

# 3. Kiểm tra các static routes trong fabric-tgw-edge-rt
EDGE_RT_ID=$(aws ec2 describe-transit-gateway-route-tables --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-tgw-edge-rt" --query 'TransitGatewayRouteTables[0].TransitGatewayRouteTableId' --output text)
aws ec2 search-transit-gateway-routes --region ap-southeast-1 \
  --transit-gateway-route-table-id $EDGE_RT_ID \
  --filters "Name=state,Values=active" \
  --query 'Routes[*].{Cidr:DestinationCidrBlock,Type:Type,State:State}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Trong trường hợp cần hoàn tác các attachments và route tables:
1. Tại VPC Console -> Transit Gateway Route Tables -> Xóa các static routes và associations.
2. Xóa 4 Route Tables: `fabric-tgw-edge-rt`, `fabric-tgw-core-rt`, `fabric-tgw-inspection-rt`, `fabric-tgw-egress-rt`.
3. Tại Transit Gateway Attachments -> Chọn từng attachment -> Actions -> Delete transit gateway attachment.
4. Hoặc thực thi qua CLI:
   ```bash
   for att_id in $(aws ec2 describe-transit-gateway-vpc-attachments --region ap-southeast-1 --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" --query 'TransitGatewayVpcAttachments[*].TransitGatewayAttachmentId' --output text); do
     aws ec2 delete-transit-gateway-vpc-attachment --region ap-southeast-1 --transit-gateway-attachment-id $att_id
   done
   ```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/02-network/03-tgw-attachments-and-routes.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Cả 4 VPC Attachments đều ở trạng thái `available`.
- [ ] Cờ `ApplianceModeSupport` của `fabric-insp-tgw-attachment` hiển thị chính xác `enable`.
- [ ] Cờ `ApplianceModeSupport` của `fabric-egress-tgw-attachment` hiển thị chính xác `enable`.
- [ ] 4 bảng định tuyến TGW Route Tables được phân tách và liên kết chính xác với từng attachment.
- [ ] Tắt hoàn toàn default propagation và default association.
