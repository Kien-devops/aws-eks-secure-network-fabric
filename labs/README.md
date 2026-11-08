# Hệ Thống Đặc Tả Tài Nguyên Hạ Tầng: AWS EKS Secure Network Fabric

Tài liệu đặc tả kiến trúc và tài nguyên hạ tầng kỹ thuật (Enterprise Resource Specifications) phục vụ xây dựng, kiểm thử và vận hành hệ thống **AWS Advanced Networking & Cloud-Native Security Fabric** trên nền tảng Amazon EKS đa VPC.

> [!IMPORTANT]
> **Tôn Chỉ Thiết Kế & Chuẩn Mực Vận Hành (Core Principles):**
> 1. **Zero Fake Data:** Mọi kết luận kỹ thuật, bảng log, số đo latency và packet drop phải trích xuất trực tiếp từ runtime evidence có dấu thời gian ISO 8601 UTC thực tế.
> 2. **Đặc Tả Tài Nguyên Ngắn Gọn (Declarative Resource Spec):** Toàn bộ bài lab được cấu trúc theo 7 mục chuẩn hóa (Mục tiêu, Tài nguyên, Thẻ định danh, Cấu hình, Phụ thuộc, Kiểm tra đạt, An toàn & Rollback), loại bỏ hoàn toàn các hướng dẫn click-through thủ công trên Console.
> 3. **Region Chuẩn:** **Singapore (`ap-southeast-1`)** — Phân bổ đối xứng trên 2 Availability Zones (`ap-southeast-1a`, `ap-southeast-1b`).
> 4. **Bảo Mật Tuyệt Đối (Sanitization & Zero Secret Leak):** Che giấu 100% AWS Account ID thực tế (thay bằng `123456789012`), cấm lưu trữ Access Keys, Tokens, Passwords cơ sở dữ liệu và Private Keys.
> 5. **Kiến Trúc Microservices Chuẩn Hóa:** 2 dịch vụ độc lập: `edge-frontend` (Edge VPC) và `core-service` (Core VPC, tích hợp SQS consumer và kết nối Aurora DB/Redis).

---

## 1. Bản Đồ Thứ Tự Phụ Thuộc (Execution DAG & Dependency Flow)

```text
[00 Chuẩn Bị & Inventory]        --> Kiểm kê AWS qua MCP, Region ap-southeast-1, FinOps Budget ($50)
       │
       ▼
[01 Thiết Kế & Threat Model]     --> Phân tích STRIDE, CIDR IP Plan, TGW Routing Matrix & Hop Tables
       │
       ▼
[02 Hạ Tầng Mạng Cơ Bản]         --> 4 VPCs, Subnets theo AZ, TGW (Appliance Mode), Fail-closed routes, VPC Flow Logs
       │
       ├────────────────────────────────────┐
       │                                    │
       ▼                                    ▼
[05 GWLB & Suricata IDS/IPS]        [06 Centralized Egress Firewall]
(Bootstrap appliance, GWLB, 2 zonal  (AWS Network Firewall A/B,
 GWLBe, đối xứng luồng GENEVE 6081)  NAT Gateways, Domain allowlist)
       │                                    │
       └─────────────────┬──────────────────┘
                         │
                         ▼
              [02.06 / 06.04 Prerequisites] --> Private VPC Endpoints & Egress Routing sẵn sàng
                         │
                         ▼
              [03 Cụm EKS Kép (Dual EKS)]   --> Dual EKS 1.37, Pod Identity, Cilium/Calico NetworkPolicy
                         │
                         ▼
              [04 Phân Bổ Workloads]        --> Deploy edge-frontend, core-service, SQS, Aurora DB & Redis
                         │
                         ▼
              [05.04 East-West Inspection]  --> Nghiệm thu kiểm tra an ninh luồng East-West qua GWLB
                         │
                         ▼
              [07 Edge Ingress & AWS WAF]   --> Public Route 53, ACM TLS, Internet-facing ALB, WAF v2 Count-to-Block
                         │
                         ▼
              [08 CI/CD & DevSecOps]        --> Terraform Checkov, Trivy scan, SBOM Syft, Cosign, GitOps Digest Pinning
                         │
                         ▼
              [09 Toàn Diện Observability]  --> Tập trung VPC Flow Logs, Suricata EVE, CW Insights, Reachability Analyzer
                         │
                         ▼
              [10 GameDay Kịch Bản Sự Cố]   --> Route leak, Asymmetric flow drop, Appliance failover, IPS drop, NAT fail
                         │
                         ▼
              [11 Bằng Chứng & Báo Cáo]     --> Tổng hợp raw evidence, sanitize audit, post-mortem, FinOps cost report
                         │
                         ▼
              [12 Dọn Dẹp FinOps Hoàn Toàn] --> Reverse 6-tier teardown, zero residual verification ($0.00 spend)
```

