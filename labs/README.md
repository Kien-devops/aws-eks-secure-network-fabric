# Hệ Thống Labs Triển Khai: AWS EKS Secure Network Fabric

Tài liệu hướng dẫn thực hành (Hands-on Labs) chi tiết từng bước xây dựng kiến trúc **AWS Advanced Networking & Cloud-Native Security Fabric** trên nền tảng Amazon EKS đa VPC.

> [!IMPORTANT]
> **Tôn chỉ Thực thi & Chất lượng Bằng chứng (Core Principles):**
> 1. **Zero Fake Data:** Mọi kết luận kỹ thuật, bảng log, số đo latency, packet drop phải lấy trực tiếp từ raw runtime evidence có timestamp.
> 2. **AWS MCP-First:** Mọi thao tác kiểm tra, tạo, sửa, xóa tài nguyên AWS được thực thi tự động qua AWS MCP Server (`aws-api-mcp` / `aws-mcp` / `kubernetes-mcp-server`).
> 3. **Region Chuẩn:** **Singapore (`ap-southeast-1`)** - Trải rộng trên 2 Vùng sẵn sàng (`ap-southeast-1a`, `ap-southeast-1b`).
> 4. **Bảo Mật Tuyệt Đối (Sanitization):** Che giấu 100% AWS Account ID (thay bằng `123456789012` hoặc `***`), Access Keys, Passwords trước khi commit.
> 5. **Vòng đời Trạng thái Lab (Lab Status Lifecycle):**
>    - `DRAFT`: Tài liệu đã được rà soát cấu trúc, chuẩn bị quy trình chi tiết, chưa chạy trên tài khoản thực tế.
>    - `READY_TO_RUN`: Tiền đề, quyền IAM, script kiểm tra và rollback đã được kiểm duyệt, sẵn sàng kích hoạt.
>    - `RUNTIME_PASS`: Đã triển khai thực tế trên AWS Singapore qua MCP, có file raw evidence và timestamp đối chiếu.

---

## 1. Bản Đồ Thứ Tự Thực Thi DAG (Execution DAG & Dependency Flow)

Để tránh hiện tượng vòng phụ thuộc (cyclic dependency) hoặc nghẽn mạng cụm EKS riêng tư (Private EKS), thứ tự thực thi chuẩn tuân theo DAG dưới đây:

```text
[00 Chuẩn Bị & Inventory]        --> Kiểm kê AWS qua MCP, Region ap-southeast-1, FinOps Budget ($50)
       |
       v
[01 Thiết Kế & Threat Model]     --> Phân tích STRIDE, CIDR IP Plan, TGW Routing Matrix & Hop Tables
       |
       v
[02 Hạ Tầng Mạng Cơ Bản]         --> 4 VPCs, Subnets theo AZ, TGW (Appliance Mode), Temporary Direct Route, VPC Flow Logs
       |
       +------------------------------------+
       |                                    |
       v                                    v
[05 GWLB & Suricata IDS/IPS]        [06 Centralized Egress Firewall]
(Triển khai GWLB, 2 zonal GWLBe,     (AWS Network Firewall A/B,
 Suricata GENEVE 6081, Appliance     NAT Gateways, Domain allowlist,
 Mode, Cutover East-West route)       Appliance Mode trên Egress TGW)
       |                                    |
       +-----------------+------------------+
                         |
                         v
              [02.06 VPC Endpoints]         --> Tạo Private Endpoints (ECR, S3, STS, EKS, Logs) trong Edge/Core
                         |
                         v
              [03 Cụm EKS Kép (Dual EKS)]   --> EKS 1.31 Private Clusters, Node Groups, Pod Identity, NetworkPolicy baseline
                         |
                         v
              [04 Phân Bổ Workloads (app3)] --> Deploy microservices qua GitOps, Core Internal NLB (IP-target), TLS mTLS
                         |
                         v
              [07 Edge Ingress & AWS WAF]   --> Public Route 53, ACM TLS, Internet-facing ALB, AWS WAF v2 Count-to-Block
                         |
                         v
              [08 CI/CD & DevSecOps]        --> Terraform Checkov, Trivy scan, SBOM, Cosign, GitOps digest pinning
                         |
                         v
              [09 Toàn Diện Observability]  --> Tập trung CloudWatch Logs, Suricata EVE json, CW Insights, Reachability Analyzer
                         |
                         v
              [10 GameDay Kịch Bản Sự Cố]   --> Route leak, Asymmetric flow drop, Appliance failover, Firewall drop, NAT fail
                         |
                         v
              [11 Bằng Chứng & Báo Cáo]     --> Tổng hợp raw evidence, sanitize audit, post-mortem, FinOps cost report
                         |
                         v
              [12 Dọn Dẹp FinOps Hoàn Toàn] --> Reverse teardown dependency, zero residual verification, billing latency note
```

