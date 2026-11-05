# Module 06: Kiểm Soát Luồng Ra Ngoài Tập Trung (Centralized Egress Firewall)

## 1. Mục Tiêu Kỹ Thuật
- **Mục tiêu:**
  - Khởi tạo **AWS Network Firewall** trong `fabric-egress-vpc` trải dài trên 2 AZs (`ap-southeast-1a` và `ap-southeast-1b`).
  - Thiết lập cụm **NAT Gateway độc lập cho từng AZ** trong Public Subnets để tránh lỗi định tuyến xuyên AZ (Cross-AZ traffic).
  - Cấu hình nhóm quy tắc lọc trạng thái (Stateful Rule Groups) dựa trên cú pháp Suricata để lọc tên miền qua TLS SNI (Domain Allowlist).
  - Cấu hình bảng định tuyến TGW `edge-rt` và `core-rt` định hướng mọi traffic `0.0.0.0/0` qua Egress VPC Attachment.
  - Kiểm chứng: Cho phép truy cập các domain thiết yếu (`quay.io`, `github.com`), drop toàn bộ các domain và địa chỉ IP ngoài danh mục.

---

## 2. Luồng Định Tuyến Chi Tiết (Egress Traffic Path)

```text
[Core EKS Workload]
        |
        v (Route 0.0.0.0/0 trỏ về TGW)
[TGW Attachment ENI (Egress VPC)]
        |
        v (Egress TGW Subnet Route Table trỏ 0.0.0.0/0 sang Firewall Endpoint)
[AWS Network Firewall Endpoint (AZ-a / AZ-b)]
        | (Kiểm tra TLS SNI: Cho phép nếu nằm trong Allowlist)
        v
[NAT Gateway (AZ-a / AZ-b)]
        | (SNAT sang Public IPv4)
        v
[Internet Gateway (IGW)] --> [Internet]
```

---

## 3. Các Bước Thực Hiện Chi Tiết

### Bước 1: Khởi tạo Quy Tắc Tường Lửa (Stateful Rule Group)
Tạo Rule Group loại `Domain list` hoặc `Suricata compatible`:
```text
# Domain Allowlist
.quay.io
.github.com
.docker.io
.registry-1.docker.io
.amazonaws.com
```
*Hành vi mặc định: Chặn toàn bộ các tên miền không nằm trong danh sách (Default Drop).*

### Bước 2: Khởi tạo AWS Network Firewall Policy & Firewall
1. Tạo Firewall Policy gắn Stateful Rule Group vừa tạo.
2. Khởi tạo AWS Network Firewall:
   - VPC: `fabric-egress-vpc`
   - Subnets: Chọn 2 Subnets `Firewall Endpoint Subnet` (1a và 1b).

### Bước 3: Khởi tạo NAT Gateway & Cấu hình Route Tables
1. Cấp phát 2 Elastic IPs độc lập.
2. Tạo NAT Gateway A tại Public Subnet 1a, NAT Gateway B tại Public Subnet 1b.
3. Cấu hình bảng định tuyến định tuyến 3 chặng:
   - **TGW Subnet Route Table:** `0.0.0.0/0` -> trỏ tới `Network Firewall Endpoint ID`.
   - **Firewall Subnet Route Table:** `0.0.0.0/0` -> trỏ tới `NAT Gateway ID` (tương ứng từng AZ).
   - **Public Subnet Route Table:** `0.0.0.0/0` -> trỏ tới `Internet Gateway (IGW)`.
   - **Đường về từ NAT:** `10.40.0.0/16` và `10.50.0.0/16` trỏ tới `tgw-attachment-id`.

---

## 4. Xác Minh (Verification)
1. **Kiểm tra luồng được phép:**
   Từ Core Pod, gọi tới `github.com`:
   ```bash
   curl -Iv https://github.com
   ```
   > Kết quả: Thành công (HTTP 200/301).
2. **Kiểm tra luồng bị cấm:**
   Gọi tới domain ngoài allowlist hoặc IP trực tiếp:
   ```bash
   curl -m 5 -Iv https://www.facebook.com
   curl -m 5 http://1.1.1.1
   ```
   > Kết quả: Connection timed out (Bị drop bởi Firewall).

---

## 5. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] AWS Network Firewall ở trạng thái `READY` trên cả 2 AZs.
- [ ] Truy cập ra ngoài tới domain cho phép thành công 100%.
- [ ] Truy cập domain hoặc IP bị cấm bị chặn đứng lập tức và xuất hiện log `DROP` trong CloudWatch Logs.