---

## 2. Kiến Trúc Mạng Chi Tiết (Architecture Blueprint)

```text
                                  Internet
                                     │
                               Route 53 Public
                                     │
                             ALB + AWS WAF v2
                                     │
    +-----------------------------------------------------------------+
    | VPC Edge EKS — 10.40.0.0/16 (ap-southeast-1a/b)                 |
    | - Public Subnets: ALB Ingress (10.40.0.0/24, 10.40.1.0/24)      |
    | - Private Subnets: Edge Nodes EKS 1.37 (10.40.8.0/22, 12.0/22)  |
    |   Workload: edge-frontend                                       |
    | - VPC Endpoints: ECR, S3, STS, Logs, EC2, eks-auth (10.40.20-21)|
    | - TGW Subnets: Attachment ENIs (10.40.250.0/28, 250.16/28)      |
    +-----------------------------------------------------------------+
                                     │
                          [ Transit Gateway (TGW) ]
                                     │
    +-----------------------------------------------------------------+
    | VPC Inspection — 10.70.0.0/16 (ap-southeast-1a/b)               |
    | - TGW Subnets: TGW Attachment (Appliance Mode = ENABLED)        |
    | - GWLBe Subnets: Zonal VPC Endpoints (10.70.1.0/28, 10.70.1.16/28)|
    | - Firewall Subnets: Suricata EC2 Instances (GENEVE 6081)        |
    |   <---> Gateway Load Balancer (GWLB)                            |
    +-----------------------------------------------------------------+
                                     │
                          [ Transit Gateway (TGW) ]
                                     │
    +-----------------------------------------------------------------+
    | VPC Core EKS — 10.50.0.0/16 (ap-southeast-1a/b)                 |
    | - Private Subnets: Core Nodes EKS 1.37 (10.50.8.0/22, 12.0/22)  |
    |   Workload: core-service (Internal API + SQS Consumer)          |
    | - VPC Endpoints: ECR, S3, STS, Logs, EC2, SQS, eks-auth (30-31) |
    | - Data Subnets: Aurora DB, Redis Cache (10.50.20.0/24, 21.0/24) |
    | - TGW Subnets: Attachment ENIs (10.50.250.0/28, 250.16/28)      |
    +-----------------------------------------------------------------+
                                     │
                       (0.0.0.0/0 qua TGW -> Egress)
                                     │
    +-----------------------------------------------------------------+
    | VPC Centralized Egress — 10.80.0.0/16 (ap-southeast-1a/b)       |
    | - TGW Subnets: TGW Attachment (10.80.0.0/28, 10.80.0.16/28)     |
    | - Firewall Subnets: AWS Network Firewall Endpoints (10.80.1.0/28) |
    | - Public Subnets: NAT Gateway A/B + IGW (10.80.10.0/24, 11.0/24)|
    +-----------------------------------------------------------------+
                                     │
                                  Internet
```

---

## 3. Ma Trận Miền Định Tuyến TGW (Routing Matrix)

> **Quy tắc bắt buộc:**
> 1. Tắt hoàn toàn `Default Route Table Association` và `Default Route Table Propagation` trên Transit Gateway.
> 2. Bật `ApplianceModeSupport = enable` trên cả **Inspection Attachment** và **Egress Attachment** để bảo đảm tính đối xứng của luồng gói tin (Symmetric stateful routing).

