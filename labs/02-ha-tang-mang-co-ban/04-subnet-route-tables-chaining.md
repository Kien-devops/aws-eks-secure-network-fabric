# 02.04 — Cấu Hình Bảng Định Tuyến Subnet (Subnet Route Tables Chaining)

> **Mã bài lab:** `02.04`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** $0.00 USD (Bảng định tuyến VPC Route Tables hoàn toàn miễn phí)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — AZs: `ap-southeast-1a`, `ap-southeast-1b`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành toàn bộ các bài lab [02.01](01-four-vpcs-and-subnets.md), [02.02](02-transit-gateway-setup.md), và [02.03](03-tgw-route-tables-and-attachments.md).
- 4 VPCs, 26 subnets, Transit Gateway và 4 TGW Attachments đã ở trạng thái `available`.
- Đăng nhập AWS Management Console tại Region Singapore `ap-southeast-1`.

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
        "ec2:DeleteRoute",
        "ec2:DescribeRouteTables",
        "ec2:CreateTags"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD (Bảng định tuyến VPC Route Tables miễn phí).
- **Cảnh báo cô lập vùng nhạy cảm:** Tuyệt đối không gắn Internet Gateway vào `fabric-core-vpc` hoặc `fabric-inspection-vpc`. Tuyệt đối không thêm route `0.0.0.0/0` vào Route Table của Data Subnet (`fabric-core-data-rt`) để tránh mọi nguy cơ rò rỉ cơ sở dữ liệu.
- **Quy tắc TGW Subnet Route Table:** Theo khuyến nghị AWS Well-Architected, subnet dành cho TGW Attachment chỉ nên chứa duy nhất tuyến nội bộ (Local route) để tránh tình trạng định tuyến vòng lặp (routing loops).

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Tạo & Cấu Hình Bảng Định Tuyến Cho Edge VPC (`fabric-edge-vpc`)
Mở **VPC Console** -> Menu bên trái chọn **Route tables** -> Nhấp nút cam **Create route table**.

#### 1. Tạo `fabric-edge-public-rt` (Dành cho ALB Ingress Subnets):
1. **Name:** Nhập `fabric-edge-public-rt`.
2. **VPC:** Chọn `fabric-edge-vpc`.
3. Nhấp **Create route table**.
4. Chuyển sang tab **Subnet associations** -> Nhấp nút **Edit subnet associations**:
   - Tích chọn 2 subnets: `fabric-edge-public-1a` và `fabric-edge-public-1b`.
   - Nhấp **Save associations**.
5. Chuyển sang tab **Routes** -> Nhấp nút **Edit routes**:
   - Tuyến 1: `10.40.0.0/16` -> Target: `local` (mặc định có sẵn).
   - Nhấp **Add route**:
     - Destination: `0.0.0.0/0` -> Target: Chọn **Internet Gateway** -> Chọn `fabric-edge-igw`.
   - Nhấp **Add route**:
     - Destination: `10.50.0.0/16` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
   - Nhấp **Save changes**.

#### 2. Tạo `fabric-edge-private-rt` (Dành cho EKS Worker Nodes & VPCE):
1. Nhấp **Create route table**.
2. **Name:** Nhập `fabric-edge-private-rt` | **VPC:** Chọn `fabric-edge-vpc`.
3. Nhấp **Create route table**.
4. Tab **Subnet associations** -> **Edit subnet associations**:
   - Tích chọn 4 subnets: `fabric-edge-nodes-1a`, `fabric-edge-nodes-1b`, `fabric-edge-vpce-1a`, `fabric-edge-vpce-1b`.
   - Nhấp **Save associations**.
5. Tab **Routes** -> **Edit routes**:
   - Nhấp **Add route**: Destination: `0.0.0.0/0` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
   - Nhấp **Add route**: Destination: `10.50.0.0/16` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
   - Nhấp **Save changes**.

