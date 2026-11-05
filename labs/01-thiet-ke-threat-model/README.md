# Module 01: Thiết Kế Kiến Trúc & Mô Hình Đe Dọa (Threat Model)

## 1. Mục Tiêu Thiết Kế
- **Mục tiêu:** 
  - Hoàn thiện mô hình phân tích mối đe dọa an ninh mạng theo chuẩn **STRIDE** cho hệ thống Dual EKS và Centralized Inspection.
  - Xây dựng ma trận định tuyến (Routing Matrix) logic trên Transit Gateway.
  - Thiết kế bảng đường đi gói tin từng chặng (Hop-by-Hop Packet Flow) cho cả 2 luồng: East-West (qua GWLB) và North-South (qua Network Firewall).
  - Xác lập ranh giới chi phí (Cost Boundary) cho từng thành phần (NAT, GWLB, Firewall).

---

## 2. Mô Hình Phân Tích Đe Dọa (STRIDE Threat Model)

| Phân Loại STRIDE | Nguy Cơ Tiềm Ẩn | Biện Pháp Kiểm Soát & Khắc Phục Trong Thiết Kế |
|---|---|---|
| **Spoofing (Giả mạo danh tính)** | Giả mạo IP từ VPC này sang VPC khác | Bật Reverse Path Filtering (rp_filter) trên Suricata; NACL stateless chặn IP spoofed. |
| **Tampering (Can thiệp gói tin)** | Can thiệp hoặc sửa đổi dữ liệu khi truyền giữa Edge và Core | Bắt buộc mTLS hoặc TLS 1.3 nội bộ giữa Frontend và Backend; mã hóa đường truyền TGW. |
| **Repudiation (Chối bỏ trách nhiệm)** | Tấn công không để lại dấu vết trong mạng nội bộ | Bật VPC Flow Logs cấp độ `ALL`, TGW Flow Logs, và lưu trữ Suricata `eve.json` tập trung. |
| **Information Disclosure (Lộ lọt thông tin)** | Dữ liệu nhạy cảm rò rỉ ra Internet qua outbound channels | Chặn toàn bộ direct Internet access; buộc qua AWS Network Firewall lọc domain SNI allowlist. |
| **Denial of Service (Từ chối dịch vụ)** | Tấn công SYN Flood hoặc DDoS từ Internet vào hệ thống | Tích hợp AWS Shield Standard + AWS WAF v2 Rate Limiting tại tầng Edge ALB Ingress. |
| **Elevation of Privilege (Leo thang đặc quyền)** | Pod bị chiếm quyền cố gắng quét ngang sang Database nội bộ | TGW Blackhole cô lập môi trường Dev; Kubernetes NetworkPolicy mặc định chặn toàn bộ (Default Deny). |

---

## 3. Bảng Phân Tích Đường Đi Gói Tin Từng Chặng (Hop-by-Hop Flow)

### Luồng 1: East-West (Frontend Edge gọi Order Core qua cổng 443)
```text
[Frontend Pod (10.40.10.x)]
  --> Subnet Route Table: 10.50.0.0/16 trỏ về TGW Attachment ENI
  --> TGW edge-rt: 10.50.0.0/16 trỏ về Inspection VPC Attachment
  --> TGW Subnet trong Inspection VPC: Nhận gói tin (Appliance Mode = ON)
  --> Inspection TGW Subnet Route Table: 10.50.0.0/16 trỏ về GWLBe-a (10.70.1.x)
  --> GWLBe đóng gói gói tin vào GENEVE tunnel (UDP 6081) chuyển tới Suricata EC2
  --> Suricata EC2 (10.70.10.x): Giải mã GENEVE, kiểm tra IDS/IPS signature
  --> Suricata gửi lại gói tin hợp lệ về GWLB qua GENEVE
  --> GWLB chuyển tiếp gói tin ra khỏi GWLBe
  --> GWLBe Subnet Route Table: 10.50.0.0/16 trỏ về TGW Attachment ENI
  --> TGW inspection-rt: 10.50.0.0/16 trỏ về Core VPC Attachment
  --> Core VPC TGW Subnet: Nhận gói tin và chuyển tiếp theo Core Route Table
  --> [Order Service Pod (10.50.10.x)]
```

### Luồng 2: North-South Egress (Core Pod tải gói từ quay.io qua cổng 443)
```text
[Core Pod (10.50.10.x)]
  --> Subnet Route Table: 0.0.0.0/0 trỏ về TGW Attachment ENI
  --> TGW core-rt: 0.0.0.0/0 trỏ về Egress VPC Attachment
  --> Egress TGW Subnet Route Table: 0.0.0.0/0 trỏ về AWS Network Firewall Endpoint
  --> AWS Network Firewall: Kiểm tra TLS Client Hello SNI (quay.io thuộc Allowlist)
  --> Gói tin được chuyển tiếp tới Public Subnet Route Table
  --> NAT Gateway A (10.80.10.x) thực hiện SNAT chuyển thành Elastic IP công khai
  --> Internet Gateway (IGW) --> Internet (quay.io)
```

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [x] Bảng định tuyến chi tiết không có vòng lặp (No routing loop).
- [x] Ma trận phân tách rõ ràng, không có kết nối trực tiếp (no direct peering) giữa Edge và Core.
- [x] Ranh giới chi phí dự kiến duy trì dưới $50.00 cho phiên chạy GameDay (`fabric-project6-monthly-budget` đã kích hoạt).

