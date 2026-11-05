# Hệ Thống Labs Triển Khai: AWS EKS Secure Network Fabric

Tài liệu hướng dẫn thực hành (Hands-on Labs) chi tiết từng bước xây dựng kiến trúc **AWS Advanced Networking & Cloud-Native Security Fabric** trên nền tảng Amazon EKS đa VPC.

> [!IMPORTANT]
> **Tôn chỉ Thực thi & Chất lượng Bằng chứng (Core Principles):**
> 1. **Zero Fake Data:** Mọi kết luận kỹ thuật, bảng log, số đo latency, packet drop phải lấy trực tiếp từ raw runtime evidence có timestamp.
> 2. **AWS MCP-First:** Mọi thao tác kiểm tra, tạo, sửa, xóa tài nguyên AWS được thực thi tự động qua AWS MCP Server (`aws-api-mcp` / `aws-mcp` / `kubernetes-mcp-server`).
> 3. **Region Chuẩn:** **Singapore (`ap-southeast-1`)** - Trải rộng trên 2 Vùng sẵn sàng (`ap-southeast-1a`, `ap-southeast-1b`).
> 4. **Bảo Mật Tuyệt Đối (Sanitization):** Che giấu 100% AWS Account ID (thay bằng `123456789012` hoặc `***`), Access Keys, Passwords trước khi commit.

---

## 1. Bản Đồ Tổng Thể 13 Module Triển Khai (Phases 00 - 12)

```text
[00 Chuẩn Bị & Inventory]        --> Kiểm kê tài nguyên AWS hiện tại, xác thực Region ap-southeast-1, ngân sách FinOps
       |
       v
[01 Thiết Kế & Threat Model]     --> Phân tích đe dọa STRIDE, IP Plan không chồng lấn, TGW routing matrix, hop tables
       |
       v
[02 Hạ Tầng Mạng Cơ Bản]         --> 4 VPCs, Subnets theo AZ, Transit Gateway, Route Domains (Edge/Core/Insp/Egress), Flow Logs
       |
       v
[03 Cụm EKS Kép (Dual EKS)]      --> Edge EKS & Core EKS riêng tư, EKS Pod Identity, KMS encryption, NetworkPolicy cơ bản
       |
       v
[04 Phân Bổ Workloads (app3)]    --> Frontend & Auth (Edge), Order/Inventory/Payment (Core), Route 53 Private, Internal TLS
       |
       v
[05 GWLB & Suricata IDS/IPS]     --> Gateway Load Balancer, GWLBe, GENEVE tunnel (UDP 6081), TGW Appliance Mode, Symmetric flow
       |
       v
[06 Centralized Egress Firewall] --> AWS Network Firewall, Stateful Suricata rules, NAT Gateway theo AZ, Domain allowlist
       |
       v
[07 Edge Ingress & AWS WAF]      --> Public Route 53, ACM TLS, Internet-facing ALB, AWS WAF v2 (Count-to-Block), Rate Limiting
       |
       v
[08 CI/CD & DevSecOps]           --> Terraform Checkov scan, Trivy container scan, SBOM, Cosign signing, Immutable digest
       |
       v
[09 Toàn Diện Observability]     --> VPC Flow Logs, TGW Logs, Network Firewall alerts, Suricata eve.json, Reachability Analyzer
       |
       v
[10 GameDay Kịch Bản Sự Cố]      --> Route leak, Asymmetric routing, Appliance failure (failover), Firewall drop, NAT return fail
       |
       v
[11 Bằng Chứng & Báo Cáo]        --> Tổng hợp raw logs, biểu đồ đường truyền thực tế, báo cáo Incident Post-mortem, bảng chi phí
       |
       v
[12 Dọn Dẹp FinOps Hoàn Toàn]    --> Reverse Cleanup Dependency Order, kiểm kê tự động xác nhận chi phí tồn dư về đúng $0.00
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
    | - Private Subnets: Edge Nodes (10.40.10.0/22, 10.40.14.0/22)    |
    | - TGW Subnets: Attachment ENIs (10.40.250.0/28, 10.40.250.16/28)|
    +-----------------------------------------------------------------+
                                     |
                          [ Transit Gateway (TGW) ]
                                     |
    +-----------------------------------------------------------------+
    | VPC Inspection — 10.70.0.0/16 (ap-southeast-1a/b)               |
    | - TGW Subnets: TGW Attachment (Appliance Mode = ENABLED)        |
    | - GWLBe Subnets: VPC Endpoints trỏ đến GWLB (gwlbe-a, gwlbe-b)  |
    | - Firewall Subnets: Suricata EC2 Instances (GENEVE 6081)        |
    |   <---> Gateway Load Balancer (GWLB)                            |
    +-----------------------------------------------------------------+
                                     |
                          [ Transit Gateway (TGW) ]
                                     |
    +-----------------------------------------------------------------+
    | VPC Core EKS — 10.50.0.0/16 (ap-southeast-1a/b)                 |
    | - Private Subnets: Core Nodes (10.50.10.0/22, 10.50.14.0/22)    |
    | - Data Subnets: Aurora DB, Redis Cache, SQS VPCE                |
    | - TGW Subnets: Attachment ENIs (10.50.250.0/28, 10.50.250.16/28)|
    +-----------------------------------------------------------------+
                                     |
                               0.0.0.0/0 qua TGW
                                     |
    +-----------------------------------------------------------------+
    | VPC Centralized Egress — 10.80.0.0/16 (ap-southeast-1a/b)       |
    | - TGW Subnets: Attachment ENIs (10.80.0.0/28, 10.80.0.16/28)    |
    | - Firewall Subnets: AWS Network Firewall Endpoints (AZ-A, AZ-B) |
    | - Public Subnets: NAT Gateway A/B, Internet Gateway             |
    +-----------------------------------------------------------------+
                                     |
                                  Internet
```