---

## 2. Kiến Trúc Mạng Chi Tiết (Architecture Blueprint)

```text
                                  Internet
                                     |
                                  Route 53
                                     |
                               ALB + AWS WAF
                                     |
    +-----------------------------------------------------------------+
    | VPC Edge EKS — 10.40.0.0/16 (ap-southeast-1a/b)                 |
    | - Public Subnets: ALB Ingress (10.40.0.0/24, 10.40.1.0/24)      |
    | - Private Subnets: Edge Nodes EKS 1.31 (10.40.8.0/22, 12.0/22)  |
    | - VPC Endpoints: ECR, S3, STS, Logs, EC2, eks-auth (10.40.20-21)|
    | - TGW Subnets: Attachment ENIs (10.40.250.0/28, 250.16/28)      |
    +-----------------------------------------------------------------+
                                     |
                          [ Transit Gateway (TGW) ]
                                     |
    +-----------------------------------------------------------------+
    | VPC Inspection — 10.70.0.0/16 (ap-southeast-1a/b)               |
    | - TGW Subnets: TGW Attachment (Appliance Mode = ENABLED)        |
    | - GWLBe Subnets: Zonal VPC Endpoints (10.70.1.0/28, 10.70.1.16/28)    |
    | - Firewall Subnets: Suricata EC2 Instances (GENEVE 6081)        |
    |   <---> Gateway Load Balancer (GWLB)                            |
    +-----------------------------------------------------------------+
                                     |
                          [ Transit Gateway (TGW) ]
                                     |
    +-----------------------------------------------------------------+
    | VPC Core EKS — 10.50.0.0/16 (ap-southeast-1a/b)                 |
    | - Private Subnets: Core Nodes EKS 1.31 (10.50.8.0/22, 12.0/22)  |
    | - VPC Endpoints: ECR, S3, STS, Logs, EC2, SQS, eks-auth (30-31) |
    | - Data Subnets: Aurora DB, Redis Cache (10.50.20.0/24, 21.0/24) |
    | - TGW Subnets: Attachment ENIs (10.50.250.0/28, 250.16/28)      |
    +-----------------------------------------------------------------+
                                     |
                      (0.0.0.0/0 qua TGW -> Inspection)
                                     |
    +-----------------------------------------------------------------+
    | VPC Centralized Egress — 10.80.0.0/16 (ap-southeast-1a/b)       |
    | - TGW Subnets: TGW Attachment (10.80.0.0/28, 10.80.0.16/28)     |
    | - Firewall Subnets: AWS Network Firewall Endpoints (10.80.1.0/28, 1.16/28) |
    | - Public Subnets: NAT Gateway A/B + IGW (10.80.10.0/24, 11.0/24)|
    +-----------------------------------------------------------------+
                                     |
                                  Internet
```

---

## 3. Ma Trận Miền Định Tuyến TGW (Routing Matrix)

> **Quy tắc bắt buộc:**
> 1. Tắt hoàn toàn `Default Route Table Association` và `Default Route Table Propagation` trên Transit Gateway.
> 2. Bật `ApplianceModeSupport = enable` trên cả **Inspection Attachment** và **Egress Attachment** để bảo đảm tính đối xứng của luồng gói tin (Symmetric stateful routing).

| TGW Route Table | Associated VPC Attachment | Routes Cấu Hình | Mục Đích Luồng Traffic |
|---|---|---|---|
| **`fabric-tgw-edge-rt`** | Edge VPC | - `10.50.0.0/16` -> Inspection Attachment<br>- `0.0.0.0/0` -> Inspection Attachment | Toàn bộ traffic sang Core hoặc ra Internet bắt buộc vào Inspection VPC kiểm tra |
| **`fabric-tgw-core-rt`** | Core VPC | - `10.40.0.0/16` -> Inspection Attachment<br>- `0.0.0.0/0` -> Inspection Attachment | Toàn bộ traffic sang Edge hoặc ra Internet bắt buộc vào Inspection VPC kiểm tra |
| **`fabric-tgw-inspection-rt`**| Inspection VPC | - `10.40.0.0/16` -> Edge Attachment<br>- `10.50.0.0/16` -> Core Attachment<br>- `0.0.0.0/0` -> Egress Attachment | Chuyển traffic đã kiểm duyệt tới đúng Spoke VPC hoặc chuyển ra Egress VPC |
| **`fabric-tgw-egress-rt`** | Egress VPC | - `10.40.0.0/16` -> Inspection Attachment<br>- `10.50.0.0/16` -> Inspection Attachment | Traffic phản hồi từ Internet về Spoke VPC bắt buộc qua Inspection kiểm tra đối xứng |
| **`fabric-tgw-dev-rt`** | Dev Test VPC *(Mở rộng)* | - `10.40.0.0/16` -> Blackhole<br>- `10.50.0.0/16` -> Blackhole | Cô lập tuyệt đối môi trường thử nghiệm với môi trường Production |

