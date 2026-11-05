# 02.01 — Khởi Tạo 4 VPCs & Hệ Thống Subnets Đa AZ Tại Singapore

> **Mã bài lab:** `02.01`  
> **Trạng thái:** `RUNTIME_PASS`  
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

> [!WARNING]
> **Nguyên tắc An ninh Cốt lõi (Strict VPC Isolation):**
> - **Chỉ tạo và gắn IGW vào đúng 2 VPCs:** `fabric-edge-vpc` (đón traffic Internet vào ALB Ingress) và `fabric-egress-vpc` (cho phép NAT Gateways đẩy traffic ra ngoài Internet).
> - **Tuyệt đối KHÔNG gắn IGW vào `fabric-core-vpc` hoặc `fabric-inspection-vpc`**. Hai VPC này hoàn toàn private, mọi kết nối ra ngoài hoặc giữa các VPC bắt buộc phải đi qua Transit Gateway.

#### 1. Tạo & Gắn Internet Gateway cho Edge VPC (`fabric-edge-vpc`)
- **Cách thực hiện trên Console:**
  1. Tại menu điều hướng bên trái VPC Console, chọn **Internet gateways** -> Nhấp nút cam **Create internet gateway**.
  2. Điền thông tin cấu hình:
     - **Name tag:** `fabric-edge-igw`.
     - **Tags:**
       - Key: `Project` | Value: `aws-eks-secure-network-fabric`
       - Key: `Environment` | Value: `prod`
       - Key: `ManagedBy` | Value: `console-lab`
  3. Nhấp **Create internet gateway** (tài nguyên tạo thành công có ID: `igw-0849ffbd341601849`).
  4. Tại trang chi tiết IGW, nhấp nút **Actions** ở góc trên bên phải -> Chọn **Attach to VPC**.
  5. Trong ô **Available VPCs**, chọn `fabric-edge-vpc` (`vpc-0468b18dddd1d4d2d`) -> Nhấp **Attach internet gateway**.
- **Lệnh tương đương qua AWS CLI:**
  ```bash
  # Tạo Edge IGW
  EDGE_IGW_ID=$(aws ec2 create-internet-gateway --region ap-southeast-1 \
    --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=fabric-edge-igw},{Key=Project,Value=aws-eks-secure-network-fabric},{Key=Environment,Value=prod},{Key=ManagedBy,Value=console-lab}]" \
    --query 'InternetGateway.InternetGatewayId' --output text)

  # Gắn vào fabric-edge-vpc
  aws ec2 attach-internet-gateway --region ap-southeast-1 \
    --internet-gateway-id $EDGE_IGW_ID \
    --vpc-id vpc-0468b18dddd1d4d2d
  ```

#### 2. Tạo & Gắn Internet Gateway cho Egress VPC (`fabric-egress-vpc`)
- **Cách thực hiện trên Console:**
  1. Tại menu **Internet gateways**, tiếp tục nhấp nút cam **Create internet gateway**.
  2. Điền thông tin cấu hình:
     - **Name tag:** `fabric-egress-igw`.
     - **Tags:**
       - Key: `Project` | Value: `aws-eks-secure-network-fabric`
       - Key: `Environment` | Value: `prod`
       - Key: `ManagedBy` | Value: `console-lab`
  3. Nhấp **Create internet gateway** (tài nguyên tạo thành công có ID: `igw-0742fe0915c3feadc`).
  4. Nhấp nút **Actions** -> Chọn **Attach to VPC**.
  5. Trong ô **Available VPCs**, chọn `fabric-egress-vpc` (`vpc-0c1479727a5e38b4c`) -> Nhấp **Attach internet gateway**.
