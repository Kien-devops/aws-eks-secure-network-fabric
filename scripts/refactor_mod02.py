#!/usr/bin/env python3
"""Refactor Module 02 files to standard 7-section format and resolve routing loops & VPC endpoints."""

from pathlib import Path

BASE = Path("E:/repo/project6/aws-eks-secure-network-fabric/labs/02-ha-tang-mang-co-ban")

# 01-four-vpcs-and-subnets.md
(BASE / "01-four-vpcs-and-subnets.md").write_text("""# 02.01 — Khởi Tạo 4 VPCs & Hệ Thống Subnets Đa AZ Tại Singapore

> **Mã bài lab:** `02.01`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** $0.00 USD (VPC và Subnets miễn phí)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — AZs: `ap-southeast-1a`, `ap-southeast-1b`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành toàn bộ các bài lab tại [Module 00](../00-chuan-bi-inventory/README.md) và [Module 01](../01-thiet-ke-threat-model/README.md).
- Tài khoản AWS đã được kiểm kê sạch sẽ, không có VPC trùng dải `10.40.0.0/16`, `10.50.0.0/16`, `10.70.0.0/16`, `10.80.0.0/16`.

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
        "ec2:CreateVpc",
        "ec2:CreateSubnet",
        "ec2:CreateTags",
        "ec2:ModifyVpcAttribute",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Việc tạo VPC và Subnet là hoàn toàn miễn phí. Chi phí chỉ phát sinh khi tạo NAT Gateway, TGW Attachment hoặc dữ liệu truyền qua mạng.
- **Cảnh báo Subnet Sizing:** Subnet TGW attachment bắt buộc phải là subnet chuyên dụng (dedicated subnet) có kích thước tối thiểu `/28` và không được chứa bất kỳ tài nguyên nào khác ngoài TGW ENI theo khuyến nghị của AWS Best Practices.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Khởi Tạo 4 VPCs
Truy cập **VPC Console** tại Region Singapore (`ap-southeast-1`):
1. **Edge EKS VPC:**
   - Name tag: `fabric-edge-vpc`
   - IPv4 CIDR block: `10.40.0.0/16`
   - Bật `Enable DNS hostnames` và `Enable DNS resolution`.
2. **Core EKS VPC:**
   - Name tag: `fabric-core-vpc`
   - IPv4 CIDR block: `10.50.0.0/16`
   - Bật `Enable DNS hostnames` và `Enable DNS resolution`.
3. **Inspection VPC:**
   - Name tag: `fabric-inspection-vpc`
   - IPv4 CIDR block: `10.70.0.0/16`
   - Bật `Enable DNS hostnames` và `Enable DNS resolution`.
4. **Centralized Egress VPC:**
   - Name tag: `fabric-egress-vpc`
   - IPv4 CIDR block: `10.80.0.0/16`
   - Bật `Enable DNS hostnames` và `Enable DNS resolution`.

### Bước 2: Tạo Hệ Thống Subnets Đa AZ
Tạo các subnets tương ứng trong 2 AZ: `ap-southeast-1a` và `ap-southeast-1b`:
- **Edge VPC:**
  - `fabric-edge-public-1a` (`10.40.0.0/24`), `fabric-edge-public-1b` (`10.40.1.0/24`)
  - `fabric-edge-nodes-1a` (`10.40.10.0/22`), `fabric-edge-nodes-1b` (`10.40.14.0/22`)
  - `fabric-edge-vpce-1a` (`10.40.20.0/24`), `fabric-edge-vpce-1b` (`10.40.21.0/24`)
  - `fabric-edge-tgw-1a` (`10.40.250.0/28`), `fabric-edge-tgw-1b` (`10.40.250.16/28`)
- **Core VPC:**
  - `fabric-core-nodes-1a` (`10.50.10.0/22`), `fabric-core-nodes-1b` (`10.50.14.0/22`)
  - `fabric-core-data-1a` (`10.50.20.0/24`), `fabric-core-data-1b` (`10.50.21.0/24`)
  - `fabric-core-vpce-1a` (`10.50.30.0/24`), `fabric-core-vpce-1b` (`10.50.31.0/24`)
  - `fabric-core-tgw-1a` (`10.50.250.0/28`), `fabric-core-tgw-1b` (`10.50.250.16/28`)
- **Inspection VPC:**
  - `fabric-insp-tgw-1a` (`10.70.0.0/28`), `fabric-insp-tgw-1b` (`10.70.0.16/28`)
  - `fabric-insp-gwlbe-1a` (`10.70.1.0/28`), `fabric-insp-gwlbe-1b` (`10.70.1.16/28`)
  - `fabric-insp-fw-1a` (`10.70.10.0/24`), `fabric-insp-fw-1b` (`10.70.11.0/24`)
- **Centralized Egress VPC:**
  - `fabric-egress-tgw-1a` (`10.80.0.0/28`), `fabric-egress-tgw-1b` (`10.80.0.16/28`)
  - `fabric-egress-fw-1a` (`10.80.1.0/28`), `fabric-egress-fw-1b` (`10.80.1.16/28`)
  - `fabric-egress-public-1a` (`10.80.10.0/24`), `fabric-egress-public-1b` (`10.80.11.0/24`)

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy các lệnh xác minh trạng thái VPCs và Subnets qua AWS CLI hoặc MCP Server (`aws-api-mcp/call_aws`):
```bash
# 1. Liệt kê 4 VPCs vừa tạo kèm trạng thái
aws ec2 describe-vpcs --region ap-southeast-1 \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query 'Vpcs[*].{VpcId:VpcId,Cidr:CidrBlock,Name:Tags[?Key==`Name`].Value | [0],State:State}' \
  --output table

# 2. Đếm tổng số Subnet đã khởi tạo (kỳ vọng: 26 subnets)
aws ec2 describe-subnets --region ap-southeast-1 \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query 'length(Subnets)' --output text
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Trong trường hợp cần xóa toàn bộ VPC để tái tạo từ đầu:
1. Xóa toàn bộ Subnet thuộc từng VPC.
2. Xóa 4 VPC: `fabric-edge-vpc`, `fabric-core-vpc`, `fabric-inspection-vpc`, `fabric-egress-vpc`.
3. Hoặc thực thi qua CLI:
   ```bash
   for vpc_id in $(aws ec2 describe-vpcs --region ap-southeast-1 --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" --query 'Vpcs[*].VpcId' --output text); do
     aws ec2 delete-vpc --region ap-southeast-1 --vpc-id $vpc_id
   done
   ```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/02-network/01-vpcs-and-subnets.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Cả 4 VPCs đều ở trạng thái `available` tại Singapore `ap-southeast-1`.
- [ ] Tính năng DNS resolution và DNS hostnames được bật (`true`) trên cả 4 VPCs.
- [ ] Toàn bộ 26 subnets được gán đúng dải IP và AZ tương ứng.
""", encoding="utf-8")