---

## 4. Kế Hoạch Phân Bổ Dải Mạng (IP Plan)

| VPC | CIDR Block | Phân Bổ Subnet Chi Tiết |
|---|---|---|
| **Edge EKS** | `10.40.0.0/16` | Public ALB: `10.40.0.0/24`, `10.40.1.0/24`<br>Private Node: `10.40.8.0/22`, `10.40.12.0/22`<br>Private VPCE: `10.40.20.0/24`, `10.40.21.0/24`<br>TGW Attachment: `10.40.250.0/28`, `10.40.250.16/28` |
| **Core EKS** | `10.50.0.0/16` | Private Node: `10.50.8.0/22`, `10.50.12.0/22`<br>Private VPCE: `10.50.30.0/24`, `10.50.31.0/24`<br>Data Subnet (DB/Cache): `10.50.20.0/24`, `10.50.21.0/24`<br>TGW Attachment: `10.50.250.0/28`, `10.50.250.16/28` |
| **Inspection** | `10.70.0.0/16` | TGW Subnet: `10.70.0.0/28`, `10.70.0.16/28`<br>GWLBe Subnet: `10.70.1.0/28`, `10.70.1.16/28`<br>Suricata EC2 Subnet: `10.70.10.0/24`, `10.70.11.0/24` |
| **Centralized Egress** | `10.80.0.0/16` | TGW Subnet: `10.80.0.0/28`, `10.80.0.16/28`<br>Firewall Endpoint Subnet: `10.80.1.0/28`, `10.80.1.16/28`<br>Public Subnet (NAT/IGW): `10.80.10.0/24`, `10.80.11.0/24` |

---

## 5. Danh Mục 13 Module Thực Hành Chi Tiết

| Module | Tên Bài Lab & Nội Dung Trọng Tâm | Trạng Thái | File Hướng Dẫn |
|---|---|:---:|---|
| **00** | **Chuẩn bị & Kiểm kê:** Read-only AWS Inventory qua MCP, Region validation, FinOps Budget ($50). | `DRAFT` | [00-chuan-bi-inventory/README.md](00-chuan-bi-inventory/README.md) |
| **01** | **Thiết kế & Threat Model:** STRIDE Threat Analysis, CIDR non-overlapping plan, TGW Hop table. | `DRAFT` | [01-thiet-ke-threat-model/README.md](01-thiet-ke-threat-model/README.md) |
| **02** | **Hạ tầng Mạng Cơ bản:** Khởi tạo 4 VPCs, Subnets theo AZ, Transit Gateway, Route Domains, Flow Logs. | `DRAFT` | [02-ha-tang-mang-co-ban/README.md](02-ha-tang-mang-co-ban/README.md) |
| **03** | **Cụm Kubernetes EKS Kép:** Edge & Core Private EKS 1.31, VPC Endpoints, EKS Pod Identity, NetworkPolicy. | `DRAFT` | [03-cum-eks-kep/README.md](03-cum-eks-kep/README.md) |
| **04** | **Phân bổ Workloads (app3):** Frontend, Auth, Order, Inventory, Payment, Internal Route 53 & NLB IP-targets. | `DRAFT` | [04-phan-bo-workloads/README.md](04-phan-bo-workloads/README.md) |
| **05** | **GWLB & Suricata IDS/IPS:** Triển khai GWLB, 2 Zonal GWLBe, Suricata EC2 với GENEVE 6081, Symmetric Routing. | `DRAFT` | [05-gwlb-suricata-ids-ips/README.md](05-gwlb-suricata-ids-ips/README.md) |
| **06** | **Centralized Egress Firewall:** AWS Network Firewall, Stateful rules, NAT theo AZ, Domain allowlist, Return route. | `DRAFT` | [06-centralized-egress-firewall/README.md](06-centralized-egress-firewall/README.md) |
| **07** | **Edge Ingress & AWS WAF:** ALB Ingress, ACM Certificate, AWS WAF v2 Count-to-Block, WAF access logs. | `DRAFT` | [07-edge-ingress-waf/README.md](07-edge-ingress-waf/README.md) |
| **08** | **CI/CD & DevSecOps:** Terraform Checkov scan, Trivy container security, SBOM, Cosign, Digest pinning. | `DRAFT` | [08-cicd-devsecops/README.md](08-cicd-devsecops/README.md) |
| **09** | **Toàn diện Observability:** Tập trung hóa VPC Flow Logs, TGW Logs, Network Firewall & Suricata EVE, Reachability Analyzer. | `DRAFT` | [09-toan-dien-observability/README.md](09-toan-dien-observability/README.md) |
| **10** | **GameDay Sự Cố Mạng:** Route leak, Asymmetric flow, Appliance failover flow retention, Firewall drop, NAT return. | `DRAFT` | [10-gameday-su-co-mang/README.md](10-gameday-su-co-mang/README.md) |
| **11** | **Bằng chứng & Báo cáo:** Tổng hợp raw logs, biểu đồ packet flow runtime, báo cáo Incident Post-mortem, Cost report. | `DRAFT` | [11-bang-chung-bao-cao/README.md](11-bang-chung-bao-cao/README.md) |
| **12** | **Dọn dẹp FinOps:** Quy trình Reverse Teardown, kiểm kê xác nhận tài nguyên tính phí về đúng mức $0.00. | `DRAFT` | [12-don-dep-finops/README.md](12-don-dep-finops/README.md) |

