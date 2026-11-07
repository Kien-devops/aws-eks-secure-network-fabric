# Hệ Thống Labs Triển Khai: AWS EKS Secure Network Fabric

Tài liệu hướng dẫn thực hành (Hands-on Labs) chi tiết từng bước xây dựng kiến trúc **AWS Advanced Networking & Cloud-Native Security Fabric** trên nền tảng Amazon EKS đa VPC.

> [!IMPORTANT]
> **Tôn chỉ Thực thi & Chất lượng Bằng chứng (Core Principles):**
> 1. **Zero Fake Data:** Mọi kết luận kỹ thuật, bảng log, số đo latency, packet drop phải lấy trực tiếp từ raw runtime evidence có timestamp.
> 2. **Console-first:** Thực hành theo walkthrough Console. Khi tự động hóa trong phạm vi được phép, ưu tiên `aws-mcp` và `kubernetes-mcp-server`; không tự deploy/apply/destroy. CLI là cách kiểm chứng bổ sung.
> 3. **Region Chuẩn:** **Singapore (`ap-southeast-1`)** - Trải rộng trên 2 Vùng sẵn sàng (`ap-southeast-1a`, `ap-southeast-1b`).
> 4. **Bảo Mật Tuyệt Đối (Sanitization):** Che giấu 100% AWS Account ID (thay bằng `123456789012` hoặc `***`), Access Keys, Passwords trước khi commit.
> 5. **Vòng đời Trạng thái Lab (Lab Status Lifecycle):**
>    - `DRAFT`: Tài liệu đã được rà soát cấu trúc, chuẩn bị quy trình chi tiết, chưa chạy trên tài khoản thực tế.
>    - `READY_TO_RUN`: Tiền đề, quyền IAM, script kiểm tra và rollback đã được kiểm duyệt, sẵn sàng kích hoạt.
>    - `RUNTIME_PASS`: Đã triển khai thực tế trên AWS Singapore qua MCP, có file raw evidence và timestamp đối chiếu.

---

## Quy ước trước khi chạy

Checkpoint chỉ đọc 07/11/2026: đã có nền tảng tới 03.04; nodes đang scale 0 nên CoreDNS/EBS CSI chưa healthy, các module app/inspection/egress sau chưa triển khai. Public Kubernetes API CIDR ghi nhận `0.0.0.0/0`, khác target allowlist quản trị bên dưới. Tài liệu được sửa không đồng nghĩa live đã đổi; muốn chạy tiếp phải có cửa sổ bật nodes và xử lý access/routing riêng, được phép trước khi thay đổi. Budget $50 là cảnh báo, không tự dừng tài nguyên.

- Các bài có `RUNTIME_PASS` lưu kết quả tại thời điểm thực thi; không cam kết tài nguyên hiện còn chạy. Không ghi đè evidence cũ khi kiểm tra lại.
- `DRAFT` chưa đủ điều kiện chạy tự động. Chỉ chuyển `READY_TO_RUN` khi đã có artifact đầu vào, phiên bản được ghim, quyền hợp lệ, positive/negative control và rollback đã rà soát. Không đổi sang PASS chỉ vì đủ heading.
- Lệnh shell trong các block `bash` chạy bằng Bash trên máy quản trị có đường đến API EKS; không dán nguyên vào PowerShell. Luôn chỉ định context khi thao tác Kubernetes.
- Nguồn chuẩn của routing MVP: bài 01.03 và bảng TGW bên dưới. Egress không qua GWLB. Evidence module 02 ngày 05/11 phản ánh ma trận cũ; không phải bằng chứng ma trận đã được sửa live.
- Dừng trước module 04 nếu repo app chưa có source, Dockerfile, manifests, contract cổng/TLS/health và immutable image digest. Module 08 không được giả định Terraform hoặc pipeline đã tồn tại.
- Dependency: 00 → 01 → 02 → bootstrap quản trị appliance (05.01) → 05.02–05.03 và 06.01–06.03 → 06.04 cutover egress → 03 → 04 → 05.04 nghiệm thu East-West → 07 → 08 → 09 → 10 → 11 → 12. Phần inspection có thể dựng trước EKS, nhưng chỉ nghiệm thu app khi có workload. Dự án hiện đã thực hiện 03.04 bằng private endpoints; không dựng lại tài nguyên đã có.