#### 3. Tạo `fabric-edge-tgw-rt` (Dành riêng cho TGW Attachment ENIs):
1. Nhấp **Create route table**.
2. **Name:** Nhập `fabric-edge-tgw-rt` | **VPC:** Chọn `fabric-edge-vpc`.
3. Nhấp **Create route table**.
4. Tab **Subnet associations** -> **Edit subnet associations**:
   - Tích chọn: `fabric-edge-tgw-1a` và `fabric-edge-tgw-1b`.
   - Nhấp **Save associations**.
5. Tab **Routes**: Giữ nguyên duy nhất tuyến `10.40.0.0/16` -> `local`.

---

### Bước 2: Tạo & Cấu Hình Bảng Định Tuyến Cho Core VPC (`fabric-core-vpc`)
Tại màn hình **Route tables** -> Nhấp nút cam **Create route table**.

#### 1. Tạo `fabric-core-private-rt` (Dành cho Core EKS Nodes & VPCE):
1. **Name:** Nhập `fabric-core-private-rt`.
2. **VPC:** Chọn `fabric-core-vpc`.
3. Nhấp **Create route table**.
4. Tab **Subnet associations** -> **Edit subnet associations**:
   - Tích chọn 4 subnets: `fabric-core-nodes-1a`, `fabric-core-nodes-1b`, `fabric-core-vpce-1a`, `fabric-core-vpce-1b`.
   - Nhấp **Save associations**.
5. Tab **Routes** -> **Edit routes**:
   - Nhấp **Add route**: Destination: `0.0.0.0/0` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
   - Nhấp **Add route**: Destination: `10.40.0.0/16` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
   - Nhấp **Save changes**.

#### 2. Tạo `fabric-core-data-rt` (Dành cho Aurora PostgreSQL & ElastiCache Redis):
1. Nhấp **Create route table**.
2. **Name:** Nhập `fabric-core-data-rt` | **VPC:** Chọn `fabric-core-vpc`.
3. Nhấp **Create route table**.
4. Tab **Subnet associations** -> **Edit subnet associations**:
   - Tích chọn 2 subnets: `fabric-core-data-1a` và `fabric-core-data-1b`.
   - Nhấp **Save associations**.
5. Tab **Routes**: Giữ nguyên chỉ có tuyến `10.50.0.0/16` -> `local` (Không trỏ ra TGW, không trỏ ra Internet để bảo vệ dữ liệu tối đa).

#### 3. Tạo `fabric-core-tgw-rt` (Dành cho TGW Attachment ENIs):
1. Nhấp **Create route table**.
2. **Name:** Nhập `fabric-core-tgw-rt` | **VPC:** Chọn `fabric-core-vpc`.
3. Nhấp **Create route table**.
4. Tab **Subnet associations** -> **Edit subnet associations**:
   - Tích chọn: `fabric-core-tgw-1a` và `fabric-core-tgw-1b`.
   - Nhấp **Save associations**.
5. Tab **Routes**: Giữ nguyên chỉ có tuyến `10.50.0.0/16` -> `local`.

---

### Bước 3: Tạo Bảng Định Tuyến Nền Tảng Cho Inspection VPC (`fabric-inspection-vpc`)
1. **Tạo `fabric-insp-tgw-rt`:**
   - **Name:** Nhập `fabric-insp-tgw-rt` | **VPC:** Chọn `fabric-inspection-vpc`.
   - Nhấp **Create route table**.
   - Tab **Subnet associations**: Gắn với `fabric-insp-tgw-1a` và `fabric-insp-tgw-1b`.
   - *(Lưu ý: Các tuyến định tuyến chi tiết trỏ tới GWLB Endpoints sẽ được cấu hình trong Module 05 sau khi GWLB được triển khai)*.
2. **Tạo `fabric-insp-gwlbe-rt`:**
   - **Name:** Nhập `fabric-insp-gwlbe-rt` | **VPC:** Chọn `fabric-inspection-vpc`.
   - Nhấp **Create route table**.
   - Tab **Subnet associations**: Gắn với `fabric-insp-gwlbe-1a` và `fabric-insp-gwlbe-1b`.
