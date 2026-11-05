# 02.01 — Khởi Tạo 4 VPCs & Hệ Thống Subnets Đa AZ Tại Singapore

> **Mã bài lab:** `02.01`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** $0.00 USD (Khởi tạo VPC, Subnet và Internet Gateway hoàn toàn miễn phí)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — AZs: `ap-southeast-1a`, `ap-southeast-1b`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành toàn bộ các bài lab tại [Module 00](../00-chuan-bi-inventory/README.md) và [Module 01](../01-thiet-ke-threat-model/README.md).
- Tài khoản AWS đã được kiểm kê sạch sẽ, không có VPC nào trùng dải `10.40.0.0/16`, `10.50.0.0/16`, `10.70.0.0/16`, `10.80.0.0/16`.
- Đăng nhập AWS Management Console tại vùng **Asia Pacific (Singapore) `ap-southeast-1`**.

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
        "ec2:CreateInternetGateway",
        "ec2:AttachInternetGateway",
        "ec2:CreateTags",
        "ec2:ModifyVpcAttribute",
        "ec2:ModifySubnetAttribute",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeInternetGateways"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Việc tạo VPC, Subnet và Internet Gateway là hoàn toàn miễn phí ($0.00 USD). Chi phí chỉ bắt đầu phát sinh khi tạo NAT Gateway, TGW Attachment hoặc truyền dữ liệu qua mạng.
- **Cảnh báo cô lập Internet Gateway:** Tuyệt đối **KHÔNG ĐƯỢC TẠO VÀ GẮN** Internet Gateway vào `fabric-core-vpc` hoặc `fabric-inspection-vpc`. Hai VPC này là vùng biệt lập 100% (Isolated private networks), mọi lưu lượng ra ngoài bắt buộc phải đi qua Transit Gateway.
- **Cảnh báo Subnet Sizing TGW:** Subnet TGW attachment bắt buộc phải là subnet chuyên dụng có kích thước tối thiểu `/28` và không được chứa bất kỳ tài nguyên nào khác ngoài TGW ENI theo khuyến nghị của AWS Best Practices.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Khởi Tạo 4 Virtual Private Clouds (VPCs)
Truy cập **VPC Console** tại Singapore (`ap-southeast-1`):
1. Tại menu điều hướng bên trái, chọn **Your VPCs** -> Nhấp nút cam **Create VPC** ở góc trên bên phải.
2. Thực hiện tuần tự tạo 4 VPCs với tùy chọn **VPC only**:

   - **VPC 1 — Edge EKS VPC:**
     - Resources to create: Chọn **VPC only**.
     - Name tag: Nhập `fabric-edge-vpc`.
     - IPv4 CIDR allocation: Chọn **IPv4 CIDR manual input**.
     - IPv4 CIDR: Nhập `10.40.0.0/16`.
     - IPv6 CIDR block: Chọn **No IPv6 CIDR block**.
     - Tenancy: Chọn **Default**.
     - Tags: Key: `Project` - Value: `aws-eks-secure-network-fabric`; Key: `Environment` - Value: `prod`.
     - Nhấp **Create VPC**.

   - **VPC 2 — Core EKS VPC:**
     - Resources to create: Chọn **VPC only**.
     - Name tag: Nhập `fabric-core-vpc`.
     - IPv4 CIDR: Nhập `10.50.0.0/16`.
     - Tenancy: **Default**.
     - Tags: Key: `Project` - Value: `aws-eks-secure-network-fabric`; Key: `Environment` - Value: `prod`.
     - Nhấp **Create VPC**.

   - **VPC 3 — Inspection VPC:**
     - Resources to create: Chọn **VPC only**.
     - Name tag: Nhập `fabric-inspection-vpc`.
     - IPv4 CIDR: Nhập `10.70.0.0/16`.
     - Tenancy: **Default**.
     - Tags: Key: `Project` - Value: `aws-eks-secure-network-fabric`; Key: `Environment` - Value: `prod`.
     - Nhấp **Create VPC**.

   - **VPC 4 — Centralized Egress VPC:**
     - Resources to create: Chọn **VPC only**.
     - Name tag: Nhập `fabric-egress-vpc`.
     - IPv4 CIDR: Nhập `10.80.0.0/16`.
     - Tenancy: **Default**.
     - Tags: Key: `Project` - Value: `aws-eks-secure-network-fabric`; Key: `Environment` - Value: `prod`.
     - Nhấp **Create VPC**.

### Bước 2: Bật DNS Hostnames & DNS Resolution Cho Cả 4 VPCs
AWS mặc định tắt DNS Hostnames khi tạo VPC bằng chế độ "VPC only". Cần bật trên cả 4 VPCs để hỗ trợ EKS và VPC Endpoints:
1. Tại danh sách **Your VPCs**, chọn checkbox trước `fabric-edge-vpc`.
2. Nhấp menu **Actions** ở góc trên -> Chọn **Edit VPC settings**.
3. Tại phần **DNS settings**:
   - Đánh dấu tích vào **Enable DNS resolution**.
   - Đánh dấu tích vào **Enable DNS hostnames**.