# 02-transit-gateway-setup.md
(BASE / "02-transit-gateway-setup.md").write_text("""# 02.02 — Cấu Hình AWS Transit Gateway (TGW) Tắt Mặc Định Propagation

> **Mã bài lab:** `02.02`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 20 phút  
> **Chi phí ước tính:** ~$0.07 USD/giờ cho Transit Gateway tại Singapore  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành [02.01 — Khởi Tạo 4 VPCs & Hệ Thống Subnets](01-four-vpcs-and-subnets.md).
- Hiểu rõ cơ chế phân tách miền định tuyến (Route Domain Segmentation).

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
        "ec2:CreateTransitGateway",
        "ec2:DescribeTransitGateways",
        "ec2:CreateTags",
        "ec2:ModifyTransitGateway"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** AWS Transit Gateway tính phí khoảng $0.07 USD/giờ (khoảng $1.68 USD/ngày). Cần theo dõi trong ngân sách $50.00 USD.
- **Cảnh báo kiến trúc an ninh:** **BẮT BUỘC TẮT** `Default route table association` và `Default route table propagation`. Nếu bật mặc định, mọi VPC kết nối vào TGW sẽ tự động nhìn thấy nhau, phá vỡ hoàn toàn nguyên tắc phân đoạn an ninh và kiểm tra qua tường lửa.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Mở Bảng Điều Khiển Transit Gateway
1. Truy cập **VPC Console** tại `ap-southeast-1`.
2. Tại menu điều hướng bên trái, cuộn xuống nhóm **Transit Gateways** -> Nhấp chọn **Transit Gateways**.
3. Nhấp nút cam **Create transit gateway**.

### Bước 2: Thiết Lập Tham Số Cốt Lõi TGW
1. **Name tag:** Nhập `fabric-tgw`.
2. **Description:** Nhập `Transit Gateway trung tâm cho AWS EKS Secure Network Fabric`.
3. **Amazon side Autonomous System Number (ASN):** Nhập `64512` (Private ASN chuẩn cho Fabric).
4. **Cấu hình tùy chọn nâng cao (Cực kỳ quan trọng):**
   - **DNS support:** Chọn `enable`.
   - **VPN ECMP support:** Chọn `enable`.
   - **Default route table association:** Bỏ chọn (`disable`).
   - **Default route table propagation:** Bỏ chọn (`disable`).
   - **Auto accept shared attachments:** Chọn `disable`.
   - **Multicast support:** Bỏ chọn (`disable`).
5. **Tags:**
   - `Project`: `aws-eks-secure-network-fabric`
   - `Environment`: `prod`
6. Nhấp **Create transit gateway**.
7. Đợi trạng thái chuyển từ `pending` sang `available` (mất khoảng 2-4 phút).

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy các lệnh xác minh trạng thái TGW qua AWS CLI hoặc MCP Server (`aws-api-mcp/call_aws`):
```bash
aws ec2 describe-transit-gateways --region ap-southeast-1 \
  --filters "Name=tag:Name,Values=fabric-tgw" \
  --query 'TransitGateways[*].{Id:TransitGatewayId,State:State,ASN:Options.AmazonSideAsn,DefaultAssoc:Options.DefaultRouteTableAssociation,DefaultProp:Options.DefaultRouteTablePropagation}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Nếu cần xóa TGW:
```bash
tgw_id=$(aws ec2 describe-transit-gateways --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-tgw" --query 'TransitGateways[0].TransitGatewayId' --output text)
if [ "$tgw_id" != "None" ] && [ -n "$tgw_id" ]; then
  aws ec2 delete-transit-gateway --region ap-southeast-1 --transit-gateway-id $tgw_id
fi
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/02-network/02-tgw-status.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Transit Gateway `fabric-tgw` đạt trạng thái `available`.
- [ ] `AmazonSideAsn` hiển thị đúng giá trị `64512`.
- [ ] `DefaultRouteTableAssociation` là `disable`.
- [ ] `DefaultRouteTablePropagation` là `disable`.
""", encoding="utf-8")

