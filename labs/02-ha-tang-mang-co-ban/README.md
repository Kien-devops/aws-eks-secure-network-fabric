# Module 02: Hạ Tầng Mạng Cơ Bản (Foundation Network & Transit Gateway)

Module này cung cấp tài liệu hướng dẫn thực hành chi tiết từng bước xây dựng nền tảng hạ tầng mạng đa VPC (Multi-VPC Secure Network Fabric) trên AWS Region Singapore (`ap-southeast-1`), kết nối thông qua AWS Transit Gateway (TGW) theo mô hình phân tách miền định tuyến (Route Domain Segmentation) và bảo đảm tính đối xứng qua Appliance Mode.

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
                         /  (All E-W / N-S via)  \
                        v                         v
+-------------------------------------------------------------------------+
| VPC Inspection — 10.70.0.0/16 [ap-southeast-1a / ap-southeast-1b]       |
| - TGW Subnets: Attachment ENIs (Appliance Mode = ENABLED)               |
| - GWLBe Subnets: Zonal VPC Endpoints (10.70.1.0/28, 10.70.1.16/28)      |
| - Firewall Subnets: Suricata EC2 (GENEVE 6081) (10.70.10.0/24, 11.0/24) |
+-------------------------------------------------------------------------+
                        \                         ^
                         \  (Inspected 0.0.0.0/0) / (Inspected Return)
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
                     (0.0.0.0/0 via Inspection)
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

## 2. Danh Sách 6 Bài Lab Chi Tiết

| Mã Lab | Tên Bài Lab & Nội Dung Trọng Tâm | Trạng Thái | File Hướng Dẫn |
|---|---|:---:|---|
| **02.01** | **Khởi Tạo 4 VPCs & Subnets Đa AZ:** 4 VPCs độc lập, 28 subnets chuẩn hóa theo AZ A/B, bật DNS hostnames & DNS resolution. | `RUNTIME_PASS` | [01-four-vpcs-and-subnets.md](01-four-vpcs-and-subnets.md) |
| **02.02** | **Cấu Hình AWS Transit Gateway (TGW):** ASN 64512, tắt mặc định Route Propagation & Association (triết lý fail-closed). | `RUNTIME_PASS` | [02-transit-gateway-setup.md](02-transit-gateway-setup.md) |
| **02.03** | **TGW Attachments & Appliance Mode:** 4 attachments, bật `ApplianceModeSupport = enable` trên Inspection & Egress VPCs, 4 TGW RTBs. | `RUNTIME_PASS` | [03-tgw-route-tables-and-attachments.md](03-tgw-route-tables-and-attachments.md) |
| **02.04** | **Bảng Định Tuyến Subnet:** Chaining các tuyến đường từ VPC private qua TGW, cô lập hoàn toàn Subnet dữ liệu Core. | `RUNTIME_PASS` | [04-subnet-route-tables-chaining.md](04-subnet-route-tables-chaining.md) |
| **02.05** | **Centralized VPC Flow Logs:** Tập trung hóa toàn bộ nhật ký mạng của 4 VPCs về CloudWatch Logs (chu kỳ 1 phút, retention 7 ngày). | `RUNTIME_PASS` | [05-vpc-flow-logs-cloudwatch.md](05-vpc-flow-logs-cloudwatch.md) |
| **02.06** | **Private VPC Endpoints:** S3 Gateway Endpoint, ECR API/DKR, STS, CloudWatch Logs, EC2, SQS endpoints phục vụ cụm Private EKS. | `RUNTIME_PASS` | [06-private-vpc-endpoints.md](06-private-vpc-endpoints.md) |

---

## 3. Thứ Tự Thực Thi & Kiểm Tra (Execution Protocol)
1. Chạy theo đúng trình tự từ `02.01` đến `02.06`.
2. Mọi thao tác kiểm tra hoặc khởi tạo trên AWS Cloud sử dụng trực tiếp MCP `aws-api-mcp/call_aws` với cờ `--region ap-southeast-1`.
3. Bằng chứng kiểm thử xuất ra lưu vào thư mục chuẩn `evidence/02-network/`.
4. Che giấu toàn bộ Account ID thành `123456789012` hoặc `***` theo tiêu chuẩn Zero Fake Data & Sanitization.