3. **Tạo `fabric-insp-fw-rt`:**
   - **Name:** Nhập `fabric-insp-fw-rt` | **VPC:** Chọn `fabric-inspection-vpc`.
   - Nhấp **Create route table**.
   - Tab **Subnet associations**: Gắn với `fabric-insp-fw-1a` và `fabric-insp-fw-1b` (Subnet chứa máy chủ Suricata EC2).

---

### Bước 4: Tạo Bảng Định Tuyến Nền Tảng Cho Centralized Egress VPC (`fabric-egress-vpc`)
1. **Tạo `fabric-egress-tgw-rt`:**
   - **Name:** Nhập `fabric-egress-tgw-rt` | **VPC:** Chọn `fabric-egress-vpc`.
   - Nhấp **Create route table**.
   - Tab **Subnet associations**: Gắn với `fabric-egress-tgw-1a` và `fabric-egress-tgw-1b`.
2. **Tạo `fabric-egress-fw-rt`:**
   - **Name:** Nhập `fabric-egress-fw-rt` | **VPC:** Chọn `fabric-egress-vpc`.
   - Nhấp **Create route table**.
   - Tab **Subnet associations**: Gắn với `fabric-egress-fw-1a` và `fabric-egress-fw-1b`.
3. **Tạo `fabric-egress-public-rt`:**
   - **Name:** Nhập `fabric-egress-public-rt` | **VPC:** Chọn `fabric-egress-vpc`.
   - Nhấp **Create route table**.
   - Tab **Subnet associations**: Gắn với `fabric-egress-public-1a` và `fabric-egress-public-1b`.
   - Tab **Routes** -> **Edit routes**:
     - Nhấp **Add route**: Destination: `0.0.0.0/0` -> Target: Chọn **Internet Gateway** -> Chọn `fabric-egress-igw`.
     - Nhấp **Save changes**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy các lệnh xác minh trạng thái Route Tables và các Subnet Associations tương ứng:
```bash
# 1. Liệt kê toàn bộ Route Tables đã tạo kèm VPC ID và số lượng Subnet liên kết
aws ec2 describe-route-tables --region ap-southeast-1 \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query 'RouteTables[*].{Name:Tags[?Key==`Name`].Value | [0],Id:RouteTableId,VpcId:VpcId,AssocCount:length(Associations)}' \
  --output table

# 2. Kiểm tra chi tiết tuyến đường trong fabric-edge-private-rt
aws ec2 describe-route-tables --region ap-southeast-1 \
  --filters "Name=tag:Name,Values=fabric-edge-private-rt" \
  --query 'RouteTables[0].Routes[*].{Destination:DestinationCidrBlock,Target:TransitGatewayId || GatewayId || InstanceId,State:State}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Trong trường hợp định tuyến sai, xóa các route cụ thể hoặc gỡ association khỏi subnet:
```bash
# Xóa một route không mong muốn
aws ec2 delete-route --region ap-southeast-1 --route-table-id <rtb-id> --destination-cidr-block <cidr>

# Gỡ bỏ association khỏi subnet nếu gán nhầm
aws ec2 disassociate-route-table --region ap-southeast-1 --association-id <rtb-assoc-id>
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/02-network/04-subnet-route-tables.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Toàn bộ 26 subnets được gán đúng Route Table tương ứng (không để subnet nào rơi vào Main Route Table mặc định).
- [ ] Subnet Node của Edge EKS và Core EKS đều trỏ `0.0.0.0/0` về `fabric-tgw`.
- [ ] Subnet Data của Core VPC không có tuyến ra Internet `0.0.0.0/0`.
- [ ] Subnet TGW Attachment trong cả 4 VPCs chỉ có duy nhất tuyến `local`.
- [ ] Public Subnet của Edge VPC trỏ `0.0.0.0/0` về `fabric-edge-igw` và `10.50.0.0/16` về `fabric-tgw`.