- **Lệnh tương đương qua AWS CLI:**
  ```bash
  # Tạo Egress IGW
  EGRESS_IGW_ID=$(aws ec2 create-internet-gateway --region ap-southeast-1 \
    --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=fabric-egress-igw},{Key=Project,Value=aws-eks-secure-network-fabric},{Key=Environment,Value=prod},{Key=ManagedBy,Value=console-lab}]" \
    --query 'InternetGateway.InternetGatewayId' --output text)

  # Gắn vào fabric-egress-vpc
  aws ec2 attach-internet-gateway --region ap-southeast-1 \
    --internet-gateway-id $EGRESS_IGW_ID \
    --vpc-id vpc-0c1479727a5e38b4c
  ```

### Bước 4: Khởi Tạo 28 Subnets Phân Bổ Đa AZ Tại Singapore & Chú Thích Công Dụng

Tại menu bên trái VPC Console, chọn **Subnets** -> Nhấp nút cam **Create subnet**. Thực hiện tuần tự tạo 28 subnets cho 4 VPCs, mỗi subnet đều có vai trò kỹ thuật chuyên biệt:

---

#### A. Nhóm Subnets Cho Edge VPC (`fabric-edge-vpc` — `10.40.0.0/16`):
Chọn VPC: `fabric-edge-vpc`. Tạo 8 subnets (nhấp **Add new subnet** để thêm từng dòng):