# 03-tgw-route-tables-and-attachments.md
(BASE / "03-tgw-route-tables-and-attachments.md").write_text("""# 02.03 — Tạo TGW Attachments, Route Tables & Thiết Lập Appliance Mode

> **Mã bài lab:** `02.03`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** ~$0.07/giờ/attachment (~$0.28 USD/giờ cho 4 attachments)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành [02.01](01-four-vpcs-and-subnets.md) và [02.02](02-transit-gateway-setup.md).
- TGW `fabric-tgw` đang ở trạng thái `available`.

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
        "ec2:CreateTransitGatewayRouteTable",
        "ec2:AssociateTransitGatewayRouteTable",
        "ec2:EnableTransitGatewayRouteTablePropagation",
        "ec2:CreateTransitGatewayRoute",
        "ec2:ModifyTransitGatewayVpcAttachment",
        "ec2:DescribeTransitGateway*"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Mỗi TGW Attachment tính phí $0.07 USD/giờ. 4 Attachments sẽ tiêu tốn ~$6.72 USD/ngày.
- **Cảnh báo tính đối xứng (Appliance Mode):** Cực kỳ quan trọng: Khi gắn Attachment cho **Inspection VPC** và **Egress VPC**, bạn **BẮT BUỘC PHẢI BẬT** tùy chọn `ApplianceModeSupport = enable`. Nếu không bật, TGW sẽ băm luồng (flow hashing) không đối xứng, khiến gói tin phản hồi bị drop trên Suricata hoặc AWS Network Firewall.
- **Lưu ý chu trình DAG (Tránh vòng lặp):** Trong bài lab này, tuyến Edge<->Core ban đầu sẽ được định tuyến trực tiếp tạm thời (hoặc để chờ cutover) để kiểm tra mạng cơ bản. Tuyến đường này sẽ chính thức chuyển sang trỏ vào Inspection Attachment tại Module 05 sau khi GWLB và Suricata đã hoạt động hoàn hảo.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Tạo 4 TGW Attachments Cho 4 VPCs
Truy cập **VPC Console** -> **Transit Gateway Attachments** -> Nhấp **Create transit gateway attachment**:

1. **Edge Attachment:**
   - Name: `fabric-edge-tgw-attachment`
   - Transit Gateway ID: Chọn `fabric-tgw`
   - Attachment type: `VPC`
   - VPC ID: Chọn `fabric-edge-vpc`
   - Subnet IDs: Chọn 2 TGW Subnets (`fabric-edge-tgw-1a`, `fabric-edge-tgw-1b`)
2. **Core Attachment:**
   - Name: `fabric-core-tgw-attachment`
   - VPC ID: Chọn `fabric-core-vpc`
   - Subnet IDs: Chọn 2 TGW Subnets (`fabric-core-tgw-1a`, `fabric-core-tgw-1b`)
3. **Inspection Attachment (Bắt buộc Appliance Mode):**
   - Name: `fabric-insp-tgw-attachment`
   - VPC ID: Chọn `fabric-inspection-vpc`
   - Subnet IDs: Chọn 2 TGW Subnets (`fabric-insp-tgw-1a`, `fabric-insp-tgw-1b`)
   - **Appliance Mode:** Chọn **Enable**
4. **Egress Attachment (Bắt buộc Appliance Mode):**
   - Name: `fabric-egress-tgw-attachment`
   - VPC ID: Chọn `fabric-egress-vpc`
   - Subnet IDs: Chọn 2 TGW Subnets (`fabric-egress-tgw-1a`, `fabric-egress-tgw-1b`)
   - **Appliance Mode:** Chọn **Enable**

### Bước 2: Tạo 4 TGW Route Tables Riêng Biệt (Route Domains)
Truy cập **Transit Gateway Route Tables** -> Tạo 4 bảng:
1. `fabric-tgw-edge-rt`
2. `fabric-tgw-core-rt`
3. `fabric-tgw-inspection-rt`
4. `fabric-tgw-egress-rt`

### Bước 3: Thiết Lập Associations & Static Routes
1. **Liên kết (Associations):**
   - Gán `fabric-edge-tgw-attachment` vào bảng `fabric-tgw-edge-rt`.
   - Gán `fabric-core-tgw-attachment` vào bảng `fabric-tgw-core-rt`.
   - Gán `fabric-insp-tgw-attachment` vào bảng `fabric-tgw-inspection-rt`.
   - Gán `fabric-egress-tgw-attachment` vào bảng `fabric-tgw-egress-rt`.

2. **Cấu hình Static Routes Ban Đầu (Initial Routing):**
   - Tại `fabric-tgw-edge-rt`:
     - `0.0.0.0/0` -> trỏ tới `fabric-egress-tgw-attachment`
     - `10.50.0.0/16` -> trỏ tạm tới `fabric-core-tgw-attachment` (sẽ cutover sang Inspection tại Module 05)
   - Tại `fabric-tgw-core-rt`:
     - `0.0.0.0/0` -> trỏ tới `fabric-egress-tgw-attachment`
     - `10.40.0.0/16` -> trỏ tạm tới `fabric-edge-tgw-attachment` (sẽ cutover sang Inspection tại Module 05)
   - Tại `fabric-tgw-inspection-rt`:
     - `10.40.0.0/16` -> trỏ tới `fabric-edge-tgw-attachment`
     - `10.50.0.0/16` -> trỏ tới `fabric-core-tgw-attachment`
   - Tại `fabric-tgw-egress-rt`:
     - `10.40.0.0/16` -> trỏ tới `fabric-edge-tgw-attachment`
     - `10.50.0.0/16` -> trỏ tới `fabric-core-tgw-attachment`

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy các lệnh xác minh trạng thái Attachment và cờ Appliance Mode:
```bash
# 1. Kiểm tra 4 attachments và cờ Appliance Mode
aws ec2 describe-transit-gateway-vpc-attachments --region ap-southeast-1 \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query 'TransitGatewayVpcAttachments[*].{Name:Tags[?Key==`Name`].Value | [0],Id:TransitGatewayAttachmentId,State:State,ApplianceMode:Options.ApplianceModeSupport}' \
  --output table

# 2. Kiểm tra associations của từng TGW Route Table
aws ec2 describe-transit-gateway-route-tables --region ap-southeast-1 \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query 'TransitGatewayRouteTables[*].{Name:Tags[?Key==`Name`].Value | [0],Id:TransitGatewayRouteTableId,State:State}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Trong trường hợp cần hoàn tác các attachments:
```bash
for att_id in $(aws ec2 describe-transit-gateway-attachments --region ap-southeast-1 --query 'TransitGatewayAttachments[*].TransitGatewayAttachmentId' --output text); do
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
- [ ] Cờ `ApplianceModeSupport` của `fabric-insp-tgw-attachment` hiển thị `enable`.
- [ ] Cờ `ApplianceModeSupport` của `fabric-egress-tgw-attachment` hiển thị `enable`.
- [ ] 4 bảng định tuyến TGW Route Tables được phân tách và liên kết chính xác với từng attachment.
""", encoding="utf-8")