---

## 3. Ma Trận Miền Định Tuyến TGW (Routing Matrix)

> **Quy tắc bắt buộc:** Tắt hoàn toàn `Default Route Table Association` và `Default Route Table Propagation` trên Transit Gateway. Bật `ApplianceModeSupport = enable` trên Inspection Attachment.

| TGW Route Table | Associated VPC Attachment | Routes Cấu Hình | Mục Đích Luồng Traffic |
|---|---|---|---|
| **`edge-rt`** | Edge VPC | - `10.50.0.0/16` -> Inspection Attachment<br>- `0.0.0.0/0` -> Egress Attachment | Traffic tới Core bắt buộc qua GWLB kiểm tra; traffic ra Internet vào Egress |
| **`core-rt`** | Core VPC | - `10.40.0.0/16` -> Inspection Attachment<br>- `0.0.0.0/0` -> Egress Attachment | Traffic về Edge bắt buộc qua GWLB kiểm tra; traffic ra Internet vào Egress |
| **`inspection-rt`**| Inspection VPC | - `10.40.0.0/16` -> Edge Attachment<br>- `10.50.0.0/16` -> Core Attachment | Trả traffic đã qua kiểm duyệt Suricata về đúng VPC đích |
| **`egress-rt`** | Egress VPC | - `10.40.0.0/16` -> Edge Attachment<br>- `10.50.0.0/16` -> Core Attachment | Trả traffic phản hồi từ Internet về đúng VPC khởi tạo kết nối |
| **`dev-rt`** | Dev Test VPC *(Mở rộng)* | - `10.40.0.0/16` -> Blackhole<br>- `10.50.0.0/16` -> Blackhole | Cô lập tuyệt đối môi trường thử nghiệm với môi trường Production |

---

## 4. Kế Hoạch Phân Bổ Dải Mạng (IP Plan)