4. Nhấp **Save changes**.
5. Lặp lại bước này lần lượt cho `fabric-core-vpc`, `fabric-inspection-vpc`, và `fabric-egress-vpc`.

### Bước 3: Tạo & Gắn Internet Gateways (Chỉ Cho Edge và Egress VPC)
1. Tại menu điều hướng bên trái VPC Console, chọn **Internet gateways** -> Nhấp **Create internet gateway**.
2. **Tạo Edge IGW:**
   - Name tag: `fabric-edge-igw`.
   - Tags: Key: `Project`, Value: `aws-eks-secure-network-fabric`.
   - Nhấp **Create internet gateway**.
   - Tại trang chi tiết vừa tạo, nhấp nút **Actions** -> Chọn **Attach to VPC** -> Chọn `fabric-edge-vpc` -> Nhấp **Attach internet gateway**.
3. **Tạo Egress IGW:**
   - Nhấp lại **Create internet gateway**.
   - Name tag: `fabric-egress-igw`.
   - Tags: Key: `Project`, Value: `aws-eks-secure-network-fabric`.
   - Nhấp **Create internet gateway**.
   - Nhấp nút **Actions** -> Chọn **Attach to VPC** -> Chọn `fabric-egress-vpc` -> Nhấp **Attach internet gateway**.

### Bước 4: Khởi Tạo 26 Subnets Phân Bổ Đa AZ Tại Singapore
Tại menu bên trái VPC Console, chọn **Subnets** -> Nhấp nút cam **Create subnet**. Thực hiện tuần tự cho từng VPC:

#### A. Nhóm Subnets Cho Edge VPC (`fabric-edge-vpc`):
Chọn VPC: `fabric-edge-vpc`. Tạo 8 subnets (nhấp **Add new subnet** để thêm từng dòng):
1. Name: `fabric-edge-public-1a` | AZ: `ap-southeast-1a` | CIDR: `10.40.0.0/24`
2. Name: `fabric-edge-public-1b` | AZ: `ap-southeast-1b` | CIDR: `10.40.1.0/24`
3. Name: `fabric-edge-nodes-1a`  | AZ: `ap-southeast-1a` | CIDR: `10.40.10.0/22`
4. Name: `fabric-edge-nodes-1b`  | AZ: `ap-southeast-1b` | CIDR: `10.40.14.0/22`
5. Name: `fabric-edge-vpce-1a`   | AZ: `ap-southeast-1a` | CIDR: `10.40.20.0/24`
6. Name: `fabric-edge-vpce-1b`   | AZ: `ap-southeast-1b` | CIDR: `10.40.21.0/24`
7. Name: `fabric-edge-tgw-1a`    | AZ: `ap-southeast-1a` | CIDR: `10.40.250.0/28`
8. Name: `fabric-edge-tgw-1b`    | AZ: `ap-southeast-1b` | CIDR: `10.40.250.16/28`
Nhấp **Create subnet**.

#### B. Nhóm Subnets Cho Core VPC (`fabric-core-vpc`):
Nhấp **Create subnet**, chọn VPC: `fabric-core-vpc`. Tạo 8 subnets:
1. Name: `fabric-core-nodes-1a`  | AZ: `ap-southeast-1a` | CIDR: `10.50.10.0/22`
2. Name: `fabric-core-nodes-1b`  | AZ: `ap-southeast-1b` | CIDR: `10.50.14.0/22`
3. Name: `fabric-core-data-1a`   | AZ: `ap-southeast-1a` | CIDR: `10.50.20.0/24`
4. Name: `fabric-core-data-1b`   | AZ: `ap-southeast-1b` | CIDR: `10.50.21.0/24`
5. Name: `fabric-core-vpce-1a`   | AZ: `ap-southeast-1a` | CIDR: `10.50.30.0/24`
6. Name: `fabric-core-vpce-1b`   | AZ: `ap-southeast-1b` | CIDR: `10.50.31.0/24`
7. Name: `fabric-core-tgw-1a`    | AZ: `ap-southeast-1a` | CIDR: `10.50.250.0/28`
8. Name: `fabric-core-tgw-1b`    | AZ: `ap-southeast-1b` | CIDR: `10.50.250.16/28`
Nhấp **Create subnet**.

