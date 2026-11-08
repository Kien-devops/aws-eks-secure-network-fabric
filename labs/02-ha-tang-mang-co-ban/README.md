# Module 02: Hạ Tầng Mạng Cơ Bản (Foundation Network & Transit Gateway)

Module này cung cấp các đặc tả tài nguyên hạ tầng mạng đa VPC (Multi-VPC Secure Network Fabric) trên AWS Region Singapore (`ap-southeast-1`), kết nối thông qua AWS Transit Gateway (TGW) theo mô hình phân tách miền định tuyến (Route Domain Segmentation) và bảo đảm tính đối xứng qua Appliance Mode.

---

## 1. Sơ Đồ Kiến Trúc Mạng 4 VPCs

```text
                                Internet
                                   |
                                Route 53
                                   |
                             ALB + AWS WAF
                                   |
+-------------------------------------------------------------------------+
| VPC Edge EKS — 10.40.0.0/16 [ap-southeast-1a / ap-southeast-1b]         |
| - Public Subnets: ALB Ingress (10.40.0.0/24, 10.40.1.0/24)              |
| - Private Subnets: Edge Nodes EKS (10.40.8.0/22, 10.40.12.0/22)         |
| - VPCE Subnets: Interface Endpoints (10.40.20.0/24, 10.40.21.0/24)      |
| - TGW Subnets: Attachment ENIs (10.40.250.0/28, 10.40.250.16/28)        |
+-------------------------------------------------------------------------+
                                   |
                         [ Transit Gateway (TGW) ]
                          /                     \
                         /  (East-West via)  \
                        v                         v
+-------------------------------------------------------------------------+
| VPC Inspection — 10.70.0.0/16 [ap-southeast-1a / ap-southeast-1b]       |
| - TGW Subnets: Attachment ENIs (Appliance Mode = ENABLED)               |
| - GWLBe Subnets: Zonal VPC Endpoints (10.70.1.0/28, 10.70.1.16/28)      |
| - Firewall Subnets: Suricata EC2 (GENEVE 6081) (10.70.10.0/24, 11.0/24) |
+-------------------------------------------------------------------------+
                        \                         ^
                         \  (East-West only) / (Inspected Return)
                          v                      /
                         [ Transit Gateway (TGW) ]
                                   |
+-------------------------------------------------------------------------+
| VPC Core EKS — 10.50.0.0/16 [ap-southeast-1a / ap-southeast-1b]         |
| - Private Subnets: Core Nodes EKS (10.50.8.0/22, 10.50.12.0/22)         |
| - Data Subnets: Aurora PostgreSQL & Redis (10.50.20.0/24, 21.0/24)      |
| - VPCE Subnets: Interface Endpoints (10.50.30.0/24, 10.50.31.0/24)      |
| - TGW Subnets: Attachment ENIs (10.50.250.0/28, 10.50.250.16/28)        |
+-------------------------------------------------------------------------+
                                   |
                     (0.0.0.0/0 via Egress)
                                   v
+-------------------------------------------------------------------------+
| VPC Centralized Egress — 10.80.0.0/16 [ap-southeast-1a / 1b]           |
| - TGW Subnets: Attachment ENIs (10.80.0.0/28, 10.80.0.16/28)            |
| - Firewall Subnets: Network Firewall Endpoints (10.80.1.0/28, 1.16/28)  |
| - Public Subnets: NAT Gateways A & B + IGW (10.80.10.0/24, 11.0/24)     |
+-------------------------------------------------------------------------+
                                   |
                                Internet
```

---

## 2. Thứ Tự Phụ Thuộc (Dependency Tree)

```text
02.01 (4 VPCs & 28 Subnets)
  │
  ├──> 02.02 (Transit Gateway - ASN 64512)
  │      │
  │      └──> 02.03 (TGW Attachments & Appliance Mode)
  │             │
  │             └──> 02.04 (Subnet Route Tables & Chaining)
  │
  ├──> 02.05 (Centralized VPC Flow Logs -> CloudWatch Logs)
  │
  └──> 02.06 (Private VPC Endpoints: 2 S3 GW + 13 Interface)
```