| VPC | CIDR Block | Phân Bổ Subnet Chi Tiết |
|---|---|---|
| **Edge EKS** | `10.40.0.0/16` | Public ALB: `10.40.0.0/24`, `10.40.1.0/24`<br>Private Node: `10.40.10.0/22`, `10.40.14.0/22`<br>Private Pod (Secondary): `10.40.64.0/18`<br>TGW Attachment: `10.40.250.0/28`, `10.40.250.16/28` |
| **Core EKS** | `10.50.0.0/16` | Private Node: `10.50.10.0/22`, `10.50.14.0/22`<br>Private Pod (Secondary): `10.50.64.0/18`<br>Data Subnet (DB/Cache): `10.50.20.0/24`, `10.50.21.0/24`<br>TGW Attachment: `10.50.250.0/28`, `10.50.250.16/28` |
| **Inspection** | `10.70.0.0/16` | TGW Subnet: `10.70.0.0/28`, `10.70.0.16/28`<br>GWLBe Subnet: `10.70.1.0/28`, `10.70.1.16/28`<br>Suricata EC2 Subnet: `10.70.10.0/24`, `10.70.11.0/24` |
| **Centralized Egress** | `10.80.0.0/16` | TGW Subnet: `10.80.0.0/28`, `10.80.0.16/28`<br>Firewall Endpoint Subnet: `10.80.1.0/28`, `10.80.1.16/28`<br>Public Subnet (NAT/IGW): `10.80.10.0/24`, `10.80.11.0/24` |

---

## 5. Danh Mục 13 Module Thực Hành Chi Tiết

| Module | Tên Bài Lab & Nội Dung Trọng Tâm | Trạng Thái | File Hướng Dẫn |
|---|---|:---:|---|
| **00** | **Chuẩn bị & Kiểm kê:** Read-only AWS Inventory qua MCP, Region validation, FinOps Budget ($50). | Sẵn sàng | [00-chuan-bi-inventory/README.md](00-chuan-bi-inventory/README.md) |
| **01** | **Thiết kế & Threat Model:** STRIDE Threat Analysis, CIDR non-overlapping plan, TGW Hop table. | Sẵn sàng | [01-thiet-ke-threat-model/README.md](01-thiet-ke-threat-model/README.md) |
| **02** | **Hạ tầng Mạng Cơ bản:** Khởi tạo 4 VPCs, Subnets theo AZ, Transit Gateway, Route Domains, Flow Logs. | Sẵn sàng | [02-ha-tang-mang-co-ban/README.md](02-ha-tang-mang-co-ban/README.md) |
| **03** | **Cụm Kubernetes EKS Kép:** Edge & Core Private Clusters, EKS Pod Identity, KMS Secrets, NetworkPolicy. | Sẵn sàng | [03-cum-eks-kep/README.md](03-cum-eks-kep/README.md) |
| **04** | **Phân bổ Workloads (app3):** Frontend, Auth, Order, Inventory, Payment, Internal Route 53 & NLB TLS. | Sẵn sàng | [04-phan-bo-workloads/README.md](04-phan-bo-workloads/README.md) |
| **05** | **GWLB & Suricata IDS/IPS:** Triển khai GWLB, GWLBe, 2 Suricata EC2 với GENEVE 6081, Symmetric Routing. | Sẵn sàng | [05-gwlb-suricata-ids-ips/README.md](05-gwlb-suricata-ids-ips/README.md) |
| **06** | **Centralized Egress Firewall:** AWS Network Firewall, Stateful rules, NAT theo AZ, Domain allowlist. | Sẵn sàng | [06-centralized-egress-firewall/README.md](06-centralized-egress-firewall/README.md) |
| **07** | **Edge Ingress & AWS WAF:** ALB Ingress, ACM Certificate, AWS WAF v2 Count-to-Block, WAF access logs. | Sẵn sàng | [07-edge-ingress-waf/README.md](07-edge-ingress-waf/README.md) |
| **08** | **CI/CD & DevSecOps:** Terraform Checkov scan, Trivy container security, SBOM, Cosign, Digest pinning. | Sẵn sàng | [08-cicd-devsecops/README.md](08-cicd-devsecops/README.md) |
| **09** | **Toàn diện Observability:** Tập trung hóa VPC Flow Logs, TGW Logs, Network Firewall & Suricata EVE, Reachability Analyzer. | Sẵn sàng | [09-toan-dien-observability/README.md](09-toan-dien-observability/README.md) |
| **10** | **GameDay Sự Cố Mạng:** Route leak, Asymmetric flow, Appliance failover, Firewall drop, NAT return fail. | Sẵn sàng | [10-gameday-su-co-mang/README.md](10-gameday-su-co-mang/README.md) |
| **11** | **Bằng chứng & Báo cáo:** Tổng hợp raw logs, biểu đồ packet flow runtime, báo cáo Incident Post-mortem, Cost report. | Sẵn sàng | [11-bang-chung-bao-cao/README.md](11-bang-chung-bao-cao/README.md) |
| **12** | **Dọn dẹp FinOps:** Quy trình Reverse Teardown, kiểm kê xác nhận tài nguyên tính phí về đúng mức $0.00. | Sẵn sàng | [12-don-dep-finops/README.md](12-don-dep-finops/README.md) |

