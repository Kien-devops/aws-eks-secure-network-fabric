# Bản Đặc Tả Kỹ Thuật Dự Án: AWS EKS Secure Network Fabric

## 1. Thông Tin Chung & Bối Cảnh Portfolio

- **Tên dự án:** `aws-eks-secure-network-fabric`
- **Mục tiêu cốt lõi:** Chứng minh năng lực Chuyên gia Mạng Nâng cao & An ninh Đám mây (AWS Advanced Networking & Cloud-Native Security Architect) ở cấp độ Production. Tập trung giải quyết bài toán: **Phân đoạn mạng đa VPC (Multi-VPC Segmentation)**, **Định tuyến đối xứng qua TGW Appliance Mode**, **Kiểm tra sâu gói tin nội bộ qua GWLB/GENEVE + Suricata IDS/IPS (East-West)**, và **Tường lửa tập trung kiểm soát lưu lượng đi ra ngoài (Centralized Egress qua AWS Network Firewall)** trên 2 cụm Kubernetes EKS độc lập. Dự án tập trung thuần túy vào giải pháp hạ tầng mạng, không làm thêm dự án DR hoặc CRUD ứng dụng mới.
- **Ranh giới Vùng Địa Lý (Strictly Single-Region Scope):**
  - **DUY NHẤT 1 VÙNG:** **Singapore (`ap-southeast-1`)**.
  - **Phạm vi khả dụng:** Triển khai chịu lỗi cao đa Availability Zones (Multi-AZ) trên đúng 2 AZs: **`ap-southeast-1a`** và **`ap-southeast-1b`**.
  - **Khẳng định nguyên tắc:** Tuyệt đối **KHÔNG** triển khai liên vùng (Multi-Region), không peering cross-region, không dùng Global Accelerator liên vùng. Toàn bộ 4 VPCs và 2 cụm EKS đều nằm trọn vẹn trong `ap-southeast-1`.