---

## 6. Tiêu Chí Nghiệm Thu (Acceptance Gate - 9 Verification Criteria)

Mọi tiêu chí bắt buộc phải có bằng chứng runtime có timestamp trước khi chuyển trạng thái sang `[RUNTIME_PASS]`:
1. `[PENDING_VERIFICATION]` Edge gọi Core qua cổng `443` thành công thông qua GWLBe và Suricata appliance.
2. `[PENDING_VERIFICATION]` Kết nối thử nghiệm tới cổng trái phép hoặc attack payload (plaintext HTTP/TCP) bị Suricata drop và ghi nhận trong `eve.json`.
3. `[PENDING_VERIFICATION]` Môi trường Dev không thể kết nối tới bất kỳ IP nào của Prod do TGW Blackhole route.
4. `[PENDING_VERIFICATION]` Workload trong Core EKS truy cập thành công domain trong allowlist (`quay.io`, `github.com`) qua Network Firewall.
5. `[PENDING_VERIFICATION]` Workload truy cập domain ngoài danh mục bị Network Firewall drop và xuất hiện log `DROP`/`ALERT`.
6. `[PENDING_VERIFICATION]` Ghi nhận `tcpdump` trên Suricata appliance xác nhận request và response cùng đi qua appliance trong cùng một AZ (Symmetric flow).
7. `[PENDING_VERIFICATION]` Khi terminate 1 Suricata appliance, GWLB tự loại target trong chu kỳ health check, các luồng kết nối mới được chuyển thông suốt sang appliance sống.
8. `[PENDING_VERIFICATION]` AWS VPC Reachability Analyzer phân tích đường truyền TGW và chỉ ra đúng điểm nghẽn (route/NACL).
9. `[PENDING_VERIFICATION]` Container images chạy bằng `@sha256:...`, không dùng static AWS credentials.

---

## 7. Tài Liệu Tham Chiếu Cốt Lõi

- [Lab 274 — TGW Segmentation](file:///E:/repo/lab-aws/network-advance/labs/Lab%20274%20-%20Transit%20Gateway%20Segmentation.md)
- [Lab 275 — Centralized Egress with TGW](file:///E:/repo/lab-aws/network-advance/labs/Lab%20275%20-%20Centralized%20Egress%20with%20Transit%20Gateway.md)
- [Lab 280 — Gateway Load Balancer Inspection](file:///E:/repo/lab-aws/network-advance/labs/Lab%20280%20-%20Gateway%20Load%20Balancer%20Inspection.md)
- [Lab 281 — AWS Network Firewall Egress](file:///E:/repo/lab-aws/network-advance/labs/Lab%20281%20-%20AWS%20Network%20Firewall%20Egress.md)
- [Lab 282 — ALB/NLB TLS and Source IP](file:///E:/repo/lab-aws/network-advance/labs/Lab%20282%20-%20ALB%20NLB%20TLS%20and%20Source%20IP.md)
- [Lab 283 — WAF and Ingress Security](file:///E:/repo/lab-aws/network-advance/labs/Lab%20283%20-%20CloudFront%20WAF%20and%20OAC.md)
- [Lab 288 — Network Observability & Incident](file:///E:/repo/lab-aws/network-advance/labs/Lab%20288%20-%20Network%20Observability%20Incident%20Lab.md)