---

## 6. Tiêu Chí Nghiệm Thu (Acceptance Gate - 9 PASS Criteria)

Mọi tiêu chí bắt buộc phải có bằng chứng runtime có timestamp trước khi đánh dấu hoàn thành:
1. `[PASS]` Edge gọi Core qua cổng `443` thành công thông qua GWLBe và Suricata appliance.
2. `[PASS]` Kết nối thử nghiệm tới cổng trái phép hoặc attack payload bị Suricata drop và ghi nhận trong `eve.json`.
3. `[PASS]` Môi trường Dev không thể kết nối tới bất kỳ IP nào của Prod do TGW Blackhole route.
4. `[PASS]` Workload trong Core EKS truy cập thành công domain trong allowlist (`quay.io`, `github.com`) qua Network Firewall.
5. `[PASS]` Workload truy cập domain ngoài danh mục bị Network Firewall drop và xuất hiện log `DROP`/`ALERT`.
6. `[PASS]` Ghi nhận `tcpdump` trên Suricata appliance xác nhận request và response cùng đi qua appliance trong cùng một AZ.
7. `[PASS]` Khi terminate 1 Suricata appliance, GWLB tự loại target trong vài giây, lưu lượng duy trì thông suốt.
8. `[PASS]` AWS VPC Reachability Analyzer phân tích chính xác đường truyền và phát hiện lỗi route/NACL nhân tạo.
9. `[PASS]` Container images chạy bằng `@sha256:...`, không dùng static AWS credentials.

---

## 7. Tài Liệu Tham Chiếu Cốt Lõi

- [Lab 274 — TGW Segmentation](file:///E:/repo/lab-aws/network-advance/labs/Lab%20274%20-%20Transit%20Gateway%20Segmentation.md)
- [Lab 275 — Centralized Egress with TGW](file:///E:/repo/lab-aws/network-advance/labs/Lab%20275%20-%20Centralized%20Egress%20with%20Transit%20Gateway.md)
- [Lab 280 — Gateway Load Balancer Inspection](file:///E:/repo/lab-aws/network-advance/labs/Lab%20280%20-%20Gateway%20Load%20Balancer%20Inspection.md)
- [Lab 281 — AWS Network Firewall Egress](file:///E:/repo/lab-aws/network-advance/labs/Lab%20281%20-%20AWS%20Network%20Firewall%20Egress.md)
- [Lab 282 — ALB/NLB TLS and Source IP](file:///E:/repo/lab-aws/network-advance/labs/Lab%20282%20-%20ALB%20NLB%20TLS%20and%20Source%20IP.md)
- [Lab 283 — WAF and Ingress Security](file:///E:/repo/lab-aws/network-advance/labs/Lab%20283%20-%20CloudFront%20WAF%20and%20OAC.md)
- [Lab 288 — Network Observability & Incident](file:///E:/repo/lab-aws/network-advance/labs/Lab%20288%20-%20Network%20Observability%20Incident%20Lab.md)
