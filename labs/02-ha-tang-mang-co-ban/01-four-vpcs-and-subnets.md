# Lab 02.01: Khởi Tạo 4 VPCs & Hệ Thống Subnets Đa AZ Tại Singapore

> **Mã bài lab:** `02.01`
> **Trạng thái:** `RUNTIME_PASS`
> **Thời gian dự kiến:** 45 phút
> **Chi phí ước tính:** $0.00 USD (Hạ tầng VPC cơ sở)
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — AZs: `ap-southeast-1a`, `ap-southeast-1b`

---

## 1. Mục Tiêu (Objective)

Đặc tả 4 Virtual Private Clouds (VPCs) chức năng cô lập và 28 subnets phân bổ đều trên 2 Availability Zones (`ap-southeast-1a`, `ap-southeast-1b`), gắn Internet Gateways có kiểm soát.

---

## 2. Tài Nguyên (Resources)

### 2.1 Virtual Private Clouds (4 VPCs)
| Tên Logical | Định Danh Runtime (Snapshot) | IPv4 CIDR | DNS Settings | Vai Trò & Ranh Giới |
| :--- | :--- | :--- | :---: | :--- |
| `fabric-edge-vpc` | `vpc-0468b18dddd1d4d2d` | `10.40.0.0/16` | Hostnames & Resolution: ON | Cụm biên tiếp nhận Internet Ingress, chứa `edge-frontend` |
| `fabric-core-vpc` | `vpc-09888cc991104c959` | `10.50.0.0/16` | Hostnames & Resolution: ON | Cụm lõi bảo mật cao, chứa `core-service`, Aurora DB, Redis |
| `fabric-inspection-vpc` | `vpc-0c94a30a1a915fc0f` | `10.70.0.0/16` | Hostnames & Resolution: ON | Vùng kiểm tra tập trung chứa GWLB và cụm Suricata EC2 |
| `fabric-egress-vpc` | `vpc-0c1479727a5e38b4c` | `10.80.0.0/16` | Hostnames & Resolution: ON | Cổng thoát Internet tập trung với Network Firewall & Dual NAT |