# 04-subnet-route-tables-chaining.md
(BASE / "04-subnet-route-tables-chaining.md").write_text("""# 02.04 — Cấu Hình Bảng Định Tuyến Subnet (Subnet Route Tables)

> **Mã bài lab:** `02.04`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 40 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab [02.01](01-four-vpcs-and-subnets.md), [02.02](02-transit-gateway-setup.md), [02.03](03-tgw-route-tables-and-attachments.md).

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
        "ec2:DescribeRouteTables"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD (Bảng định tuyến VPC Route Tables miễn phí).
- **Cảnh báo cô lập:** Tuyệt đối không gắn Internet Gateway vào Core VPC hoặc Inspection VPC. Mọi kết nối ra ngoài phải được điều hướng thông qua TGW.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Tạo Bảng Định Tuyến Cho Edge VPC
1. **`fabric-edge-public-rt`**:
   - Gắn với `fabric-edge-public-1a` và `fabric-edge-public-1b`.
   - Route `0.0.0.0/0` -> Internet Gateway (`fabric-edge-igw`).
   - Route `10.50.0.0/16` -> Transit Gateway (`fabric-tgw`).
2. **`fabric-edge-private-rt`**:
   - Gắn với Node Subnets và VPCE Subnets của Edge VPC.
   - Route `0.0.0.0/0` -> Transit Gateway (`fabric-tgw`).
   - Route `10.50.0.0/16` -> Transit Gateway (`fabric-tgw`).

### Bước 2: Tạo Bảng Định Tuyến Cho Core VPC
1. **`fabric-core-private-rt`**:
   - Gắn với Core Node Subnets, VPCE Subnets và Data Subnets.
   - Route `0.0.0.0/0` -> Transit Gateway (`fabric-tgw`).
   - Route `10.40.0.0/16` -> Transit Gateway (`fabric-tgw`).

### Bước 3: Tạo Bảng Định Tuyến Cho Inspection & Egress VPCs
1. **`fabric-insp-tgw-rt`**:
   - Gắn với `fabric-insp-tgw-1a` và `fabric-insp-tgw-1b`.
   - Các tuyến định tuyến chi tiết tới GWLB Endpoint sẽ được thiết lập trong Module 05.
2. **`fabric-egress-tgw-rt`**:
   - Gắn với `fabric-egress-tgw-1a` và `fabric-egress-tgw-1b`.
   - Tuyến `0.0.0.0/0` sẽ được trỏ tới Network Firewall Endpoints trong Module 06.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra danh sách route tables đã tạo và các associations tương ứng:
```bash
aws ec2 describe-route-tables --region ap-southeast-1 \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query 'RouteTables[*].{Name:Tags[?Key==`Name`].Value | [0],VpcId:VpcId,RoutesCount:length(Routes)}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Trong trường hợp định tuyến sai, xóa các route cụ thể hoặc gỡ association khỏi subnet:
```bash
# Xóa một route không mong muốn
aws ec2 delete-route --region ap-southeast-1 --route-table-id <rtb-id> --destination-cidr-block <cidr>
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/02-network/04-subnet-route-tables.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Toàn bộ các Subnet đều có bảng định tuyến rõ ràng (Explicit Association).
- [ ] Core VPC hoàn toàn không có đường trỏ trực tiếp ra IGW.
- [ ] Các tuyến liên VPC và Internet đều trỏ đến `fabric-tgw`.
""", encoding="utf-8")

