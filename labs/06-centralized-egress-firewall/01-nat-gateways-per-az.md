# 06.01 — Khởi Tạo Cụm NAT Gateway Độc Lập Theo Từng AZ & Cổng Internet IGW

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Thiết lập lớp chuyển dịch địa chỉ mạng (Source NAT) độc lập cho từng Availability Zone trong Centralized Egress VPC.

---

## 1. Mục Tiêu Kỹ Thuật

- Cấp phát 2 địa chỉ IPv4 công khai (Elastic IPs - EIPs) tại Region Singapore (`ap-southeast-1`).
- Khởi tạo **Internet Gateway (IGW)** `fabric-egress-igw` và gắn vào `fabric-egress-vpc`.
- Khởi tạo 2 **NAT Gateways** riêng biệt đặt tại 2 Public Subnets của Egress VPC:
  1. `fabric-egress-nat-1a` đặt tại `fabric-egress-public-1a`.
  2. `fabric-egress-nat-1b` đặt tại `fabric-egress-public-1b`.
- **Nguyên tắc thiết kế:** Không dùng chung 1 NAT Gateway cho nhiều AZs nhằm triệt tiêu độ trễ xuyên vùng (cross-AZ latency) và tránh lỗi đơn điểm (Single Point of Failure).

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Khởi Tạo & Gắn Internet Gateway (IGW)
1. Mở dịch vụ **VPC Console** tại `ap-southeast-1` -> Chọn **Internet gateways** -> Nhấp **Create internet gateway**.
2. **Name tag:** `fabric-egress-igw` -> Nhấp **Create internet gateway**.
3. Tại trang chi tiết vừa tạo, nhấp nút **Actions** -> Chọn **Attach to VPC**.
4. Chọn VPC: `fabric-egress-vpc` -> Nhấp nút cam **Attach internet gateway**.

---

### Bước 2: Cấp Phát 2 Địa Chỉ Elastic IPs (EIPs)
1. Tại menu bên trái VPC Console, chọn **Elastic IPs** -> Nhấp nút cam **Allocate Elastic IP address**.
2. **Network border group:** `ap-southeast-1`.
3. **Tags:** `Name` = `fabric-egress-nat-eip-1a`, `Project` = `aws-eks-secure-network-fabric`.
4. Nhấp **Allocate**.
5. Lặp lại thao tác cấp phát thêm IP thứ hai với Name: `fabric-egress-nat-eip-1b`.

---

### Bước 3: Khởi Tạo 2 NAT Gateways
1. Tại menu bên trái VPC Console, chọn **NAT gateways** -> Nhấp nút cam **Create NAT gateway**.
2. **Cấu hình NAT Gateway 1 (AZ-a):**
   - **Name:** `fabric-egress-nat-1a`
   - **Subnet:** Chọn `fabric-egress-public-1a`.
   - **Connectivity type:** Chọn **Public**.
   - **Elastic IP allocation ID:** Chọn `fabric-egress-nat-eip-1a`.
   - Nhấp **Create NAT gateway**.
3. **Cấu hình NAT Gateway 2 (AZ-b):**
   - **Name:** `fabric-egress-nat-1b`
   - **Subnet:** Chọn `fabric-egress-public-1b`.
   - **Connectivity type:** Chọn **Public**.
   - **Elastic IP allocation ID:** Chọn `fabric-egress-nat-eip-1b`.
   - Nhấp **Create NAT gateway**.

---

## 3. Xác Minh (Verification)

Kiểm tra trạng thái NAT Gateways qua AWS CLI:
```bash
aws ec2 describe-nat-gateways \
  --region ap-southeast-1 \
  --filter "Name=vpc-id,Values=$(aws ec2 describe-vpcs --filters Name=tag:Name,Values=fabric-egress-vpc --query 'Vpcs[0].VpcId' --output text --region ap-southeast-1)" \
  --query 'NatGateways[*].{Id:NatGatewayId,Subnet:SubnetId,State:State,PublicIP:NatGatewayAddresses[0].PublicIp}' \
  --output table
```
> Kết quả: Cả 2 NAT Gateways đều ở trạng thái `available`.

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Internet Gateway được gắn kết thành công vào `fabric-egress-vpc`.
- [ ] 2 NAT Gateways ở trạng thái `available` tại đúng 2 Public Subnets của AZ-a và AZ-b.
