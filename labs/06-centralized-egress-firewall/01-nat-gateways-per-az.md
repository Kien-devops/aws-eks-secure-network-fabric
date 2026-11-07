# 06.01 — Khởi Tạo NAT Gateways & Elastic IPs Đa AZ Tại Public Subnets

> **Mã bài lab:** `06.01`  
> **Trạng thái:** `COMPLETED`  
> **Thời gian dự kiến:** 20 phút  
> **Chi phí ước tính:** ~$0.045 USD / giờ / NAT Gateway (~$0.09 USD / giờ cho 2 NAT Gateways)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — Subnets: `fabric-egress-public-1a`, `fabric-egress-public-1b`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành hạ tầng Centralized Egress VPC tại [Module 02](../02-ha-tang-mang-co-ban/README.md).
- Internet Gateway `fabric-egress-igw` đã được gắn vào `fabric-egress-vpc` và Public Subnet Route Table đã trỏ `0.0.0.0/0` ra IGW.
- Subnets `fabric-egress-public-1a` (`10.80.10.0/24`) và `fabric-egress-public-1b` (`10.80.11.0/24`) đã sẵn sàng.
- Đang mở phiên AWS Management Console tại Singapore `ap-southeast-1`.

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
        "ec2:AllocateAddress",
        "ec2:DescribeAddresses",
        "ec2:ReleaseAddress",
        "ec2:CreateNatGateway",
        "ec2:DescribeNatGateways",
        "ec2:DeleteNatGateway",
        "ec2:CreateTags"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** 2 NAT Gateways tiêu tốn ~$2.16 USD/ngày cố định cộng với phí xử lý dữ liệu ($0.045 USD/GB). Đây là thành phần ngốn chi phí liên tục, cần chủ động dọn dẹp theo Module 12 khi kết thúc phiên thử nghiệm.
- **Cảnh báo tính độc lập vùng (Zonal Isolation):** Bắt buộc phải triển khai 2 NAT Gateways riêng biệt tại 2 AZs:
  - `fabric-nat-gw-1a` tại `ap-southeast-1a` (Public Subnet A).
  - `fabric-nat-gw-1b` tại `ap-southeast-1b` (Public Subnet B).
  Mô hình 2 NAT Gateways đảm bảo: Nếu một AZ gặp sự cố, AZ còn lại vẫn tiếp tục phục vụ lưu lượng ra ngoài mà không bị mất kết nối; đồng thời ngăn ngừa chi phí truyền dữ liệu liên vùng (cross-AZ data transfer fees).

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Cấp Phát 2 Địa Chỉ Elastic IP (EIP)
Mở **VPC Console** tại Singapore `ap-southeast-1`:
1. Tại menu điều hướng bên trái, cuộn xuống mục **Virtual private cloud** -> Chọn **Elastic IP addresses**.
2. Nhấp vào nút cam **Allocate Elastic IP address** ở góc trên bên phải.
3. **Cấp phát EIP 1 (`fabric-nat-eip-1a`):**
   - **Network Border Group:** Chọn `ap-southeast-1`.
   - **Public IPv4 address pool:** Chọn **Amazon's pool of IPv4 addresses**.
   - **Tags:**
     - Key: `Name` | Value: `fabric-nat-eip-1a`
     - Key: `Project` | Value: `aws-eks-secure-network-fabric`
     - Key: `AZ` | Value: `ap-southeast-1a`
   - Nhấp nút cam **Allocate**.
4. **Cấp phát EIP 2 (`fabric-nat-eip-1b`):**
   - Tiếp tục nhấp **Allocate Elastic IP address**.
   - **Tags:**
     - Key: `Name` | Value: `fabric-nat-eip-1b`
     - Key: `Project` | Value: `aws-eks-secure-network-fabric`
     - Key: `AZ` | Value: `ap-southeast-1b`
   - Nhấp **Allocate**.
5. Ghi nhận 2 địa chỉ Public IPv4 và Allocation IDs vừa cấp phát.

---

### Bước 2: Khởi Tạo NAT Gateway Tại AZ-a (`fabric-nat-gw-1a`)
Tại menu điều hướng bên trái VPC Console -> Chọn **NAT gateways**:
1. Nhấp vào nút cam **Create NAT gateway** ở góc trên bên phải.
2. **NAT gateway settings:**
   - **Name:** Nhập `fabric-nat-gw-1a`.
   - **Subnet:** Chọn `fabric-egress-public-1a` (`10.80.10.0/24`).
   - **Connectivity type:** Chọn **Public** (Để có thể liên lạc trực tiếp với Internet Gateway).
   - **Elastic IP allocation ID:** Tìm và chọn `fabric-nat-eip-1a` từ danh sách thả xuống.
   - **Secondary private IPv4 addresses:** Giữ mặc định (0).
   - **Tags:**
     - Key: `Project` | Value: `aws-eks-secure-network-fabric`
     - Key: `Environment` | Value: `prod`
3. Nhấp nút cam **Create NAT gateway** ở cuối trang.