# 05-vpc-flow-logs-cloudwatch.md
(BASE / "05-vpc-flow-logs-cloudwatch.md").write_text("""# 02.05 — Thiết Lập Centralized VPC Flow Logs Về CloudWatch Logs

> **Mã bài lab:** `02.05`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 30 phút  
> **Chi phí ước tính:** ~$0.50 USD / GB dữ liệu logs nạp vào CloudWatch  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab từ [02.01](01-four-vpcs-and-subnets.md) đến [02.04](04-subnet-route-tables-chaining.md).
- Quyền IAM tạo Log Group và IAM Role phục vụ Flow Logs.

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
        "iam:CreateRole",
        "iam:PutRolePolicy",
        "logs:CreateLogGroup",
        "logs:PutRetentionPolicy",
        "ec2:CreateFlowLogs",
        "ec2:DescribeFlowLogs"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** CloudWatch Logs tính phí $0.50/GB cho dữ liệu nạp vào (Ingestion) và $0.03/GB lưu trữ mỗi tháng. Bắt buộc đặt Retention 7 ngày để tối ưu chi phí.
- **Cảnh báo độ trễ:** VPC Flow Logs có độ trễ thu thập từ 1 đến 5 phút trước khi xuất hiện trên CloudWatch Logs.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Tạo IAM Role Cho VPC Flow Logs
1. Truy cập **IAM Console** -> **Roles** -> **Create role**.
2. **Trusted entity type:** Chọn `AWS service`, use case: chọn `EC2`.
3. Nhấp **Next** -> Đặt tên role: `fabric-vpc-flow-logs-role`.
4. Gán Policy tùy chỉnh cho phép ghi log vào CloudWatch:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "logs:CreateLogGroup",
           "logs:CreateLogStream",
           "logs:PutLogEvents",
           "logs:DescribeLogGroups",
           "logs:DescribeLogStreams"
         ],
         "Resource": "*"
       }
     ]
   }
   ```
5. Chỉnh sửa Trust Relationship của Role để cho phép service `vpc-flow-logs.amazonaws.com` assume role:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "Service": "vpc-flow-logs.amazonaws.com"
         },
         "Action": "sts:AssumeRole"
       }
     ]
   }
   ```

### Bước 2: Tạo CloudWatch Log Group Tập Trung
1. Truy cập **CloudWatch Console** -> **Log groups** -> **Create log group**.
2. Log group name: `/aws/vpc/fabric-centralized-flow-logs`.
3. Retention setting: Chọn `7 days` (tiết kiệm chi phí).

### Bước 3: Bật Flow Logs Trên Cả 4 VPCs
1. Truy cập **VPC Console** -> Chọn lần lượt 4 VPCs (`fabric-edge-vpc`, `fabric-core-vpc`, `fabric-inspection-vpc`, `fabric-egress-vpc`).
2. Nhấp tab **Flow logs** -> Nhấp **Create flow log**:
   - Filter: `ALL` (Bao gồm ACCEPT và REJECT).
   - Maximum aggregation interval: `1 minute` (độ phân giải cao cho GameDay).
   - Destination: `Send to CloudWatch Logs`.
   - Destination log group: `/aws/vpc/fabric-centralized-flow-logs`.
   - IAM role: `fabric-vpc-flow-logs-role`.
   - Log record format: `AWS default format` (kèm TCP flags, flow-direction).

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra danh sách Flow Logs đang hoạt động:
```bash
aws ec2 describe-flow-logs --region ap-southeast-1 \
  --query 'FlowLogs[*].{FlowLogId:FlowLogId,ResourceId:ResourceId,LogGroupName:LogGroupName,TrafficType:TrafficType,State:FlowLogStatus}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Để tắt và xóa Flow Logs:
```bash
for fl_id in $(aws ec2 describe-flow-logs --region ap-southeast-1 --query 'FlowLogs[*].FlowLogId' --output text); do
  aws ec2 delete-flow-logs --region ap-southeast-1 --flow-log-ids $fl_id
done
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/02-network/05-flow-logs-active.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Cả 4 VPCs đều có Flow Log ở trạng thái `ACTIVE`.
- [ ] Dữ liệu logs được đẩy về Log Group `/aws/vpc/fabric-centralized-flow-logs`.
- [ ] Thời gian lưu trữ (Retention) được đặt chính xác `7 days`.
""", encoding="utf-8")