| TGW Route Table | Associated VPC Attachment | Routes Cấu Hình | Mục Đích Luồng Traffic |
| :--- | :--- | :--- | :--- |
| **`fabric-tgw-edge-rt`** | Edge VPC | - `10.50.0.0/16` -> Inspection Attachment<br>- `0.0.0.0/0` -> Egress Attachment | Traffic sang Core qua Inspection; traffic Internet qua Egress |
| **`fabric-tgw-core-rt`** | Core VPC | - `10.40.0.0/16` -> Inspection Attachment<br>- `0.0.0.0/0` -> Egress Attachment | Traffic sang Edge qua Inspection; traffic Internet qua Egress |
| **`fabric-tgw-inspection-rt`**| Inspection VPC | - `10.40.0.0/16` -> Edge Attachment<br>- `10.50.0.0/16` -> Core Attachment | Chuyển traffic East-West đã kiểm duyệt tới đúng Spoke VPC |
| **`fabric-tgw-egress-rt`** | Egress VPC | - `10.40.0.0/16` -> Edge Attachment<br>- `10.50.0.0/16` -> Core Attachment | Traffic phản hồi từ Internet về đúng Spoke, không qua GWLB |

---

## 4. Kế Hoạch Phân Bổ Dải Mạng (IP Plan)

| VPC | CIDR Block | Phân Bổ Subnet Chi Tiết |
| :--- | :--- | :--- |
| **Edge EKS** | `10.40.0.0/16` | Public ALB: `10.40.0.0/24`, `10.40.1.0/24`<br>Private Node: `10.40.8.0/22`, `10.40.12.0/22`<br>Private VPCE: `10.40.20.0/24`, `10.40.21.0/24`<br>TGW Attachment: `10.40.250.0/28`, `10.40.250.16/28` |
| **Core EKS** | `10.50.0.0/16` | Private Node: `10.50.8.0/22`, `10.50.12.0/22`<br>Private VPCE: `10.50.30.0/24`, `10.50.31.0/24`<br>Data Subnet (DB/Cache): `10.50.20.0/24`, `10.50.21.0/24`<br>TGW Attachment: `10.50.250.0/28`, `10.50.250.16/28` |
| **Inspection** | `10.70.0.0/16` | TGW Subnet: `10.70.0.0/28`, `10.70.0.16/28`<br>GWLBe Subnet: `10.70.1.0/28`, `10.70.1.16/28`<br>Suricata EC2 Subnet: `10.70.10.0/24`, `10.70.11.0/24` |
| **Centralized Egress** | `10.80.0.0/16` | TGW Subnet: `10.80.0.0/28`, `10.80.0.16/28`<br>Firewall Endpoint Subnet: `10.80.1.0/28`, `10.80.1.16/28`<br>Public Subnet (NAT/IGW): `10.80.10.0/24`, `10.80.11.0/24` |

---

## 5. Danh Mục 13 Module Đặc Tả Tài Nguyên