1. **`fabric-edge-public-1a`** (`subnet-04dfffbdc3e5e0c93`) | AZ: `ap-southeast-1a` | CIDR: `10.40.0.0/24` (251 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet Public AZ-a đón lưu lượng người dùng từ Internet. Dùng để đặt các giao diện mạng của Internet-facing Application Load Balancer (ALB Ingress) tích hợp AWS WAF v2. Đã kích hoạt Auto-assign Public IP.
2. **`fabric-edge-public-1b`** (`subnet-0a9017b8109df0c48`) | AZ: `ap-southeast-1b` | CIDR: `10.40.1.0/24` (251 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet Public AZ-b đảm bảo khả năng chịu lỗi đa AZ (Multi-AZ High Availability) cho cụm Ingress ALB. Đã kích hoạt Auto-assign Public IP.
3. **`fabric-edge-nodes-1a`** (`subnet-0e9f90d0d4e220d3a`) | AZ: `ap-southeast-1a` | CIDR: `10.40.8.0/22` (1,019 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet Private chứa EKS Managed Worker Nodes (cụm `edge-eks`) và phân bổ IP trực tiếp cho các Pods biên: `frontend` và `auth-service` thông qua AWS VPC CNI. Dải `/22` (chuẩn boundary `10.40.8.0` - `10.40.11.255`) đảm bảo hơn 1,000 IPs khi mở rộng tải.
4. **`fabric-edge-nodes-1b`** (`subnet-034f4fc00bfd6cd09`) | AZ: `ap-southeast-1b` | CIDR: `10.40.12.0/22` (1,019 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet Private AZ-b (chuẩn boundary `10.40.12.0` - `10.40.15.255`) chứa worker nodes và phân bổ Pods dự phòng cho cụm Edge EKS.
5. **`fabric-edge-vpce-1a`** (`subnet-01aa1d8c163dffca5`) | AZ: `ap-southeast-1a` | CIDR: `10.40.20.0/24` (251 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet chuyên dụng đặt các điểm cuối dịch vụ riêng tư (Interface VPC Endpoints - ENIs) tại AZ-a: ECR API/DKR, STS, CloudWatch Logs, EC2, phục vụ cụm EKS kéo image và xác thực không cần ra Internet.
6. **`fabric-edge-vpce-1b`** (`subnet-06c83b89e45f47650`) | AZ: `ap-southeast-1b` | CIDR: `10.40.21.0/24` (251 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet chuyên dụng đặt Interface VPC Endpoints dự phòng tại AZ-b.
7. **`fabric-edge-tgw-1a`** (`subnet-0ee88bbf364687ec6`) | AZ: `ap-southeast-1a` | CIDR: `10.40.250.0/28` (11 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet chuyên dụng (Dedicated `/28`) chỉ chứa duy nhất ENI kết nối của Transit Gateway tại AZ-a. Không đặt thêm bất kỳ tài nguyên nào khác để tránh xung đột định tuyến.
8. **`fabric-edge-tgw-1b`** (`subnet-027f9fd24d6ff94ca`) | AZ: `ap-southeast-1b` | CIDR: `10.40.250.16/28` (11 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet TGW Attachment chuyên dụng tại AZ-b.

Nhấp nút **Create subnet**.

---

#### B. Nhóm Subnets Cho Core VPC (`fabric-core-vpc` — `10.50.0.0/16`):
Nhấp **Create subnet**, chọn VPC: `fabric-core-vpc`. Tạo 8 subnets:

1. **`fabric-core-nodes-1a`** (`subnet-0124e28037a2e4118`) | AZ: `ap-southeast-1a` | CIDR: `10.50.8.0/22` (1,019 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet Private chứa EKS Managed Worker Nodes (cụm `core-eks`) và phân bổ IP cho các microservices lõi: `order-service`, `inventory-service`, `payment-worker`. Dải `/22` (chuẩn boundary `10.50.8.0` - `10.50.11.255`).
2. **`fabric-core-nodes-1b`** (`subnet-0fe561d6217b04955`) | AZ: `ap-southeast-1b` | CIDR: `10.50.12.0/22` (1,019 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet Private AZ-b (chuẩn boundary `10.50.12.0` - `10.50.15.255`) chứa worker nodes và pods dự phòng cho cụm Core EKS.
3. **`fabric-core-data-1a`** (`subnet-060f6827edc15bf70`) | AZ: `ap-southeast-1a` | CIDR: `10.50.20.0/24` (251 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet dữ liệu cô lập tuyệt đối (Isolated Data Tier). Chứa Aurora PostgreSQL Serverless v2 Primary Instance và ElastiCache Redis Node A. Subnet này không có route ra Internet hay TGW.
4. **`fabric-core-data-1b`** (`subnet-0d738daa01c9369d3`) | AZ: `ap-southeast-1b` | CIDR: `10.50.21.0/24` (251 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet dữ liệu cô lập AZ-b chứa Aurora PostgreSQL Read Replica và ElastiCache Redis Node B.
5. **`fabric-core-vpce-1a`** (`subnet-053d2f1c4cf3235c6`) | AZ: `ap-southeast-1a` | CIDR: `10.50.30.0/24` (251 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet đặt Interface VPC Endpoints AZ-a: ECR, STS, Logs, EC2, và SQS VPC Endpoint phục vụ `payment-worker` tiêu thụ hàng đợi nội bộ an toàn.
6. **`fabric-core-vpce-1b`** (`subnet-0f4c9a2c5bcf93261`) | AZ: `ap-southeast-1b` | CIDR: `10.50.31.0/24` (251 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet đặt Interface VPC Endpoints dự phòng tại AZ-b.
7. **`fabric-core-tgw-1a`** (`subnet-0b8fbf236704cd49f`) | AZ: `ap-southeast-1a` | CIDR: `10.50.250.0/28` (11 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet chuyên dụng (Dedicated `/28`) chỉ chứa ENI kết nối Transit Gateway tại AZ-a để nhận traffic đã được kiểm duyệt từ Inspection VPC và gửi outbound traffic sang Egress VPC.
8. **`fabric-core-tgw-1b`** (`subnet-067ef27abb3c9fc27`) | AZ: `ap-southeast-1b` | CIDR: `10.50.250.16/28` (11 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet TGW Attachment chuyên dụng tại AZ-b.

Nhấp nút **Create subnet**.

---

#### C. Nhóm Subnets Cho Inspection VPC (`fabric-inspection-vpc` — `10.70.0.0/16`):
Nhấp **Create subnet**, chọn VPC: `fabric-inspection-vpc`. Tạo 6 subnets phân tách 3 lớp kiến trúc GWLB:

1. **`fabric-insp-tgw-1a`** (`subnet-0e260eae20eea3ccb`) | AZ: `ap-southeast-1a` | CIDR: `10.70.0.0/28` (11 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet TGW Attachment AZ-a (bật **Appliance Mode = ENABLED**). Đón luồng East-West giữa Edge và Core, ép toàn bộ các gói tin cùng phiên kết nối phải đi qua cùng một máy chủ an ninh trong cùng AZ.
2. **`fabric-insp-tgw-1b`** (`subnet-0a1481ce7d8302538`) | AZ: `ap-southeast-1b` | CIDR: `10.70.0.16/28` (11 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet TGW Attachment AZ-b (bật **Appliance Mode = ENABLED**).
3. **`fabric-insp-gwlbe-1a`** (`subnet-0aebf9d83c8118058`) | AZ: `ap-southeast-1a` | CIDR: `10.70.1.0/28` (11 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet chứa Gateway Load Balancer Endpoint (GWLBe) AZ-a. Đóng vai trò điểm trung chuyển (next-hop) đón gói tin từ TGW, đóng gói GENEVE UDP 6081 và chuyển tới cụm Suricata EC2.
4. **`fabric-insp-gwlbe-1b`** (`subnet-0a1a561fe99bcc9fd`) | AZ: `ap-southeast-1b` | CIDR: `10.70.1.16/28` (11 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet chứa Gateway Load Balancer Endpoint (GWLBe) AZ-b.
5. **`fabric-insp-fw-1a`** (`subnet-0b743a1b6492b62ce`) | AZ: `ap-southeast-1a` | CIDR: `10.70.10.0/24` (251 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet Firewall AZ-a chứa máy chủ ảo Suricata EC2 Instance A (Target Group của GWLB). Thực hiện giải mã GENEVE, kiểm tra sâu gói tin IDS/IPS, drop gói tin độc hại và ghi nhật ký `eve.json`.
6. **`fabric-insp-fw-1b`** (`subnet-00621165b37f9a04e`) | AZ: `ap-southeast-1b` | CIDR: `10.70.11.0/24` (251 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet Firewall AZ-b chứa máy chủ ảo Suricata EC2 Instance B đảm bảo dự phòng cao (High Availability).

Nhấp nút **Create subnet**.

---

#### D. Nhóm Subnets Cho Centralized Egress VPC (`fabric-egress-vpc` — `10.80.0.0/16`):
Nhấp **Create subnet**, chọn VPC: `fabric-egress-vpc`. Tạo 6 subnets:

1. **`fabric-egress-tgw-1a`** (`subnet-0a9b70d43770f1e86`) | AZ: `ap-southeast-1a` | CIDR: `10.80.0.0/28` (11 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet TGW Attachment AZ-a (bật **Appliance Mode = ENABLED**). Nhận toàn bộ lưu lượng ra Internet (`0.0.0.0/0`) từ Edge và Core chuyển tiếp tới Network Firewall Endpoint.
2. **`fabric-egress-tgw-1b`** (`subnet-0b0653845a52c4f75`) | AZ: `ap-southeast-1b` | CIDR: `10.80.0.16/28` (11 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet TGW Attachment AZ-b (bật **Appliance Mode = ENABLED**).
3. **`fabric-egress-fw-1a`** (`subnet-0c7142131794aa34c`) | AZ: `ap-southeast-1a` | CIDR: `10.80.1.0/28` (11 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet chứa AWS Network Firewall Endpoint AZ-a. Kiểm tra an ninh trạng thái L3-L7, lọc tên miền TLS SNI (Domain Allowlist) chỉ cho phép truy cập các domain được phê duyệt trước khi cho ra NAT Gateway.
4. **`fabric-egress-fw-1b`** (`subnet-05ce922d28724c2f9`) | AZ: `ap-southeast-1b` | CIDR: `10.80.1.16/28` (11 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet chứa AWS Network Firewall Endpoint AZ-b.
5. **`fabric-egress-public-1a`** (`subnet-0262d7eefa20689ed`) | AZ: `ap-southeast-1a` | CIDR: `10.80.10.0/24` (251 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet Public AZ-a chứa NAT Gateway A (gắn Elastic IP) và kết nối trực tiếp Internet Gateway (`fabric-egress-igw`). Thực hiện SNAT gói tin ra Internet và định tuyến gói tin phản hồi quay lại Firewall Endpoint.
6. **`fabric-egress-public-1b`** (`subnet-0ad99949d3dcf5d10`) | AZ: `ap-southeast-1b` | CIDR: `10.80.11.0/24` (251 IPs khả dụng)  
   - **Mục đích sử dụng:** Subnet Public AZ-b chứa NAT Gateway B (gắn Elastic IP) đảm bảo dự phòng độc lập theo AZ.

Nhấp nút **Create subnet**.

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

# 2. Đếm tổng số Subnet đã khởi tạo (kỳ vọng đúng 28 subnets)
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
2. Xóa toàn bộ 28 Subnets trong từng VPC.
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

- [x] Cả 4 VPCs đều ở trạng thái `available` tại Singapore `ap-southeast-1` (`vpc-0468b18dddd1d4d2d`, `vpc-09888cc991104c959`, `vpc-0c94a30a1a915fc0f`, `vpc-0c1479727a5e38b4c`).
- [x] Tính năng DNS resolution và DNS hostnames được bật (`true`) trên cả 4 VPCs.
- [x] 2 Internet Gateways được gắn đúng vào `fabric-edge-vpc` (`igw-0849ffbd341601849`) và `fabric-egress-vpc` (`igw-0742fe0915c3feadc`).
- [x] Không có Internet Gateway nào được gắn vào `fabric-core-vpc` hoặc `fabric-inspection-vpc`.
- [x] Toàn bộ 28 subnets được gán đúng dải IP và AZ tương ứng (`ap-southeast-1a`, `ap-southeast-1b`).

### Trạng Thái Thực Thi Runtime (All 4 VPCs, 2 IGWs & 28 Subnets Fully Completed)
- **Thời gian hoàn thành:** `2026-11-05T16:34:00Z`
- **Công cụ thực thi:** MCP `aws-api-mcp/call_aws`
- **VPCs Đã Tạo:**
  1. `fabric-edge-vpc`: `vpc-0468b18dddd1d4d2d` (CIDR: `10.40.0.0/16`, DNS Hostnames/Resolution: Enabled)
  2. `fabric-core-vpc`: `vpc-09888cc991104c959` (CIDR: `10.50.0.0/16`, DNS Hostnames/Resolution: Enabled)
  3. `fabric-inspection-vpc`: `vpc-0c94a30a1a915fc0f` (CIDR: `10.70.0.0/16`, DNS Hostnames/Resolution: Enabled)
  4. `fabric-egress-vpc`: `vpc-0c1479727a5e38b4c` (CIDR: `10.80.0.0/16`, DNS Hostnames/Resolution: Enabled)
- **Internet Gateways Đã Gắn & Gán Tags Chuẩn:**
  1. `fabric-edge-igw`: `igw-0849ffbd341601849` -> gắn vào `fabric-edge-vpc`
  2. `fabric-egress-igw`: `igw-0742fe0915c3feadc` -> gắn vào `fabric-egress-vpc`
- **8 Subnets Của Edge VPC Đã Tạo Thành Công:**
  1. `fabric-edge-public-1a`: `subnet-04dfffbdc3e5e0c93` (`10.40.0.0/24`, AZ-a, Public IP auto-assign: ON)
  2. `fabric-edge-public-1b`: `subnet-0a9017b8109df0c48` (`10.40.1.0/24`, AZ-b, Public IP auto-assign: ON)
  3. `fabric-edge-nodes-1a`: `subnet-0e9f90d0d4e220d3a` (`10.40.8.0/22`, AZ-a, 1,019 IPs)
  4. `fabric-edge-nodes-1b`: `subnet-034f4fc00bfd6cd09` (`10.40.12.0/22`, AZ-b, 1,019 IPs)
  5. `fabric-edge-vpce-1a`: `subnet-01aa1d8c163dffca5` (`10.40.20.0/24`, AZ-a)
  6. `fabric-edge-vpce-1b`: `subnet-06c83b89e45f47650` (`10.40.21.0/24`, AZ-b)
  7. `fabric-edge-tgw-1a`: `subnet-0ee88bbf364687ec6` (`10.40.250.0/28`, AZ-a)
  8. `fabric-edge-tgw-1b`: `subnet-027f9fd24d6ff94ca` (`10.40.250.16/28`, AZ-b)
- **8 Subnets Của Core VPC Đã Tạo Thành Công:**
  1. `fabric-core-nodes-1a`: `subnet-0124e28037a2e4118` (`10.50.8.0/22`, AZ-a, 1,019 IPs)
  2. `fabric-core-nodes-1b`: `subnet-0fe561d6217b04955` (`10.50.12.0/22`, AZ-b, 1,019 IPs)
  3. `fabric-core-data-1a`: `subnet-060f6827edc15bf70` (`10.50.20.0/24`, AZ-a, Aurora Primary / Redis A)
  4. `fabric-core-data-1b`: `subnet-0d738daa01c9369d3` (`10.50.21.0/24`, AZ-b, Aurora Replica / Redis B)
  5. `fabric-core-vpce-1a`: `subnet-053d2f1c4cf3235c6` (`10.50.30.0/24`, AZ-a, VPCE SQS/ECR/Logs)
  6. `fabric-core-vpce-1b`: `subnet-0f4c9a2c5bcf93261` (`10.50.31.0/24`, AZ-b)
  7. `fabric-core-tgw-1a`: `subnet-0b8fbf236704cd49f` (`10.50.250.0/28`, AZ-a)
  8. `fabric-core-tgw-1b`: `subnet-067ef27abb3c9fc27` (`10.50.250.16/28`, AZ-b)
- **6 Subnets Của Inspection VPC Đã Tạo Thành Công:**
  1. `fabric-insp-tgw-1a`: `subnet-0e260eae20eea3ccb` (`10.70.0.0/28`, AZ-a)
  2. `fabric-insp-tgw-1b`: `subnet-0a1481ce7d8302538` (`10.70.0.16/28`, AZ-b)
  3. `fabric-insp-gwlbe-1a`: `subnet-0aebf9d83c8118058` (`10.70.1.0/28`, AZ-a)
  4. `fabric-insp-gwlbe-1b`: `subnet-0a1a561fe99bcc9fd` (`10.70.1.16/28`, AZ-b)
  5. `fabric-insp-fw-1a`: `subnet-0b743a1b6492b62ce` (`10.70.10.0/24`, AZ-a)
  6. `fabric-insp-fw-1b`: `subnet-00621165b37f9a04e` (`10.70.11.0/24`, AZ-b)
- **6 Subnets Của Centralized Egress VPC Đã Tạo Thành Công:**
  1. `fabric-egress-tgw-1a`: `subnet-0a9b70d43770f1e86` (`10.80.0.0/28`, AZ-a)
  2. `fabric-egress-tgw-1b`: `subnet-0b0653845a52c4f75` (`10.80.0.16/28`, AZ-b)
  3. `fabric-egress-fw-1a`: `subnet-0c7142131794aa34c` (`10.80.1.0/28`, AZ-a)
  4. `fabric-egress-fw-1b`: `subnet-05ce922d28724c2f9` (`10.80.1.16/28`, AZ-b)
  5. `fabric-egress-public-1a`: `subnet-0262d7eefa20689ed` (`10.80.10.0/24`, AZ-a, Public IP auto-assign: ON)
  6. `fabric-egress-public-1b`: `subnet-0ad99949d3dcf5d10` (`10.80.11.0/24`, AZ-b, Public IP auto-assign: ON)
- **Xác Nhận Cô Lập (Zero IGW Attached):**
  - `fabric-core-vpc`: Không gắn IGW (100% Private).
  - `fabric-inspection-vpc`: Không gắn IGW (100% Private).
- **File bằng chứng:** `evidence/02-network/01-vpcs-and-subnets.json`