# 06-private-vpc-endpoints.md
(BASE / "06-private-vpc-endpoints.md").write_text("""# 02.06 — Cấu Hình Private VPC Endpoints Cho Cụm EKS Riêng Tư (Edge & Core)

> **Mã bài lab:** `02.06`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 35 phút  
> **Chi phí ước tính:** ~$0.01/giờ/endpoint (~$0.14 USD/giờ cho các endpoints thiết yếu)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab [02.01](01-four-vpcs-and-subnets.md) đến [02.05](05-vpc-flow-logs-cloudwatch.md).
- Cần thiết để các cụm Private EKS (Edge và Core) tại Module 03 khởi động worker nodes, join cluster và kéo container images mà không bị treo do thiếu kết nối AWS API.

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
        "ec2:CreateVpcEndpoint",
        "ec2:DescribeVpcEndpoints",
        "ec2:ModifyVpcEndpoint",
        "ec2:CreateSecurityGroup",
        "ec2:AuthorizeSecurityGroupIngress"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Mỗi Interface VPC Endpoint tính phí ~$0.01 USD/giờ tại Singapore. S3 Gateway Endpoint hoàn toàn miễn phí.
- **Cảnh báo EKS Private Cluster Bootstrapping:** Nếu thiếu `ecr.api`, `ecr.dkr`, `s3` hoặc `sts`, EKS Managed Node Groups sẽ không thể cài đặt `aws-node`, `kube-proxy`, `coredns`, dẫn đến node ở trạng thái `NotReady` vĩnh viễn!

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Tạo Security Group Cho VPC Endpoints
1. Tại **Edge VPC** (`fabric-edge-vpc`): Tạo SG `fabric-edge-vpce-sg`, mở Inbound port `443` từ CIDR `10.40.0.0/16`.
2. Tại **Core VPC** (`fabric-core-vpc`): Tạo SG `fabric-core-vpce-sg`, mở Inbound port `443` từ CIDR `10.50.0.0/16`.

### Bước 2: Tạo Gateway Endpoint Cho Amazon S3 (Miễn Phí)
1. Truy cập **VPC Console** -> **Endpoints** -> **Create endpoint**:
   - Name: `fabric-edge-s3-endpoint` (trong Edge VPC) / `fabric-core-s3-endpoint` (trong Core VPC).
   - Service category: `AWS services`.
   - Services: Tìm `com.amazonaws.ap-southeast-1.s3` (Type: `Gateway`).
   - VPC: Chọn VPC tương ứng.
   - Route tables: Tích chọn bảng định tuyến private của VPC để tự động chèn route tới S3 Prefix List.
   - Policy: `Full access`.

### Bước 3: Tạo Interface Endpoints Thiết Yếu
Tạo các Interface Endpoints (Service category: `AWS services`, Type: `Interface`):
- `com.amazonaws.ap-southeast-1.ecr.api` (ECR API)
- `com.amazonaws.ap-southeast-1.ecr.dkr` (ECR Docker Registry - kéo images)
- `com.amazonaws.ap-southeast-1.sts` (Security Token Service cho Pod Identity)
- `com.amazonaws.ap-southeast-1.logs` (CloudWatch Logs)
- `com.amazonaws.ap-southeast-1.ec2` (EC2 API cho EBS CSI và Node management)

Khi tạo mỗi endpoint:
- Chọn Subnets: Đặt tại 2 Subnet VPCE theo 2 AZ (`fabric-edge-vpce-1a`, `fabric-edge-vpce-1b` hoặc `fabric-core-vpce-1a`, `fabric-core-vpce-1b`).
- Security Group: Gán SG đã tạo ở Bước 1.
- Enable Private DNS: Chọn **Enable** (`true`).

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái các VPC Endpoints đã tạo:
```bash
aws ec2 describe-vpc-endpoints --region ap-southeast-1 \
  --filters "Name=vpc-id,Values=$(aws ec2 describe-vpcs --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-core-vpc" --query 'Vpcs[0].VpcId' --output text)" \
  --query 'VpcEndpoints[*].{ServiceName:ServiceName,Type:VpcEndpointType,State:State,PrivateDns:PrivateDnsEnabled}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Để xóa VPC Endpoints khi dọn dẹp môi trường:
```bash
for ep_id in $(aws ec2 describe-vpc-endpoints --region ap-southeast-1 --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" --query 'VpcEndpoints[*].VpcEndpointId' --output text); do
  aws ec2 delete-vpc-endpoints --region ap-southeast-1 --vpc-endpoint-ids $ep_id
done
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/02-network/06-vpc-endpoints.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] S3 Gateway Endpoint được liên kết với bảng định tuyến của Edge và Core VPCs.
- [ ] Các Interface Endpoints (`ecr.api`, `ecr.dkr`, `sts`, `logs`, `ec2`) đạt trạng thái `available`.
- [ ] Tính năng Private DNS Name được kích hoạt thành công trên các Interface Endpoints.
""", encoding="utf-8")

