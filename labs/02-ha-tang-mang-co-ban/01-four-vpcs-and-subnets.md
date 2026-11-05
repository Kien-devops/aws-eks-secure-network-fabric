# 02.01 — Khởi Tạo 4 VPCs & Hệ Thống Subnets Đa AZ Trên AWS Console

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Xây dựng 4 VPCs biệt lập và phân chia Subnets tại 2 Availability Zones (`ap-southeast-1a`, `ap-southeast-1b`).

---

## 1. Mục Tiêu Kỹ Thuật

- Khởi tạo 4 VPCs: `fabric-edge-vpc` (`10.40.0.0/16`), `fabric-core-vpc` (`10.50.0.0/16`), `fabric-inspection-vpc` (`10.70.0.0/16`), `fabric-egress-vpc` (`10.80.0.0/16`).
- Kích hoạt thuộc tính **Enable DNS hostnames** và **Enable DNS resolution** cho cả 4 VPCs.
- Tạo toàn bộ subnets theo đúng bảng phân bổ dải mạng tại Module 01.

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Khởi Tạo 4 Virtual Private Clouds (VPCs)
1. Đăng nhập AWS Console tại Region **Singapore (`ap-southeast-1`)** -> Mở dịch vụ **VPC**.
2. Tại menu bên trái, nhấp vào **Your VPCs** -> Nhấp nút cam **Create VPC**.
3. **Cấu hình VPC 1 (Edge VPC):**
   - Chọn radio button: **VPC only**.
   - **Name tag:** `fabric-edge-vpc`.
   - **IPv4 CIDR block:** `10.40.0.0/16`.
   - **Tenancy:** `Default`.
   - **Tags:** `Project` = `aws-eks-secure-network-fabric`, `Environment` = `dev`.
   - Nhấp **Create VPC**.
4. Lặp lại thao tác cho 3 VPC còn lại:
   - **VPC 2 (Core VPC):** Name: `fabric-core-vpc`, CIDR: `10.50.0.0/16`.
   - **VPC 3 (Inspection VPC):** Name: `fabric-inspection-vpc`, CIDR: `10.70.0.0/16`.
   - **VPC 4 (Egress VPC):** Name: `fabric-egress-vpc`, CIDR: `10.80.0.0/16`.

---

### Bước 2: Bật Thuộc Tính DNS Cho Cả 4 VPCs
Với mỗi VPC vừa tạo:
1. Chọn VPC trong danh sách -> Nhấp menu **Actions** ở góc trên -> Chọn **Edit VPC settings**.
2. Tại mục **DNS settings**:
   - Tích chọn **Enable DNS resolution**.
   - Tích chọn **Enable DNS hostnames**.
3. Nhấp **Save changes**.

---

### Bước 3: Khởi Tạo Subnets Cho Từng VPC

1. Tại menu bên trái, chọn **Subnets** -> Nhấp nút cam **Create subnet**.
2. Chọn VPC tương ứng và nhập thông số từng subnet:
   - **Tại `fabric-edge-vpc`:**
     - `fabric-edge-public-1a`: AZ `ap-southeast-1a`, CIDR `10.40.0.0/24`
     - `fabric-edge-public-1b`: AZ `ap-southeast-1b`, CIDR `10.40.1.0/24`
     - `fabric-edge-node-1a`: AZ `ap-southeast-1a`, CIDR `10.40.10.0/22`
     - `fabric-edge-node-1b`: AZ `ap-southeast-1b`, CIDR `10.40.14.0/22`
     - `fabric-edge-tgw-1a`: AZ `ap-southeast-1a`, CIDR `10.40.250.0/28`
     - `fabric-edge-tgw-1b`: AZ `ap-southeast-1b`, CIDR `10.40.250.16/28`
   - **Tại `fabric-core-vpc`:**
     - `fabric-core-node-1a`: AZ `ap-southeast-1a`, CIDR `10.50.10.0/22`
     - `fabric-core-node-1b`: AZ `ap-southeast-1b`, CIDR `10.50.14.0/22`
     - `fabric-core-data-1a`: AZ `ap-southeast-1a`, CIDR `10.50.20.0/24`
     - `fabric-core-data-1b`: AZ `ap-southeast-1b`, CIDR `10.50.21.0/24`
     - `fabric-core-tgw-1a`: AZ `ap-southeast-1a`, CIDR `10.50.250.0/28`
     - `fabric-core-tgw-1b`: AZ `ap-southeast-1b`, CIDR `10.50.250.16/28`
   - **Tại `fabric-inspection-vpc`:**
     - `fabric-inspection-tgw-1a`: AZ `ap-southeast-1a`, CIDR `10.70.0.0/28`
     - `fabric-inspection-tgw-1b`: AZ `ap-southeast-1b`, CIDR `10.70.0.16/28`
     - `fabric-inspection-gwlbe-1a`: AZ `ap-southeast-1a`, CIDR `10.70.1.0/28`
     - `fabric-inspection-gwlbe-1b`: AZ `ap-southeast-1b`, CIDR `10.70.1.16/28`
     - `fabric-inspection-fw-1a`: AZ `ap-southeast-1a`, CIDR `10.70.10.0/24`
     - `fabric-inspection-fw-1b`: AZ `ap-southeast-1b`, CIDR `10.70.11.0/24`
   - **Tại `fabric-egress-vpc`:**
     - `fabric-egress-tgw-1a`: AZ `ap-southeast-1a`, CIDR `10.80.0.0/28`
     - `fabric-egress-tgw-1b`: AZ `ap-southeast-1b`, CIDR `10.80.0.16/28`
     - `fabric-egress-nfw-1a`: AZ `ap-southeast-1a`, CIDR `10.80.1.0/28`
     - `fabric-egress-nfw-1b`: AZ `ap-southeast-1b`, CIDR `10.80.1.16/28`
     - `fabric-egress-public-1a`: AZ `ap-southeast-1a`, CIDR `10.80.10.0/24`
     - `fabric-egress-public-1b`: AZ `ap-southeast-1b`, CIDR `10.80.11.0/24`

3. Nhấp **Create subnet** hoàn tất tạo toàn bộ subnets.

---

## 3. Xác Minh Bằng AWS CLI (Qua MCP `aws-api-mcp/call_aws`)

Chạy lệnh kiểm tra danh sách VPC và subnets:
```bash
aws ec2 describe-vpcs \
  --region ap-southeast-1 \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query 'Vpcs[*].{Name:Tags[?Key==`Name`].Value | [0],Cidr:CidrBlock,DnsHostnames:EnableDnsHostnames}' \
  --output table
```

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Cả 4 VPCs đều ở trạng thái `available` với DNS Hostnames = `true`.
- [ ] 24 subnets được tạo đầy đủ trên cả 2 AZs `ap-southeast-1a` và `ap-southeast-1b`.
