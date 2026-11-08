# Lab 01.02: Kế Hoạch Phân Bổ Dải Mạng (IP Plan) & Quy Hoạch Subnets

> **Mã bài lab:** `01.02`
> **Trạng thái:** `RUNTIME_PASS`
> **Thời gian dự kiến:** 30 phút
> **Chi phí ước tính:** $0.00 USD (Thiết kế kiến trúc)
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — AZs: `ap-southeast-1a`, `ap-southeast-1b`

---

## 1. Mục Tiêu (Objective)

Quy hoạch dải mạng RFC 1918 không chồng lấn cho 4 VPC chức năng và 28 subnets phân bổ đối xứng đa vùng (Multi-AZ), đảm bảo đáp ứng dung lượng IP cho EKS Pods, Interface Endpoints và Transit Gateway Dedicated Attachments.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | VPC / Subnet / AZ | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-edge-vpc` | `AWS::EC2::VPC` | `10.40.0.0/16` (8 Subnets) | `vpc-0468b18dddd1d4d2d` |
| `fabric-core-vpc` | `AWS::EC2::VPC` | `10.50.0.0/16` (8 Subnets) | `vpc-09888cc991104c959` |
| `fabric-inspection-vpc` | `AWS::EC2::VPC` | `10.70.0.0/16` (6 Subnets) | `vpc-0c94a30a1a915fc0f` |
| `fabric-egress-vpc` | `AWS::EC2::VPC` | `10.80.0.0/16` (6 Subnets) | `vpc-0c1479727a5e38b4c` |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế (có thể thay đổi khi tái tạo hạ tầng); Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Khóa (Key) | Giá Trị (Value) | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-*-vpc` / `fabric-*-subnet` | Toàn bộ VPC và Subnet tạo mới |
| `Project` | `aws-eks-secure-network-fabric` | Bắt buộc trên toàn bộ tài nguyên mạng |
| `Environment` | `prod` | Phân vùng môi trường chính thức |
| `ManagedBy` | `manual` | Quản lý triển khai thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### Bảng Phân Bổ Subnet Chuẩn Hóa 4 VPCs (Canonical IP Plan)

| VPC | Tên Subnet Logical | Dải Mạng (CIDR Block) | AZ | Mục Đích Kỹ Thuật |
| :--- | :--- | :--- | :--- | :--- |
| **Edge** | `fabric-edge-public-1a` / `1b` | `10.40.0.0/24`, `10.40.1.0/24` | 1a / 1b | Public ALB Ingress (251 IPs/AZ) |
| **Edge** | `fabric-edge-nodes-1a` / `1b` | `10.40.8.0/22`, `10.40.12.0/22` | 1a / 1b | EKS Nodes & `edge-frontend` Pods (1,019 IPs/AZ) |
| **Edge** | `fabric-edge-vpce-1a` / `1b` | `10.40.20.0/24`, `10.40.21.0/24` | 1a / 1b | Interface VPC Endpoints |
| **Edge** | `fabric-edge-tgw-1a` / `1b` | `10.40.250.0/28`, `10.40.250.16/28` | 1a / 1b | TGW Dedicated Attachment ENIs |
| **Core** | `fabric-core-nodes-1a` / `1b` | `10.50.8.0/22`, `10.50.12.0/22` | 1a / 1b | EKS Nodes & `core-service` Pods (1,019 IPs/AZ) |
| **Core** | `fabric-core-data-1a` / `1b` | `10.50.20.0/24`, `10.50.21.0/24` | 1a / 1b | Aurora PostgreSQL & ElastiCache Redis |
| **Core** | `fabric-core-vpce-1a` / `1b` | `10.50.30.0/24`, `10.50.31.0/24` | 1a / 1b | Private Interface VPC Endpoints |
| **Core** | `fabric-core-tgw-1a` / `1b` | `10.50.250.0/28`, `10.50.250.16/28` | 1a / 1b | TGW Dedicated Attachment ENIs |
| **Insp** | `fabric-insp-tgw-1a` / `1b` | `10.70.0.0/28`, `10.70.0.16/28` | 1a / 1b | TGW Ingress (Appliance Mode = Enabled) |
| **Insp** | `fabric-insp-gwlbe-1a` / `1b` | `10.70.1.0/28`, `10.70.1.16/28` | 1a / 1b | Gateway Load Balancer Zonal Endpoints |
| **Insp** | `fabric-insp-fw-1a` / `1b` | `10.70.10.0/24`, `10.70.11.0/24` | 1a / 1b | Cụm Suricata EC2 IDS/IPS (GENEVE 6081) |
| **Egress** | `fabric-egress-tgw-1a` / `1b` | `10.80.0.0/28`, `10.80.0.16/28` | 1a / 1b | TGW Egress Ingress ENIs |
| **Egress** | `fabric-egress-fw-1a` / `1b` | `10.80.1.0/28`, `10.80.1.16/28` | 1a / 1b | AWS Network Firewall Zonal Endpoints |
| **Egress** | `fabric-egress-public-1a` / `1b` | `10.80.10.0/24`, `10.80.11.0/24` | 1a / 1b | Dual NAT Gateways & Internet Gateway |

---

## 5. Phụ Thuộc (Dependencies)

* [Lab 01.01](01-stride-threat-analysis.md): Mô hình mối đe dọa STRIDE và yêu cầu cô lập vùng mạng.

---

## 6. Kiểm Tra Đạt (Verification)

| Hạng Mục | Tiêu Chí Kiểm Tra | Kỳ Vọng Đạt |
| :--- | :--- | :--- |
| **Non-overlapping CIDR** | So khớp 4 dải mạng VPC chính | 100% không chồng lấn (`10.40/16`, `10.50/16`, `10.70/16`, `10.80/16`) |
| **Dung Lượng Subnet EKS** | Dải `/22` cho Node subnets | Đủ 1,019 IPs khả dụng/AZ cho Pod density |
| **Dedicated TGW Subnets** | Dải `/28` riêng biệt cho TGW | Đúng 11 IPs khả dụng phục vụ ENI attachment |
| **Đối Soát Runtime** | Kiểm tra `evidence/01-network-topology/subnets.json` | 16 Subnets runtime khớp hoàn toàn canonical IP plan |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

> [!WARNING]
> CIDR Block của VPC sau khi tạo không thể thu nhỏ. Mọi sai lệch subnet phải được rà soát đối chiếu trước khi khởi tạo route tables hoặc triển khai workloads.

### Kế Hoạch Khôi Phục (Rollback Plan)
Nếu phát hiện sai lệch CIDR trong quá trình cấu hình, xóa subnet chưa gắn ENI và khởi tạo lại theo đúng bảng phân bổ chuẩn hóa trên.