# Update README.md for Module 02
(BASE / "README.md").write_text("""# Module 02: Hạ Tầng Mạng Cơ Bản (Foundation Network & Transit Gateway)

Module này hướng dẫn khởi tạo nền tảng hạ tầng mạng đa VPC trên AWS Region Singapore (`ap-southeast-1`), kết nối thông qua AWS Transit Gateway theo mô hình phân tách miền định tuyến (Route Domain Segmentation).

## Danh Sách Bài Lab

| Mã Lab | Tên Bài Lab & Nội Dung Trọng Tâm | Trạng Thái | File Hướng Dẫn |
|---|---|:---:|---|
| **02.01** | **Khởi Tạo 4 VPCs & Subnets Đa AZ:** 4 VPCs độc lập, 26 subnets chuẩn hóa theo AZ A/B. | `DRAFT` | [01-four-vpcs-and-subnets.md](01-four-vpcs-and-subnets.md) |
| **02.02** | **Cấu Hình AWS Transit Gateway (TGW):** ASN 64512, tắt mặc định Route Propagation. | `DRAFT` | [02-transit-gateway-setup.md](02-transit-gateway-setup.md) |
| **02.03** | **TGW Attachments & Appliance Mode:** 4 attachments, bật Appliance Mode trên Inspection & Egress. | `DRAFT` | [03-tgw-route-tables-and-attachments.md](03-tgw-route-tables-and-attachments.md) |
| **02.04** | **Bảng Định Tuyến Subnet:** Chaining các tuyến đường từ VPC private qua TGW. | `DRAFT` | [04-subnet-route-tables-chaining.md](04-subnet-route-tables-chaining.md) |
| **02.05** | **Centralized VPC Flow Logs:** Tập trung hóa nhật ký gói tin về CloudWatch Logs 7 ngày. | `DRAFT` | [05-vpc-flow-logs-cloudwatch.md](05-vpc-flow-logs-cloudwatch.md) |
| **02.06** | **Private VPC Endpoints:** S3 Gateway, ECR, STS, Logs, EC2 endpoints cho Private EKS. | `DRAFT` | [06-private-vpc-endpoints.md](06-private-vpc-endpoints.md) |
""", encoding="utf-8")

print("Module 02 rewritten successfully.")