#### C. Nhóm Subnets Cho Inspection VPC (`fabric-inspection-vpc`):
Nhấp **Create subnet**, chọn VPC: `fabric-inspection-vpc`. Tạo 6 subnets:
1. Name: `fabric-insp-tgw-1a`    | AZ: `ap-southeast-1a` | CIDR: `10.70.0.0/28`
2. Name: `fabric-insp-tgw-1b`    | AZ: `ap-southeast-1b` | CIDR: `10.70.0.16/28`
3. Name: `fabric-insp-gwlbe-1a`  | AZ: `ap-southeast-1a` | CIDR: `10.70.1.0/28`
4. Name: `fabric-insp-gwlbe-1b`  | AZ: `ap-southeast-1b` | CIDR: `10.70.1.16/28`
5. Name: `fabric-insp-fw-1a`     | AZ: `ap-southeast-1a` | CIDR: `10.70.10.0/24`
6. Name: `fabric-insp-fw-1b`     | AZ: `ap-southeast-1b` | CIDR: `10.70.11.0/24`
Nhấp **Create subnet**.

#### D. Nhóm Subnets Cho Centralized Egress VPC (`fabric-egress-vpc`):
Nhấp **Create subnet**, chọn VPC: `fabric-egress-vpc`. Tạo 6 subnets:
1. Name: `fabric-egress-tgw-1a`    | AZ: `ap-southeast-1a` | CIDR: `10.80.0.0/28`
2. Name: `fabric-egress-tgw-1b`    | AZ: `ap-southeast-1b` | CIDR: `10.80.0.16/28`
3. Name: `fabric-egress-fw-1a`     | AZ: `ap-southeast-1a` | CIDR: `10.80.1.0/28`
4. Name: `fabric-egress-fw-1b`     | AZ: `ap-southeast-1b` | CIDR: `10.80.1.16/28`
5. Name: `fabric-egress-public-1a` | AZ: `ap-southeast-1a` | CIDR: `10.80.10.0/24`
6. Name: `fabric-egress-public-1b` | AZ: `ap-southeast-1b` | CIDR: `10.80.11.0/24`
Nhấp **Create subnet**.

### Bước 5: Kích Hoạt Tự Động Cấp Phát Public IP Cho Public Subnets
1. Tại danh sách **Subnets**, tìm và chọn `fabric-edge-public-1a`.
2. Nhấp menu **Actions** -> Chọn **Edit subnet settings**.
3. Tại phần **Auto-assign IP settings**, đánh dấu tích vào **Enable auto-assign public IPv4 address**.
4. Nhấp **Save**.
5. Lặp lại bước trên cho `fabric-edge-public-1b`, `fabric-egress-public-1a`, và `fabric-egress-public-1b`.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy các lệnh xác minh trạng thái VPCs và Subnets qua AWS CLI hoặc MCP Server (`aws-api-mcp/call_aws`):
```bash
# 1. Liệt kê 4 VPCs vừa tạo kèm trạng thái và DNS settings
aws ec2 describe-vpcs --region ap-southeast-1 \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query 'Vpcs[*].{VpcId:VpcId,Cidr:CidrBlock,Name:Tags[?Key==`Name`].Value | [0],State:State}' \
  --output table

# 2. Đếm tổng số Subnet đã khởi tạo (kỳ vọng đúng 26 subnets)
aws ec2 describe-subnets --region ap-southeast-1 \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query 'length(Subnets)' --output text

# 3. Kiểm tra danh sách 2 Internet Gateways đã gắn đúng VPC
aws ec2 describe-internet-gateways --region ap-southeast-1 \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query 'InternetGateways[*].{IgwId:InternetGatewayId,Name:Tags[?Key==`Name`].Value | [0],VpcAttachment:Attachments[0].VpcId}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Trong trường hợp cần xóa toàn bộ VPC để tái tạo từ đầu:
1. Tại VPC Console, gỡ attach 2 Internet Gateways (`fabric-edge-igw`, `fabric-egress-igw`) khỏi VPCs và xóa IGWs.
2. Xóa toàn bộ 26 Subnets trong từng VPC.
3. Xóa 4 VPCs: `fabric-edge-vpc`, `fabric-core-vpc`, `fabric-inspection-vpc`, `fabric-egress-vpc`.
4. Hoặc thực thi dọn dẹp nhanh qua CLI:
   ```bash
   for vpc_id in $(aws ec2 describe-vpcs --region ap-southeast-1 --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" --query 'Vpcs[*].VpcId' --output text); do
     # Xóa Subnets
     for sub_id in $(aws ec2 describe-subnets --region ap-southeast-1 --filters "Name=vpc-id,Values=$vpc_id" --query 'Subnets[*].SubnetId' --output text); do
       aws ec2 delete-subnet --region ap-southeast-1 --subnet-id $sub_id
     done
     # Xóa VPC
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
- [ ] 2 Internet Gateways được gắn đúng vào `fabric-edge-vpc` và `fabric-egress-vpc`.
- [ ] Không có Internet Gateway nào được gắn vào `fabric-core-vpc` hoặc `fabric-inspection-vpc`.
- [ ] Toàn bộ 26 subnets được gán đúng dải IP và AZ tương ứng (`ap-southeast-1a`, `ap-southeast-1b`).
