# 06.01 — Đặc Tả NAT Gateways & Elastic IPs Đa AZ Tại Public Subnets

> **Mã bài lab:** `06.01`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore) — Subnets: `fabric-egress-public-1a`, `fabric-egress-public-1b`
> **File bằng chứng:** `evidence/06-firewall/01-nat-gateways-active.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả hai cổng NAT Gateway công khai độc lập kèm địa chỉ Elastic IP tĩnh triển khai tại hai Public Subnets của Centralized Egress VPC nhằm cung cấp dịch vụ dịch địa chỉ mạng ra Internet cho cụm EKS với tính sẵn sàng cao (Multi-AZ HA) và cô lập vùng lỗi.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Vị Trí / Subnet / AZ | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-nat-eip-1a` | `AWS::EC2::EIP` | Regional (`ap-southeast-1`) | `eipalloc-07c6475acd36813d5` (IP: `52.74.11.140`) |
| `fabric-nat-eip-1b` | `AWS::EC2::EIP` | Regional (`ap-southeast-1`) | `eipalloc-01475b66f2ccd93ec` (IP: `54.151.239.60`) |
| `fabric-nat-gw-1a` | `AWS::EC2::NatGateway` | `fabric-egress-public-1a` (`ap-southeast-1a`) | `nat-02df31dd744888594` (Subnet: `subnet-0262d7eefa20689ed`) |
| `fabric-nat-gw-1b` | `AWS::EC2::NatGateway` | `fabric-egress-public-1b` (`ap-southeast-1b`) | `nat-048410a645ccfea3e` (Subnet: `subnet-0ad99949d3dcf5d10`) |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-nat-eip-*` / `fabric-nat-gw-*` | Elastic IPs và NAT Gateways |
| `Project` | `aws-eks-secure-network-fabric` | Elastic IPs và NAT Gateways |
| `Environment` | `prod` | Elastic IPs và NAT Gateways |
| `ManagedBy` | `manual` | Quản trị cổng NAT thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Cấu Hình Elastic IPs

- **Domain:** `vpc`
- **Network Border Group:** `ap-southeast-1`
- **Public IPv4 Pool:** `amazon`

### 4.2 Cấu Hình Kỹ Thuật NAT Gateways

| Thuộc Tính | NAT Gateway 1a (`fabric-nat-gw-1a`) | NAT Gateway 1b (`fabric-nat-gw-1b`) | Lý Do Thiết Kế |
| :--- | :--- | :--- | :--- |
| **Connectivity Type** | `public` | `public` | Kết nối trực tiếp với Internet Gateway (`fabric-egress-igw`). |
| **Subnet Placement** | `fabric-egress-public-1a` (`10.80.10.0/24`) | `fabric-egress-public-1b` (`10.80.11.0/24`) | Bảo đảm độc lập theo từng AZ, không cross-zone. |
| **Associated EIP** | `eipalloc-07c6475acd36813d5` | `eipalloc-01475b66f2ccd93ec` | Cung cấp địa chỉ IP nguồn tĩnh ra Internet. |

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `02.01`: Subnets `fabric-egress-public-1a/b` và Internet Gateway `fabric-egress-igw`.
- Phụ thuộc vào `02.04`: Bảng định tuyến `fabric-egress-public-rt` trỏ `0.0.0.0/0` ra `fabric-egress-igw`.
- Là next-hop đích bắt buộc cho các bảng định tuyến firewall subnet sau khi kiểm duyệt tại `06.04`.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng thái 2 NAT Gateways** | `aws ec2 describe-nat-gateways --filter "Name=tag:Project,Values=aws-eks-secure-network-fabric"` | Cả 2 bản ghi đều có `State: available`. |
| **Xác thực Subnet Binding** | Kiểm tra trường `SubnetId` của từng NAT Gateway | `fabric-nat-gw-1a` gắn vào `subnet-0262d7eefa20689ed`; `fabric-nat-gw-1b` gắn vào `subnet-0ad99949d3dcf5d10`. |
| **Public IP Mapping** | Kiểm tra trường `NatGatewayAddresses[0].PublicIp` | Hiển thị chính xác 2 IP tĩnh `52.74.11.140` và `54.151.239.60`. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo chi phí:** Mỗi NAT Gateway tính phí ~$0.045 USD/giờ ($2.16 USD/ngày cho 2 NAT Gateways) dù không có lưu lượng. Cần xóa khi dừng lab.
- **Quy trình Rollback:**
  ```bash
  # Xóa 2 NAT Gateways
  aws ec2 delete-nat-gateway --region ap-southeast-1 --nat-gateway-id nat-02df31dd744888594
  aws ec2 delete-nat-gateway --region ap-southeast-1 --nat-gateway-id nat-048410a645ccfea3e

  # Chờ NAT Gateways chuyển sang trạng thái deleted rồi giải phóng EIPs
  aws ec2 release-address --region ap-southeast-1 --allocation-id eipalloc-07c6475acd36813d5
  aws ec2 release-address --region ap-southeast-1 --allocation-id eipalloc-01475b66f2ccd93ec
  ```