---

## 3. Danh Mục Tài Nguyên (Resource Catalog)

| Tài Nguyên | Loại Resource | Số Lượng | Ghi Chú Kỹ Thuật |
| :--- | :--- | :---: | :--- |
| **VPC** | `AWS::EC2::VPC` | 4 | `edge` (10.40/16), `core` (10.50/16), `inspection` (10.70/16), `egress` (10.80/16) |
| **Subnets** | `AWS::EC2::Subnet` | 28 | Phân bổ cân bằng trên 2 AZs (`1a` và `1b`) |
| **Internet Gateway** | `AWS::EC2::InternetGateway` | 2 | Gắn tại `fabric-edge-vpc` và `fabric-egress-vpc` |
| **Transit Gateway** | `AWS::EC2::TransitGateway` | 1 | ASN 64512, tắt auto-propagate & auto-associate |
| **TGW Attachments** | `AWS::EC2::TransitGatewayVpcAttachment` | 4 | Gắn qua các `/28` TGW subnets, bật Appliance Mode tại Inspection & Egress |
| **TGW Route Tables** | `AWS::EC2::TransitGatewayRouteTable` | 4 | `edge-rt`, `core-rt`, `inspection-rt`, `egress-rt` |
| **VPC Route Tables** | `AWS::EC2::RouteTable` | 16 | Định tuyến cục bộ, TGW default hop, và cô lập Data subnets |
| **VPC Flow Logs** | `AWS::EC2::FlowLog` | 4 | Nạp vào Log Group `/aws/vpc/fabric-centralized-flow-logs` |
| **VPC Endpoints** | `AWS::EC2::VPCEndpoint` | 15 | 2 S3 Gateway + 13 Interface (Private DNS = true) |

---

## 4. Danh Sách 6 Bài Lab Đặc Tả Chi Tiết

| Mã Lab | Tên Đặc Tả & Nội Dung Trọng Tâm | Trạng Thái | File Đặc Tả |
|---|---|:---:|---|
| **02.01** | **Khởi Tạo 4 VPCs & Subnets Đa AZ:** 4 VPCs độc lập, 28 subnets chuẩn hóa theo AZ A/B, bật DNS hostnames & DNS resolution. | `RUNTIME_PASS` | [01-four-vpcs-and-subnets.md](01-four-vpcs-and-subnets.md) |
| **02.02** | **Cấu Hình AWS Transit Gateway (TGW):** ASN 64512, tắt mặc định Route Propagation & Association (triết lý fail-closed). | `RUNTIME_PASS` | [02-transit-gateway-setup.md](02-transit-gateway-setup.md) |
| **02.03** | **TGW Attachments & Appliance Mode:** 4 attachments, bật `ApplianceModeSupport = enable` trên Inspection & Egress VPCs, 4 TGW RTBs. | `RUNTIME_PASS` | [03-tgw-route-tables-and-attachments.md](03-tgw-route-tables-and-attachments.md) |
| **02.04** | **Bảng Định Tuyến Subnet:** Chaining các tuyến đường từ VPC private qua TGW, cô lập hoàn toàn Subnet dữ liệu Core. | `RUNTIME_PASS` | [04-subnet-route-tables-chaining.md](04-subnet-route-tables-chaining.md) |
| **02.05** | **Centralized VPC Flow Logs:** Tập trung hóa toàn bộ nhật ký mạng của 4 VPCs về CloudWatch Logs (chu kỳ 1 phút, retention 7 ngày). | `RUNTIME_PASS` | [05-vpc-flow-logs-cloudwatch.md](05-vpc-flow-logs-cloudwatch.md) |
| **02.06** | **Private VPC Endpoints:** S3 Gateway Endpoint, ECR API/DKR, STS, CloudWatch Logs, EC2, SQS endpoints phục vụ cụm Private EKS. | `RUNTIME_PASS` | [06-private-vpc-endpoints.md](06-private-vpc-endpoints.md) |