| Module | Tên Module & Nội Dung Trọng Tâm | Trạng Thái | File Danh Mục |
| :---: | :--- | :---: | :--- |
| **00** | **Chuẩn Bị & Inventory:** Read-only AWS Inventory qua MCP, Region validation, FinOps Budget ($50). | `RUNTIME_PASS` | [00-chuan-bi-inventory/README.md](00-chuan-bi-inventory/README.md) |
| **01** | **Thiết Kế & Threat Model:** STRIDE Threat Analysis, CIDR non-overlapping plan, TGW Hop tables. | `RUNTIME_PASS` | [01-thiet-ke-threat-model/README.md](01-thiet-ke-threat-model/README.md) |
| **02** | **Hạ Tầng Mạng Cơ Bản:** Khởi tạo 4 VPCs, Subnets theo AZ, Transit Gateway, Route Domains, Flow Logs. | `RUNTIME_PASS` | [02-ha-tang-mang-co-ban/README.md](02-ha-tang-mang-co-ban/README.md) |
| **03** | **Cụm Kubernetes EKS Kép:** Edge & Core Private EKS 1.37, VPC Endpoints, EKS Pod Identity, NetworkPolicy. | `RUNTIME_PASS` | [03-cum-eks-kep/README.md](03-cum-eks-kep/README.md) |
| **04** | **Phân Bổ Workloads:** 2 Microservices (`edge-frontend`, `core-service`), Aurora DB, Redis, SQS, Private NLB. | `RUNTIME_PASS` | [04-phan-bo-workloads/README.md](04-phan-bo-workloads/README.md) |
| **05** | **GWLB & Suricata IDS/IPS:** Triển khai GWLB, 2 Zonal GWLBe, Suricata EC2 với GENEVE 6081, Symmetric Routing. | `RUNTIME_PASS` | [05-gwlb-suricata-ids-ips/README.md](05-gwlb-suricata-ids-ips/README.md) |
| **06** | **Centralized Egress Firewall:** AWS Network Firewall, Stateful rules, NAT theo AZ, Domain allowlist, Return route. | `RUNTIME_PASS` | [06-centralized-egress-firewall/README.md](06-centralized-egress-firewall/README.md) |
| **07** | **Edge Ingress & AWS WAF:** ALB Ingress, ACM Certificate, AWS WAF v2 Count-to-Block, WAF access logs. | `RUNTIME_PASS` | [07-edge-ingress-waf/README.md](07-edge-ingress-waf/README.md) |
| **08** | **CI/CD & DevSecOps:** Terraform Checkov scan, Trivy container security, SBOM Syft, Cosign, Digest pinning. | `RUNTIME_PASS` | [08-cicd-devsecops/README.md](08-cicd-devsecops/README.md) |
| **09** | **Toàn Diện Observability:** Tập trung hóa VPC Flow Logs, TGW Logs, Network Firewall & Suricata EVE, Reachability Analyzer. | `RUNTIME_PASS` | [09-toan-dien-observability/README.md](09-toan-dien-observability/README.md) |
| **10** | **GameDay Sự Cố Mạng:** Route leak, Asymmetric flow, Appliance failover flow retention, Firewall drop, NAT return. | `RUNTIME_PASS` | [10-gameday-su-co-mang/README.md](10-gameday-su-co-mang/README.md) |
| **11** | **Bằng Chứng & Báo Cáo:** Tổng hợp raw evidence, sanitize audit, post-mortem, FinOps cost report. | `RUNTIME_PASS` | [11-bang-chung-bao-cao/README.md](11-bang-chung-bao-cao/README.md) |
| **12** | **Dọn Dẹp FinOps:** Reverse 6-tier teardown, kiểm kê retained/pending và đối soát billing ($0.00 spend). | `READY_TO_RUN` | [12-don-dep-finops/README.md](12-don-dep-finops/README.md) |

---

## 6. Tiêu Chí Nghiệm Thu Hệ Thống (Master Acceptance Gates)

1. `[RUNTIME_PASS]` `edge-frontend` gọi `core-service` thành công qua Transit Gateway và GWLB Suricata inline IPS (`evidence/10-gameday/gameday-04-legitimate-traffic-healthcheck.txt`).
2. `[RUNTIME_PASS]` Kết nối chứa marker payload `FABRIC_IPS_TEST` bị Suricata drop và ghi nhận trong `eve.json` (SID `2026001`, `evidence/10-gameday/gameday-04-suricata-eve-blocked-event.json`).
3. `[RUNTIME_PASS]` Workload trong Core EKS truy cập thành công domain trong allowlist (`github.com`) qua Network Firewall và NAT Gateway.
4. `[RUNTIME_PASS]` Workload truy cập domain ngoài danh mục bị AWS Network Firewall drop và xuất hiện log trong `/aws/network-firewall/fabric-egress-alerts`.
5. `[RUNTIME_PASS]` Kiểm chứng tính đối xứng luồng (Symmetric Flow) qua `ApplianceModeSupport = enable` trên Transit Gateway Inspection Attachment (`evidence/10-gameday/gameday-02-asymmetric-timeline.json`).
6. `[RUNTIME_PASS]` Khi ngắt máy chủ `fabric-suricata-1a`, GWLB tự động failover sang `fabric-suricata-1b` trong vòng 32 giây mà không mất kết nối (`evidence/10-gameday/gameday-03-appliance-failover.json`).
7. `[RUNTIME_PASS]` AWS WAF v2 bảo vệ ALB Ingress ghi nhận 407 requests (385 allowed, 22 blocked) ngăn chặn các cuộc tấn công quét lỗ hổng và brute-force.
8. `[RUNTIME_PASS]` Báo cáo kiểm toán dữ liệu xác nhận 100% AWS Account ID được chuẩn hóa thành `123456789012` và không rò rỉ bất kỳ bí mật hay khóa riêng tư nào.
9. `[READY_TO_RUN]` Quy trình dọn dẹp theo thứ tự phụ thuộc ngược 6 tầng sẵn sàng kích hoạt để đưa chi phí duy trì về $0.00 USD/ngày.