### 2.2 Internet Gateways (2 IGWs)
| Tên Logical | Định Danh Runtime (Snapshot) | Gắn Vào VPC | Ghi Chú An Ninh |
| :--- | :--- | :--- | :--- |
| `fabric-edge-igw` | `igw-0849ffbd341601849` | `fabric-edge-vpc` | Cho phép Public ALB Ingress nhận traffic |
| `fabric-egress-igw` | `igw-0742fe0915c3feadc` | `fabric-egress-vpc` | Cho phép NAT Gateways ra ngoài sau khi qua NFW |
| *(Không gắn IGW)* | N/A | `fabric-core-vpc` | **Cấm gắn IGW (100% Private Isolated)** |
| *(Không gắn IGW)* | N/A | `fabric-inspection-vpc` | **Cấm gắn IGW (100% Private Isolated)** |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Khóa (Key) | Giá Trị (Value) | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-*-vpc` / `fabric-*-subnet` / `fabric-*-igw` | Bắt buộc trên toàn bộ VPC, Subnet, IGW |
| `Project` | `aws-eks-secure-network-fabric` | Toàn bộ 4 VPCs, 2 IGWs, 28 Subnets |
| `Environment` | `prod` | Toàn bộ tài nguyên mạng cơ sở |
| `ManagedBy` | `manual` | Quản trị hạ tầng mạng thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Danh Sách 28 Subnets Chi Tiết (Canonical Subnet Matrix)
| VPC | Tên Subnet Logical | Định Danh Runtime (Snapshot) | CIDR Block | AZ | Loại Subnet |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Edge** | `fabric-edge-public-1a` | `subnet-04dfffbdc3e5e0c93` | `10.40.0.0/24` | 1a | Public (ALB Ingress A) |
| **Edge** | `fabric-edge-public-1b` | `subnet-0a9017b8109df0c48` | `10.40.1.0/24` | 1b | Public (ALB Ingress B) |
| **Edge** | `fabric-edge-nodes-1a` | `subnet-0e9f90d0d4e220d3a` | `10.40.8.0/22` | 1a | Private (`edge-frontend` Nodes) |
| **Edge** | `fabric-edge-nodes-1b` | `subnet-034f4fc00bfd6cd09` | `10.40.12.0/22` | 1b | Private (`edge-frontend` Nodes) |
| **Edge** | `fabric-edge-vpce-1a` | `subnet-01aa1d8c163dffca5` | `10.40.20.0/24` | 1a | Private Interface VPC Endpoints |
| **Edge** | `fabric-edge-vpce-1b` | `subnet-06c83b89e45f47650` | `10.40.21.0/24` | 1b | Private Interface VPC Endpoints |
| **Edge** | `fabric-edge-tgw-1a` | `subnet-0ee88bbf364687ec6` | `10.40.250.0/28` | 1a | Private TGW Attachment ENI |
| **Edge** | `fabric-edge-tgw-1b` | `subnet-027f9fd24d6ff94ca` | `10.40.250.16/28` | 1b | Private TGW Attachment ENI |
| **Core** | `fabric-core-nodes-1a` | `subnet-0124e28037a2e4118` | `10.50.8.0/22` | 1a | Private (`core-service` Nodes) |
| **Core** | `fabric-core-nodes-1b` | `subnet-0fe561d6217b04955` | `10.50.12.0/22` | 1b | Private (`core-service` Nodes) |
| **Core** | `fabric-core-data-1a` | `subnet-060f6827edc15bf70` | `10.50.20.0/24` | 1a | Private (Aurora Primary / Redis A) |
| **Core** | `fabric-core-data-1b` | `subnet-0d738daa01c9369d3` | `10.50.21.0/24` | 1b | Private (Aurora Replica / Redis B) |
| **Core** | `fabric-core-vpce-1a` | `subnet-053d2f1c4cf3235c6` | `10.50.30.0/24` | 1a | Private Interface VPC Endpoints |
| **Core** | `fabric-core-vpce-1b` | `subnet-0f4c9a2c5bcf93261` | `10.50.31.0/24` | 1b | Private Interface VPC Endpoints |
| **Core** | `fabric-core-tgw-1a` | `subnet-0b8fbf236704cd49f` | `10.50.250.0/28` | 1a | Private TGW Attachment ENI |
| **Core** | `fabric-core-tgw-1b` | `subnet-067ef27abb3c9fc27` | `10.50.250.16/28` | 1b | Private TGW Attachment ENI |
| **Insp** | `fabric-insp-tgw-1a` | `subnet-0e260eae20eea3ccb` | `10.70.0.0/28` | 1a | Private TGW Ingress (Appliance Mode) |
| **Insp** | `fabric-insp-tgw-1b` | `subnet-0a1481ce7d8302538` | `10.70.0.16/28` | 1b | Private TGW Ingress (Appliance Mode) |
| **Insp** | `fabric-insp-gwlbe-1a` | `subnet-0aebf9d83c8118058` | `10.70.1.0/28` | 1a | Private GWLB Endpoint |
| **Insp** | `fabric-insp-gwlbe-1b` | `subnet-0a1a561fe99bcc9fd` | `10.70.1.16/28` | 1b | Private GWLB Endpoint |
| **Insp** | `fabric-insp-fw-1a` | `subnet-0b743a1b6492b62ce` | `10.70.10.0/24` | 1a | Private Suricata EC2 Instance A |
| **Insp** | `fabric-insp-fw-1b` | `subnet-00621165b37f9a04e` | `10.70.11.0/24` | 1b | Private Suricata EC2 Instance B |
| **Egress** | `fabric-egress-tgw-1a` | `subnet-0a9b70d43770f1e86` | `10.80.0.0/28` | 1a | Private TGW Attachment Ingress |
| **Egress** | `fabric-egress-tgw-1b` | `subnet-0b0653845a52c4f75` | `10.80.0.16/28` | 1b | Private TGW Attachment Ingress |
| **Egress** | `fabric-egress-fw-1a` | `subnet-0c7142131794aa34c` | `10.80.1.0/28` | 1a | Private Network Firewall Endpoint |
| **Egress** | `fabric-egress-fw-1b` | `subnet-05ce922d28724c2f9` | `10.80.1.16/28` | 1b | Private Network Firewall Endpoint |
| **Egress** | `fabric-egress-public-1a` | `subnet-0262d7eefa20689ed` | `10.80.10.0/24` | 1a | Public (NAT Gateway A + IGW) |
| **Egress** | `fabric-egress-public-1b` | `subnet-0ad99949d3dcf5d10` | `10.80.11.0/24` | 1b | Public (NAT Gateway B + IGW) |

---

## 5. Phụ Thuộc (Dependencies)

* [Lab 01.02](../01-thiet-ke-threat-model/02-cidr-ip-allocation-plan.md): Quy hoạch dải mạng Canonical IP Plan.

---

## 6. Kiểm Tra Đạt (Verification)

| Hạng Mục | Tiêu Chí Kiểm Tra | Kỳ Vọng Đạt |
| :--- | :--- | :--- |
| **Trạng Thái VPC** | 4 VPCs tại Singapore | `State: available` trên cả 4 VPCs |
| **DNS Attributes** | `enableDnsHostnames` & `enableDnsSupport` | Bật `true` trên cả 4 VPCs |
| **Gắn IGW Có Kiểm Soát** | 2 IGWs gắn vào Edge VPC & Egress VPC | Đúng 2 VPCs có IGW, Core & Insp tuyệt đối không có IGW |
| **Đối Soát Subnets** | So khớp CIDR và AZ của 28 subnets | Khớp 100% với Canonical Subnet Matrix |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

> [!WARNING]
> Tuyệt đối không gắn Internet Gateway vào `fabric-core-vpc` hoặc `fabric-inspection-vpc`. Mọi lưu lượng ra/vào phải đi qua Transit Gateway và hệ thống tường lửa.

### Kế Hoạch Khôi Phục (Rollback Plan)
```bash
aws ec2 detach-internet-gateway --internet-gateway-id igw-0849ffbd341601849 --vpc-id vpc-0468b18dddd1d4d2d --region ap-southeast-1
aws ec2 detach-internet-gateway --internet-gateway-id igw-0742fe0915c3feadc --vpc-id vpc-0c1479727a5e38b4c --region ap-southeast-1
```