## 1. Bản Đồ Thứ Tự Thực Thi DAG (Execution DAG & Dependency Flow)

Để tránh hiện tượng vòng phụ thuộc (cyclic dependency) hoặc nghẽn mạng cụm EKS riêng tư (Private EKS), thứ tự thực thi chuẩn tuân theo DAG dưới đây:

```text
[00 Chuẩn Bị & Inventory]        --> Kiểm kê AWS qua MCP, Region ap-southeast-1, FinOps Budget ($50)
       |
       v
[01 Thiết Kế & Threat Model]     --> Phân tích STRIDE, CIDR IP Plan, TGW Routing Matrix & Hop Tables
       |
       v
[02 Hạ Tầng Mạng Cơ Bản]         --> 4 VPCs, Subnets theo AZ, TGW (Appliance Mode), Fail-closed routes (chưa cutover), VPC Flow Logs
       |
       +------------------------------------+
       |                                    |
       v                                    v
[05 GWLB & Suricata IDS/IPS]        [06 Centralized Egress Firewall]
(Bootstrap quản trị appliance,      (AWS Network Firewall A/B,
 GWLB, 2 zonal GWLBe; chỉ dựng       NAT Gateways, Domain allowlist,
 05.01–05.03, chưa nghiệm thu app)    06.01–06.03, cutover sau kiểm tra)
       |                                    |
       +-----------------+------------------+
                         |
                         v
              [02.06 / 06.04 prerequisites] --> Endpoints thuộc nền tảng 02; kiểm tra egress trước khi cần tải artifact
                         |
                         v
              [03 Cụm EKS Kép (Dual EKS)]   --> EKS 1.37; endpoints/quản trị sẵn sàng; policy app hoàn tất sau manifests
                         |
                         v
              [04 Phân Bổ Workloads (app3)] --> Deploy microservices qua GitOps, Core Internal NLB (IP-target), TLS tại backend (CA nội bộ)
                         |                     Gate: source, ECR images, manifests, CA, secrets/migration đã có
                         v
              [05.04 East-West acceptance]  --> Cutover/kiểm chứng hai AZ khi app controls đã sẵn sàng
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
    | - Private Subnets: Edge Nodes EKS 1.37 (10.40.8.0/22, 12.0/22)  |
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
    | - Private Subnets: Core Nodes EKS 1.37 (10.50.8.0/22, 12.0/22)  |
    | - VPC Endpoints: ECR, S3, STS, Logs, EC2, SQS, eks-auth (30-31) |
    | - Data Subnets: Aurora DB, Redis Cache (10.50.20.0/24, 21.0/24) |
    | - TGW Subnets: Attachment ENIs (10.50.250.0/28, 250.16/28)      |
    +-----------------------------------------------------------------+
                                     |
                      (0.0.0.0/0 qua TGW -> Egress)
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
| **`fabric-tgw-edge-rt`** | Edge VPC | - `10.50.0.0/16` -> Inspection Attachment<br>- `0.0.0.0/0` -> Egress Attachment | Traffic sang Core qua Inspection; traffic Internet qua Egress |
| **`fabric-tgw-core-rt`** | Core VPC | - `10.40.0.0/16` -> Inspection Attachment<br>- `0.0.0.0/0` -> Egress Attachment | Traffic sang Edge qua Inspection; traffic Internet qua Egress |
| **`fabric-tgw-inspection-rt`**| Inspection VPC | - `10.40.0.0/16` -> Edge Attachment<br>- `10.50.0.0/16` -> Core Attachment | Chuyển traffic East-West đã kiểm duyệt tới đúng Spoke VPC |
| **`fabric-tgw-egress-rt`** | Egress VPC | - `10.40.0.0/16` -> Edge Attachment<br>- `10.50.0.0/16` -> Core Attachment | Traffic phản hồi từ Internet về đúng Spoke, không qua GWLB |
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
| **03** | **Cụm Kubernetes EKS Kép:** Edge & Core Private EKS 1.37, VPC Endpoints, EKS Pod Identity, NetworkPolicy. | `DRAFT` | [03-cum-eks-kep/README.md](03-cum-eks-kep/README.md) |
| **04** | **Phân bổ Workloads (app3):** Frontend, Auth, Order, Inventory, Payment, Internal Route 53 & NLB IP-targets. | `DRAFT` | [04-phan-bo-workloads/README.md](04-phan-bo-workloads/README.md) |
| **05** | **GWLB & Suricata IDS/IPS:** Triển khai GWLB, 2 Zonal GWLBe, Suricata EC2 với GENEVE 6081, Symmetric Routing. | `DRAFT` | [05-gwlb-suricata-ids-ips/README.md](05-gwlb-suricata-ids-ips/README.md) |
| **06** | **Centralized Egress Firewall:** AWS Network Firewall, Stateful rules, NAT theo AZ, Domain allowlist, Return route. | `DRAFT` | [06-centralized-egress-firewall/README.md](06-centralized-egress-firewall/README.md) |
| **07** | **Edge Ingress & AWS WAF:** ALB Ingress, ACM Certificate, AWS WAF v2 Count-to-Block, WAF access logs. | `DRAFT` | [07-edge-ingress-waf/README.md](07-edge-ingress-waf/README.md) |
| **08** | **CI/CD & DevSecOps:** Terraform Checkov scan, Trivy container security, SBOM, Cosign, Digest pinning. | `DRAFT` | [08-cicd-devsecops/README.md](08-cicd-devsecops/README.md) |
| **09** | **Toàn diện Observability:** Tập trung hóa VPC Flow Logs, TGW Logs, Network Firewall & Suricata EVE, Reachability Analyzer. | `DRAFT` | [09-toan-dien-observability/README.md](09-toan-dien-observability/README.md) |
| **10** | **GameDay Sự Cố Mạng:** Route leak, Asymmetric flow, Appliance failover flow retention, Firewall drop, NAT return. | `DRAFT` | [10-gameday-su-co-mang/README.md](10-gameday-su-co-mang/README.md) |
| **11** | **Bằng chứng & Báo cáo:** Tổng hợp raw logs, biểu đồ packet flow runtime, báo cáo Incident Post-mortem, Cost report. | `DRAFT` | [11-bang-chung-bao-cao/README.md](11-bang-chung-bao-cao/README.md) |
| **12** | **Dọn dẹp FinOps:** Reverse teardown, kiểm kê retained/pending và đối soát billing sau cleanup. | `DRAFT` | [12-don-dep-finops/README.md](12-don-dep-finops/README.md) |

---

## 6. Tiêu Chí Nghiệm Thu (Acceptance Gate - 9 Verification Criteria)

Mọi tiêu chí bắt buộc phải có bằng chứng runtime có timestamp trước khi chuyển trạng thái sang `[RUNTIME_PASS]`:
1. `[PENDING_VERIFICATION]` Edge gọi Core qua cổng `443` thành công thông qua GWLBe và Suricata appliance.
2. `[PENDING_VERIFICATION]` Kết nối thử nghiệm tới cổng trái phép hoặc attack payload (plaintext HTTP/TCP) bị Suricata drop và ghi nhận trong `eve.json`.
3. `[OPTIONAL_OUTSIDE_MVP]` Dev blackhole cần VPC/attachment thứ năm và phép thử riêng; không tạo thêm chỉ để nghiệm thu MVP bốn VPC.
4. `[PENDING_VERIFICATION]` Workload trong Core EKS truy cập thành công domain trong allowlist (`quay.io`, `github.com`) qua Network Firewall.
5. `[PENDING_VERIFICATION]` Workload truy cập domain ngoài danh mục bị Network Firewall drop và xuất hiện log `DROP`/`ALERT`.
6. `[PENDING_VERIFICATION]` Ghi nhận `tcpdump` trên Suricata appliance xác nhận request và response cùng đi qua appliance trong cùng một AZ (Symmetric flow).
7. `[PENDING_VERIFICATION]` Khi stop một appliance, đo kết nối mới chuyển qua target healthy còn lại với cross-zone; đo phiên cũ riêng, không cam kết failover theo health interval.
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