---

### Bước 3: Khởi Tạo NAT Gateway Tại AZ-b (`fabric-nat-gw-1b`)
Tại danh sách **NAT gateways**, tiếp tục nhấp **Create NAT gateway**:
1. **NAT gateway settings:**
   - **Name:** Nhập `fabric-nat-gw-1b`.
   - **Subnet:** Chọn `fabric-egress-public-1b` (`10.80.11.0/24`).
   - **Connectivity type:** Chọn **Public**.
   - **Elastic IP allocation ID:** Chọn `fabric-nat-eip-1b`.
   - **Tags:**
     - Key: `Project` | Value: `aws-eks-secure-network-fabric`
     - Key: `Environment` | Value: `prod`
2. Nhấp nút cam **Create NAT gateway**.
3. Quay lại danh sách NAT gateways:
   - Theo dõi cột **Status**: Trạng thái ban đầu sẽ là `Pending`.
   - Đợi khoảng 2 đến 3 phút cho đến khi cả 2 NAT Gateways chuyển sang màu xanh: **`Available`**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái sẵn sàng của 2 NAT Gateways:
```bash
# 1. Liệt kê 2 NAT Gateways kèm trạng thái và Elastic IP tương ứng
aws ec2 describe-nat-gateways --region ap-southeast-1 \
  --filter "Name=tag:Project,Values=aws-eks-secure-network-fabric" "Name=state,Values=available" \
  --query 'NatGateways[*].{Name:Tags[?Key==`Name`].Value | [0],Id:NatGatewayId,State:State,Subnet:SubnetId,PublicIP:NatGatewayAddresses[0].PublicIp,AllocationId:NatGatewayAddresses[0].AllocationId}' \
  --output table

# 2. Kiểm tra chi tiết subnet placement của từng NAT Gateway
aws ec2 describe-subnets --region ap-southeast-1 \
  --subnet-ids $(aws ec2 describe-nat-gateways --region ap-southeast-1 --filter "Name=tag:Project,Values=aws-eks-secure-network-fabric" "Name=state,Values=available" --query 'NatGateways[*].SubnetId' --output text) \
  --query 'Subnets[*].{Name:Tags[?Key==`Name`].Value | [0],AZ:AvailabilityZone,Cidr:CidrBlock}' \
  --output table
```

**Runtime Output Thực Tế:**
```text
-----------------------------------------------------------------------------------------------------------------------
|                                                 DescribeNatGateways                                                 |
+-----------------------+---------------------+--------------------+----------------+---------------+-----------------+
|     AllocationId      |         Id          |       Name         |   PublicIP     |     State     |     Subnet      |
+-----------------------+---------------------+--------------------+----------------+---------------+-----------------+
|  eipalloc-07c6475acd36813d5 | nat-02df31dd744888594 | fabric-nat-gw-1a   |  52.74.11.140  |  available    |  subnet-0262d7eefa20689ed |
|  eipalloc-01475b66f2ccd93ec | nat-048410a645ccfea3e | fabric-nat-gw-1b   |  54.151.239.60 |  available    |  subnet-0ad99949d3dcf5d10 |
+-----------------------+---------------------+--------------------+----------------+---------------+-----------------+

----------------------------------------------------------------------
|                          DescribeSubnets                           |
+-----------------+-----------------------+--------------------------+
|       AZ        |         Cidr          |          Name            |
+-----------------+-----------------------+--------------------------+
|  ap-southeast-1a|  10.80.10.0/24        |  fabric-egress-public-1a |
|  ap-southeast-1b|  10.80.11.0/24        |  fabric-egress-public-1b |
+-----------------+-----------------------+--------------------------+
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Xóa 2 NAT Gateways và giải phóng Elastic IPs:
```bash
# 1. Xóa NAT Gateways
for nat_id in $(aws ec2 describe-nat-gateways --region ap-southeast-1 --filter "Name=tag:Project,Values=aws-eks-secure-network-fabric" --query 'NatGateways[*].NatGatewayId' --output text); do
  aws ec2 delete-nat-gateway --region ap-southeast-1 --nat-gateway-id $nat_id
done

# 2. Giải phóng Elastic IPs (sau khi NAT Gateway đã ở trạng thái Deleted)
for alloc_id in $(aws ec2 describe-addresses --region ap-southeast-1 --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" --query 'Addresses[*].AllocationId' --output text); do
  aws ec2 release-address --region ap-southeast-1 --allocation-id $alloc_id
done
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/06-firewall/01-nat-gateways-active.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [x] Cả 2 Elastic IPs `fabric-nat-eip-1a` và `fabric-nat-eip-1b` được cấp phát thành công.
- [x] Cả 2 NAT Gateways `fabric-nat-gw-1a` và `fabric-nat-gw-1b` đạt trạng thái `available`.
- [x] `fabric-nat-gw-1a` đặt tại Public Subnet AZ-a và `fabric-nat-gw-1b` đặt tại Public Subnet AZ-b.
- [x] Connectivity type hiển thị `public`.