- **Cấu trúc 2 Repository trên GitHub:**
  1. **Hạ tầng & Nền tảng (Platform & Infrastructure):** [`aws-eks-secure-network-fabric`](https://github.com/Kien-devops/aws-eks-secure-network-fabric)
  2. **Ứng dụng & GitOps (Workloads & Delivery):** [`aws-eks-secure-network-fabric-app`](https://github.com/Kien-devops/aws-eks-secure-network-fabric-app)

### Đánh giá khoảng trống năng lực từ 5 dự án trước đó

| Repository | Nội dung đã thực hiện | Mức độ bằng chứng (Evidence) | Khoảng trống cần hoàn thiện |
|---|---|---|---|
| **NT533** | ECS Fargate DR, khôi phục RDS, AWS Backup, Step Functions, CloudFormation | Một lần diễn tập DR trong lịch sử; ALB hoạt động tốt, chưa hoàn thiện chuyển hướng DNS & đối soát dữ liệu | Thiếu mô hình multi-VPC phức tạp, chưa có EKS và hệ thống kiểm soát an ninh tập trung |
| **k3s-onprem** | K3s, Ansible, HAProxy, Cloudflare Tunnel, self-hosted CD | Chủ yếu cấu hình và tài liệu; thiếu bằng chứng chạy thực tế (raw runtime evidence) | Thiếu định tuyến đám mây nâng cao và các giải pháp mạng chuẩn doanh nghiệp trên AWS |
| **NT548** | Microservices trên ECS, Terraform, CodePipeline, RDS, ADOT/X-Ray | Bằng chứng chạy local; CI/CD còn vướng quyền IAM và quyền sở hữu | Chưa có phân đoạn mạng chuyên sâu, chưa có hệ thống IDS/IPS kiểm soát luồng gói tin |
| **Multi-Region DR** | EKS trên 2 Region, Aurora Global, FSx ONTAP, Global Accelerator, Argo CD | Kịch bản Planned DR đo được `47.429 giây`; toàn bộ hạ tầng đã được dọn dẹp sạch theo tài liệu | Đã chứng minh năng lực Multi-Region DR; còn thiếu chiều sâu về bảo mật mạng nội bộ & kiểm tra gói tin |
| **SRE Platform** | EKS Multi-AZ, GitOps, giám sát vận hành, Karpenter, KEDA, canary, chaos | Có hình ảnh và bằng chứng; cấu hình IaC và manifest còn tình trạng lệch pha (drift) | Chưa có phân đoạn TGW (segmentation), GWLB/GENEVE và cụm tường lửa tập trung |

> **Khoảng trống portfolio giải quyết trong Dự án 6:** Cần một dự án tập trung chuyên sâu vào **AWS Advanced Networking trên DUY NHẤT 1 VÙNG Singapore (`ap-southeast-1`)**, kết hợp: **TGW Route Segmentation**, **Gateway Load Balancer (GWLB) giải mã GENEVE**, **Cụm Suricata EC2 IDS/IPS kiểm soát luồng Đông - Tây (East-West)**, **AWS Network Firewall kiểm soát tập trung luồng ra Internet (Centralized Egress)**, **Định tuyến đối xứng (Symmetric Routing với Appliance Mode)**, và **bằng chứng xử lý sự cố mạng thực tế (GameDay)** trên 2 cụm Kubernetes EKS riêng biệt.

---

## 2. Kiến Trúc Mạng Single-Region (Singapore `ap-southeast-1` Multi-AZ)

Toàn bộ 4 VPCs và 2 cụm Kubernetes EKS đều được triển khai tập trung trong **Region Singapore (`ap-southeast-1`)**, trải đều trên 2 Vùng sẵn sàng: `ap-southeast-1a` và `ap-southeast-1b`.

```text
                                  Internet
                                     |
                                  Route 53
                                     |
                              ALB + AWS WAF
                                     |
    +-----------------------------------------------------------------+
    | VPC Edge EKS — 10.40.0.0/16 [ap-southeast-1a/b]                 |
    | - Subnet Public: Cụm Ingress ALB (10.40.0.0/24, 10.40.1.0/24)   |
    | - Subnet Private: Các Node Edge EKS (frontend, auth-service)    |
    | - Subnet TGW: Giao diện mạng kết nối TGW (Attachment ENIs)      |
    +-----------------------------------------------------------------+
                                     |
                    [ Transit Gateway (fabric-tgw) ]
                                     |
    +-----------------------------------------------------------------+
    | VPC Inspection — 10.70.0.0/16 [ap-southeast-1a/b]               |
    | - Subnet TGW: ENI TGW (Đã BẬT Appliance Mode = ENABLED)         |
    | - Subnet GWLBe: Điểm cuối VPC kết nối tới GWLB (Endpoint A & B) |
    | - Subnet Tường lửa: Cụm máy chủ ảo Suricata EC2 (GENEVE 6081)  |
    |   <---> Gateway Load Balancer (GWLB)                            |
    +-----------------------------------------------------------------+
                                     |
                    [ Transit Gateway (fabric-tgw) ]
                                     |
    +-----------------------------------------------------------------+
    | VPC Core EKS — 10.50.0.0/16 [ap-southeast-1a/b]                 |
    | - Subnet Private: Node Core EKS (order, inventory, payment)     |
    | - Subnet Dữ liệu: Aurora PostgreSQL, ElastiCache Redis, SQS VPCE|
    | - Subnet TGW: Giao diện mạng kết nối TGW (Attachment ENIs)      |
    +-----------------------------------------------------------------+
                                     |
                               0.0.0.0/0 qua TGW
                                     |
    +-----------------------------------------------------------------+
    | VPC Centralized Egress — 10.80.0.0/16 [ap-southeast-1a/b]       |
    | - Subnet TGW: Giao diện mạng kết nối TGW (Attachment ENIs)      |
    | - Subnet Tường lửa: Điểm cuối AWS Network Firewall (AZ-A, AZ-B) |
    | - Subnet Public: Cổng NAT (NAT GW A & B) và Cổng Internet IGW   |
    +-----------------------------------------------------------------+
                                     |
                                  Internet
```

---

## 3. Chiến Lược Phân Tầng Bảo Mật & Kiểm Soát Chuyên Sâu (Phòng Thủ Đa Tầng)

### 3.1 Các Lớp Kiểm Soát An Ninh Mạng

| Lớp Kiểm Soát | Công Nghệ Áp Dụng | Phạm Vi & Trách Nhiệm Cụ Thể |
|---|---|---|
| **Lớp 7 Chiều Vào (Inbound L7)** | AWS WAF v2 | Gắn trực tiếp tại ALB: Ngăn chặn OWASP Top 10, danh tiếng IP độc hại, giới hạn tần suất truy cập (rate limiting), áp dụng quy trình Đếm trước - Chặn sau (Count-to-Block). |
| **Biên Giới Tài Nguyên (Workload Boundary)** | Security Groups | Tường lửa có trạng thái (Stateful) ở cấp độ giao diện mạng ENI của từng Pod, Node, ALB và VPC Endpoint. |
| **Hàng Rào Subnet (Subnet Guardrail)** | Network ACLs (NACL) | Tường lửa không trạng thái (Stateless) ở cấp độ Subnet, ngăn chặn lỗi rò rỉ định tuyến hoặc lệch cổng dịch vụ ngoài ý muốn. |
| **Nội Bộ Cụm Kubernetes (Pod-to-Pod)** | Kubernetes NetworkPolicy | Phân đoạn vi mô (micro-segmentation) trong cluster, mặc định chặn toàn bộ (default deny), chỉ mở cổng giữa các dịch vụ có khai báo rõ ràng. |
| **Kiểm Tra Luồng Đông - Tây (East-West Inspection)** | GWLB + Cụm Suricata EC2 | Giải mã và kiểm tra sâu toàn bộ gói tin qua giao thức GENEVE (UDP cổng 6081), phát hiện xâm nhập (IDS), ngăn chặn tấn công (IPS), chặn các cổng chưa được cấp phép. |
| **Kiểm Tra Luồng Ra Ngoài (Centralized Outbound Egress)** | AWS Network Firewall | Tường lửa kiểm soát trạng thái L3-L7 cho toàn bộ lưu lượng ra Internet, lọc danh sách tên miền được phép truy cập (domain allowlist) dựa trên TLS SNI. |
| **Phân Vùng Định Tuyến (Network Segmentation)** | Bảng Định Tuyến TGW (TGW Route Tables) | Tách biệt các miền định tuyến logic, điều phối chuỗi dịch vụ an ninh (service chaining), ngăn chặn việc kết nối tắt trực tiếp giữa các VPC. |

> **Nguyên tắc Thiết kế Cốt Lõi:** **Tuyệt đối không kết hợp GWLB và AWS Network Firewall trên cùng một luồng gói tin trong phiên bản MVP.**
> - Luồng nội bộ Đông - Tây (Edge <-> Core): `Edge VPC -> TGW -> Inspection VPC (GWLB + Suricata) -> TGW -> Core VPC`.
> - Luồng ra ngoài Internet (Edge/Core -> Internet): `VPC gửi -> TGW -> Egress VPC (AWS Network Firewall -> NAT Gateway -> IGW)`.
> Việc tách biệt này giúp loại bỏ tình trạng kiểm tra trùng lặp (double inspection), giảm độ trễ tối đa và tránh việc mơ hồ khi phân tích nguyên nhân sự cố mạng.

### 3.2 Các Miền Định Tuyến Transit Gateway (TGW Route Domains)

Hệ thống tắt hoàn toàn tính năng tự động liên kết (`Default Association`) và tự động quảng bá (`Default Propagation`) trên Transit Gateway để kiểm soát tuyệt đối từng bảng định tuyến.

| Bảng Định Tuyến TGW | VPC Attachment Được Gắn Kết | Cấu Hình Tuyến Đường (Routes) | Mục Đích Thiết Kế |
|---|---|---|---|
| `edge-rt` | Edge VPC Attachment | - `10.50.0.0/16` -> Inspection VPC Attachment<br>- `0.0.0.0/0` -> Egress VPC Attachment | Bắt buộc gói tin sang Core phải đi qua cụm GWLB kiểm tra; gói tin ra Internet phải vào Egress VPC. |
| `core-rt` | Core VPC Attachment | - `10.40.0.0/16` -> Inspection VPC Attachment<br>- `0.0.0.0/0` -> Egress VPC Attachment | Bắt buộc gói tin về Edge phải đi qua cụm GWLB kiểm tra; gói tin ra Internet phải vào Egress VPC. |
| `inspection-rt` | Inspection VPC Attachment | - `10.40.0.0/16` -> Edge VPC Attachment<br>- `10.50.0.0/16` -> Core VPC Attachment | Chuyển tiếp các gói tin hợp lệ sau khi đã được kiểm duyệt về đúng VPC đích. |
| `egress-rt` | Egress VPC Attachment | - `10.40.0.0/16` -> Edge VPC Attachment<br>- `10.50.0.0/16` -> Core VPC Attachment | Định tuyến gói tin phản hồi từ Internet về đúng VPC ban đầu đã khởi tạo kết nối. |
| `dev-rt` *(Mở rộng)* | Dev Test VPC Attachment | - `10.40.0.0/16` -> Blackhole (Hố đen)<br>- `10.50.0.0/16` -> Blackhole (Hố đen) | Chứng minh khả năng cô lập triệt để giữa môi trường Dev và môi trường Production. |

### 3.3 Đảm Bảo Định Tuyến Đối Xứng (Symmetric Routing) Với TGW Appliance Mode

- Khi lưu lượng mạng đi qua cụm tường lửa kiểm tra trạng thái trên nhiều Availability Zones trong Region Singapore, tất cả các gói tin thuộc cùng một phiên kết nối (cả chiều đi và chiều về) **bắt buộc phải đi qua cùng một máy chủ tường lửa/điểm cuối trong cùng một AZ** (`ap-southeast-1a` hoặc `ap-southeast-1b`). Nếu bị lệch AZ, phiên kết nối TCP sẽ bị đứt do không đồng bộ trạng thái (asymmetric routing drop).
- **Yêu cầu kỹ thuật bắt buộc:**
  - Bật cấu hình **`ApplianceModeSupport = enable`** trên TGW VPC Attachment gắn vào **Inspection VPC**.
  - Tách biệt độc lập 3 lớp subnet trong từng AZ tại Inspection VPC:
    1. Subnet dành riêng cho giao diện mạng của TGW (kích thước tối thiểu `/28`).
    2. Subnet dành cho điểm cuối GWLB Endpoint (GWLBe).
    3. Subnet dành cho máy chủ ảo Suricata EC2.

---

## 4. Kế Hoạch Phân Bổ Dải Mạng CIDR (Singapore `ap-southeast-1`)

Dự án thiết kế dải IP riêng tư không chồng lấn trong Region Singapore:

| Tên VPC | Dải Mạng Chính (CIDR) | Phân Bổ Subnet Chi Tiết (Tại `ap-southeast-1a` & `ap-southeast-1b`) |
|---|---|---|
| **VPC Edge EKS** | `10.40.0.0/16` | - Subnet Public (ALB Ingress): `10.40.0.0/24`, `10.40.1.0/24`<br>- Subnet Private Node: `10.40.8.0/22`, `10.40.12.0/22`<br>- Subnet Private Pod (Secondary CIDR): `10.40.64.0/18`<br>- Subnet VPC Endpoints: `10.40.20.0/24`, `10.40.21.0/24`<br>- Subnet TGW Attachment: `10.40.250.0/28`, `10.40.250.16/28` |
| **VPC Core EKS** | `10.50.0.0/16` | - Subnet Private Node: `10.50.8.0/22`, `10.50.12.0/22`<br>- Subnet Private Pod (Secondary CIDR): `10.50.64.0/18`<br>- Subnet Dữ liệu (Aurora/Redis): `10.50.20.0/24`, `10.50.21.0/24`<br>- Subnet VPC Endpoints: `10.50.30.0/24`, `10.50.31.0/24`<br>- Subnet TGW Attachment: `10.50.250.0/28`, `10.50.250.16/28` |
| **VPC Kiểm Tra (Inspection)** | `10.70.0.0/16` | - Subnet TGW Attachment: `10.70.0.0/28`, `10.70.0.16/28`<br>- Subnet GWLB Endpoint (GWLBe): `10.70.1.0/28`, `10.70.1.16/28`<br>- Subnet Máy chủ Tường lửa Suricata: `10.70.10.0/24`, `10.70.11.0/24` |
| **VPC Cổng Ra (Egress)** | `10.80.0.0/16` | - Subnet TGW Attachment: `10.80.0.0/28`, `10.80.0.16/28`<br>- Subnet Điểm cuối Network Firewall: `10.80.1.0/28`, `10.80.1.16/28`<br>- Subnet Public (NAT Gateway & IGW): `10.80.10.0/24`, `10.80.11.0/24` |

---

## 5. Bố Trí Dịch Vụ Ứng Dụng (Workload Topology - Sử Dụng Bộ Mã Nguồn `app3`)

Tận dụng toàn bộ các dịch vụ microservices từ `app3`, phân bổ khoa học giữa 2 cụm Kubernetes EKS hoàn toàn riêng tư trong Region Singapore:

### Cụm Edge EKS (Biên tiếp nhận kết nối công khai)
- **`frontend`**: Nhận yêu cầu từ người dùng Internet thông qua ALB Ingress và AWS WAF. Gọi xác thực nội bộ tới `auth-service` hoặc gọi backend Core qua tên miền nội bộ bảo mật `https://core.internal.fabric`.
- **`auth-service`**: Quản lý phiên đăng nhập, tạo và xác thực tính hợp lệ của JWT token.

### Cụm Core EKS (Khu vực xử lý dữ liệu nghiệp vụ quan trọng)
- **`order-service`**: Xử lý logic đặt hàng, lưu trữ giao dịch an toàn vào cơ sở dữ liệu Aurora PostgreSQL Serverless v2.
- **`inventory-service`**: Quản lý số lượng tồn kho, bộ đệm dữ liệu tốc độ cao qua ElastiCache Redis.
- **`payment-worker`**: Lắng nghe hàng đợi bất đồng bộ qua AWS SQS (truy cập qua VPC Endpoint nội bộ) để thực hiện thanh toán.

---

## 6. Lộ Trình Triển Khai 12 Giai Đoạn (Phases 0 - 12)

| Giai Đoạn | Tên Giai Đoạn | Mục Tiêu & Kết Quả Bàn Giao Cụ Thể (Deliverables) |
|---|---|---|
| **Giai đoạn 0** | **Kiểm Kê Tài Nguyên (Inventory)** | Sử dụng lệnh chỉ đọc (read-only) qua AWS MCP (`aws-api-mcp/call_aws`) kiểm kê tài nguyên trên Region Singapore (`ap-southeast-1`); xác nhận môi trường sạch không trùng lặp dải mạng. |
| **Giai đoạn 1** | **Thiết Kế & Mô Hình Đe Dọa (Design & Threat Model)** | Hoàn thiện tài liệu phân tích rủi ro STRIDE, lập ma trận định tuyến TGW, xây dựng bảng hop-by-hop packet flow và ranh giới kiểm soát chi phí (Cost Boundary $50). |
| **Giai đoạn 2** | **Thiết Lập Hạ Tầng Mạng Cơ Bản (Foundation)** | Triển khai mã Terraform cho 4 VPCs, chia subnets theo 2 AZs tại Singapore, khởi tạo Transit Gateway, tắt default propagation, cấu hình route tables và kích hoạt VPC Flow Logs. |
| **Giai đoạn 3** | **Cụm Kubernetes EKS Kép (Dual EKS)** | Triển khai 2 cụm EKS hoàn toàn riêng tư (`edge-eks` và `core-eks`) tại `ap-southeast-1`, cấu hình EKS Pod Identity, mã hóa Secrets bằng khóa KMS chuyên biệt, cài đặt Argo CD và NetworkPolicy. |
| **Giai đoạn 4** | **Triển Khai Ứng Dụng (Workloads)** | Đưa các container microservices từ repo app lên 2 cụm; thiết lập Route 53 Private Hosted Zone (`internal.fabric`), chứng chỉ số TLS nội bộ và Internal NLB cho Core Ingress. |
| **Giai đoạn 5** | **Cụm Kiểm Tra GWLB & Suricata IDS/IPS** | Triển khai Gateway Load Balancer, các điểm cuối GWLBe tại VPC Inspection, dựng 2 máy chủ ảo Suricata EC2 hỗ trợ giao thức GENEVE; kiểm tra luồng định tuyến đối xứng. |
| **Giai đoạn 6** | **Tường Lửa Ra Ngoài Tập Trung (Centralized Egress)** | Khởi tạo AWS Network Firewall tại VPC Egress, cấu hình bộ quy tắc Suricata stateful rules, triển khai cụm NAT Gateway riêng theo từng AZ; thiết lập danh sách tên miền cho phép đi ra Internet. |
| **Giai đoạn 7** | **Cổng Vào Biên & Tường Lửa Ứng Dụng (Ingress & WAF)** | Cấu hình Route 53 công khai, cấp phát chứng chỉ ACM, tạo Application Load Balancer công khai và gắn AWS WAF v2 (chế độ Count sau đó chuyển sang Block), thu thập log truy cập WAF. |
| **Giai đoạn 8** | **Tự Động Hóa CI/CD & DevSecOps** | Xây dựng pipeline kiểm thử tự động Terraform (kiểm tra cú pháp, quét bảo mật bằng `checkov`), quét lỗ hổng ảnh container (`trivy`), xuất hóa đơn phần mềm (SBOM), ký số ảnh container bằng `cosign`, sử dụng mã băm bất biến (immutable digest). |
| **Giai đoạn 9** | **Hệ Thống Quan Sát Toàn Diện (Observability)** | Tập trung hóa VPC Flow Logs, nhật ký TGW Logs, cảnh báo AWS Network Firewall, nhật ký sự kiện Suricata `eve.json` và ALB access logs; kiểm thử luồng truyền thông qua VPC Reachability Analyzer. |
| **Giai đoạn 10** | **Kịch Bản Diễn Tập Sự Cố Mạng (GameDay Scenarios)** | Tiến hành các kịch bản phá vỡ thực tế: Làm rò rỉ tuyến đường (route leak), tạo bất đối xứng luồng gói tin, tắt cưỡng bức 1 node Suricata, kiểm tra tường lửa drop gói tin độc hại, mô phỏng lỗi đường về từ NAT. |
| **Giai đoạn 11** | **Báo Cáo Bằng Chứng & Sự Cố (Evidence & Incident Report)** | Thu thập dữ liệu log thực tế kèm dấu thời gian (timestamp), sơ đồ đường đi gói tin thực tế, lập báo cáo phân tích sau sự cố (post-mortem) và tổng hợp bảng chi phí tiêu hao trong quá trình thực nghiệm. |
| **Giai đoạn 12** | **Dọn Dẹp Hạ Tầng Triệt Để (Cleanup)** | Thực hiện quy trình hủy tài nguyên theo thứ tự phụ thuộc ngược (Reverse Cleanup Dependency Order); dùng công cụ kiểm kê tự động xác nhận tài nguyên tính phí đã trở về đúng mức **$0.00**. |

---

## 7. Tiêu Chí Đánh Giá Hoàn Thành (PASS Criteria)

Tất cả tiêu chí đánh giá bắt buộc phải có **bằng chứng chạy thực tế kèm dấu thời gian (raw runtime evidence with timestamp)** trong Region Singapore:

1. **Kiểm tra luồng Đông - Tây:** Ứng dụng `frontend` (tại Edge) gọi thành công tới `order-service` (tại Core) qua cổng `443` thông qua điểm cuối GWLBe và máy chủ Suricata.
2. **Khả năng ngăn chặn của Suricata:** Gói tin thử nghiệm gửi tới cổng trái phép hoặc mang chữ ký tấn công giả lập bị Suricata drop ngay lập tức và xuất hiện cảnh báo trong `eve.json`.
3. **Hiệu quả phân đoạn mạng:** Máy chủ thử nghiệm tại phân vùng Dev không thể kết nối tới bất kỳ địa chỉ IP nào của phân vùng Prod nhờ cơ chế định tuyến TGW Blackhole.
4. **Kiểm soát tên miền ra ngoài:** Các Pod trong cụm Core EKS truy cập thành công các tên miền nằm trong danh sách cho phép (ví dụ `quay.io`, `github.com`) thông qua AWS Network Firewall.
5. **Chặn lưu lượng ra ngoài trái phép:** Kết nối tới các địa chỉ IP hoặc tên miền không nằm trong danh mục bị AWS Network Firewall chặn đứng và ghi nhận trong nhật ký `DROP`/`ALERT`.
6. **Xác nhận định tuyến đối xứng:** Bằng chứng bắt gói tin (`tcpdump`) trên máy chủ Suricata chứng minh toàn bộ gói tin yêu cầu và phản hồi đều đi qua cùng một máy chủ trong cùng một AZ (`ap-southeast-1a` hoặc `ap-southeast-1b`).
7. **Khả năng tự phục hồi của cụm tường lửa:** Tắt hoặc cô lập 1 máy chủ Suricata, Gateway Load Balancer tự động loại bỏ mục tiêu lỗi ra khỏi nhóm trong vài giây, các kết nối mạng duy trì liên tục qua máy chủ còn lại.
8. **Kiểm chứng khả năng tiếp cận mạng:** Sử dụng công cụ AWS VPC Reachability Analyzer phân tích thành công đường dẫn kết nối và phát hiện chính xác khi cố tình tạo lỗi cấu hình Route hoặc NACL.
9. **An toàn chuỗi cung ứng phần mềm:** 100% container images triển khai trên cụm EKS được ghim trực tiếp bằng mã băm cố định `@sha256:...`, không dùng tag nổi `:latest`, tuyệt đối không lưu static credential của AWS trong mã nguồn.

---

## 8. Danh Mục Các Bài Thực Hành Tham Chiếu (Reference Knowledge Base)

- [Bài thực hành 274 — Phân đoạn mạng với Transit Gateway](file:///E:/repo/lab-aws/network-advance/labs/Lab%20274%20-%20Transit%20Gateway%20Segmentation.md)
- [Bài thực hành 275 — Cổng ra Internet tập trung với Transit Gateway](file:///E:/repo/lab-aws/network-advance/labs/Lab%20275%20-%20Centralized%20Egress%20with%20Transit%20Gateway.md)
- [Bài thực hành 280 — Kiểm tra lưu lượng với Gateway Load Balancer](file:///E:/repo/lab-aws/network-advance/labs/Lab%20280%20-%20Gateway%20Load%20Balancer%20Inspection.md)
- [Bài thực hành 281 — Kiểm soát cổng ra với AWS Network Firewall](file:///E:/repo/lab-aws/network-advance/labs/Lab%20281%20-%20AWS%20Network%20Firewall%20Egress.md)
- [Bài thực hành 282 — So sánh ALB và NLB về quản lý TLS và Source IP](file:///E:/repo/lab-aws/network-advance/labs/Lab%20282%20-%20ALB%20NLB%20TLS%20and%20Source%20IP.md)
- [Bài thực hành 283 — Tích hợp CloudFront, AWS WAF và OAC](file:///E:/repo/lab-aws/network-advance/labs/Lab%20283%20-%20CloudFront%20WAF%20and%20OAC.md)
- [Bài thực hành 288 — Khắc phục và giám sát sự cố an ninh mạng chuyên sâu](file:///E:/repo/lab-aws/network-advance/labs/Lab%20288%20-%20Network%20Observability%20Incident%20Lab.md)

---

## 9. Phạm Vi Giới Hạn & Ranh Giới Nghiêm Ngặt (Strictly Single-Region Scope)

- **TUYỆT ĐỐI KHÔNG TRIỂN KHAI:** 
  - Không triển khai định tuyến xuyên Vùng (Multi-Region Routing) hay Cross-Region Peering.
  - Không triển khai AWS Global Accelerator liên vùng.
  - Không triển khai kết nối đường truyền vật lý AWS Direct Connect hoặc mạng diện rộng ảo AWS Cloud WAN.
  - Không triển khai AWS Firewall Manager (liên quan đến AWS Organizations).
- **RANH GIỚI BẮT BUỘC:** Tập trung 100% vào **Single-Region Advanced Networking (`ap-southeast-1` Singapore)** với mô hình phân chia nhiều VPCs trên cùng một Region và định tuyến an toàn qua Transit Gateway, GWLB và Network Firewall.
