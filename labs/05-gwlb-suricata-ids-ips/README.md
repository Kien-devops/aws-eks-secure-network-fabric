# Module 05: Cụm Kiểm Tra Tập Trung GWLB & Suricata IDS/IPS

## 1. Mục Tiêu Kỹ Thuật
- **Mục tiêu:**
  - Triển khai AWS Gateway Load Balancer (GWLB) trong `fabric-inspection-vpc`.
  - Khởi tạo 2 máy chủ ảo EC2 chạy phần mềm IDS/IPS mã nguồn mở **Suricata** trên 2 AZs (`ap-southeast-1a` và `ap-southeast-1b`).
  - Thiết lập giao thức đóng gói **GENEVE (UDP port 6081)** giữa GWLB và Suricata instances.
  - Tạo 2 GWLB VPC Endpoints (GWLBe) trong Inspection VPC.
  - Cấu hình TGW Route Tables và Inspection Subnet Route Tables để toàn bộ lưu lượng East-West giữa Edge và Core đều đi qua GWLB.
  - Kiểm chứng **Symmetric Routing** (Định tuyến đối xứng) thông qua TGW Appliance Mode.

---

## 2. Kiến Trúc Inspection VPC & Dòng Chảy GENEVE

```text
[TGW Attachment ENI (Inspection VPC)]
                  |
                  v (Bảng Route trỏ 10.50.0.0/16 sang GWLBe)
[GWLB Endpoint (GWLBe)]
                  |
                  v (GENEVE Tunnel - UDP 6081)
[Gateway Load Balancer (GWLB)]
                  |
                  v
[Suricata EC2 Instance (AZ-a hoặc AZ-b)]
  - Lắng nghe giao diện geneve0
  - Phân tích signature, phát hiện mã độc, kiểm soát cổng
  - Trả gói tin hợp lệ trở lại GWLB
                  |
                  v
[GWLBe] --> [TGW Attachment ENI] --> [Transit Gateway] --> [Core VPC]
```

---

## 3. Các Bước Thực Hiện Chi Tiết

### Bước 1: Khởi tạo Máy Chủ Ảo Suricata EC2
1. Khởi tạo 2 máy chủ EC2 (Instance Type: `c6i.large` hoặc `c6a.large`, OS: Amazon Linux 2023 hoặc Ubuntu 22.04) tại 2 Subnet `Firewall EC2 Subnet` (1a và 1b).
2. Tắt kiểm tra Source/Destination check trên ENI của cả 2 máy chủ:
   ```bash
   aws ec2 modify-instance-attribute --instance-id <instance-id> --no-source-dest-check --region ap-southeast-1
   ```
3. Cài đặt Suricata và thiết lập driver GENEVE lắng nghe cổng UDP `6081`.

### Bước 2: Tạo Gateway Load Balancer & Target Group
1. Khởi tạo GWLB Target Group với giao thức `GENEVE` (Cổng 6081), Health check cổng TCP 80 hoặc HTTP 80/health.
2. Đăng ký 2 máy chủ Suricata vào Target Group.
3. Tạo Gateway Load Balancer trong Inspection Subnets và gắn Target Group tương ứng.

### Bước 3: Tạo VPC Endpoint Service & GWLB Endpoints
1. Khởi tạo VPC Endpoint Service trỏ vào Gateway Load Balancer.
2. Tạo 2 GWLB Endpoints (GWLBe-a và GWLBe-b) đặt tại Subnet `GWLBe Subnet` của từng AZ.

### Bước 4: Cấu hình Bảng Định Tuyến Định Hướng Luồng (Service Chaining)
- **Bảng định tuyến Subnet TGW trong Inspection VPC:**
  - Đích `10.50.0.0/16` trỏ tới `gwlbe-a` (tại AZ-a) và `gwlbe-b` (tại AZ-b).
- **Bảng định tuyến Subnet GWLBe trong Inspection VPC:**
  - Đích `10.50.0.0/16` trỏ tới `tgw-attachment-id`.
  - Đích `10.40.0.0/16` trỏ tới `tgw-attachment-id`.

---

## 4. Xác Minh (Verification)
1. Từ `frontend` Pod, thực hiện request hợp lệ tới Core:
   ```bash
   curl -Iv https://order.internal.fabric/api/orders
   ```
   > Kết quả: Thành công (HTTP 200/401).
2. Kiểm tra `tcpdump` trên Suricata Instance để xác nhận gói tin được giải mã từ `geneve0`.

---

## 5. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Cả 2 target Suricata đều ở trạng thái `healthy` trên GWLB Target Group.
- [ ] Lưu lượng Edge -> Core đi qua đúng GWLBe và máy chủ Suricata.
- [ ] Bằng chứng `tcpdump` xác nhận cả chiều đi và chiều về của flow đều xử lý trên cùng 1 AZ (Symmetric Routing PASS).

