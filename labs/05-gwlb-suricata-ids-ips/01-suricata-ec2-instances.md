# 05.01 — Khởi Tạo 2 Máy Chủ Ảo Suricata EC2 Hỗ Trợ Đóng Gói GENEVE (UDP 6081)

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Thiết lập cụm thiết bị an ninh kiểm tra sâu gói tin (IDS/IPS) trên 2 Availability Zones trong Inspection VPC.

---

## 1. Mục Tiêu Kỹ Thuật

- Khởi tạo 2 máy chủ ảo EC2 (chạy Ubuntu 22.04 LTS hoặc Amazon Linux 2023) trong `fabric-inspection-vpc`:
  1. `fabric-suricata-appliance-1a` tại `fabric-inspection-fw-1a` (`10.70.10.0/24`).
  2. `fabric-suricata-appliance-1b` tại `fabric-inspection-fw-1b` (`10.70.11.0/24`).
- **Tắt thuộc tính Source/Destination Check** trên giao diện mạng ENI của cả 2 máy chủ (bắt buộc để EC2 có thể chuyển tiếp gói tin của IP khác).
- Cài đặt và cấu hình phần mềm **Suricata** để giải mã giao thức đường hầm **GENEVE (Cổng UDP 6081)** từ Gateway Load Balancer.

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Tạo Security Group Cho Suricata Appliance
1. Mở dịch vụ **EC2 Console** tại Singapore (`ap-southeast-1`) -> Chọn **Security Groups** -> Nhấp **Create security group**.
2. **Cấu hình Security Group:**
   - **Name:** `fabric-suricata-appliance-sg`
   - **Description:** `Security group for Suricata IDS/IPS appliance instances`
   - **VPC:** Chọn `fabric-inspection-vpc`.
3. **Inbound rules:**
   - **Rule 1 (GENEVE Traffic từ GWLB):** Type: `Custom UDP`, Port range: `6081`, Source: `10.70.0.0/16` (Dải mạng nội bộ Inspection VPC).
   - **Rule 2 (Health Check từ GWLB):** Type: `TCP`, Port range: `80` (hoặc `8080`), Source: `10.70.0.0/16`.
   - **Rule 3 (SSH Quản trị nội bộ):** Type: `SSH`, Port range: `22`, Source: `10.40.0.0/16` (Chỉ từ Edge Private).
4. Nhấp **Create security group**.

---

### Bước 2: Khởi Tạo 2 Máy Chủ Ảo EC2
1. Tại EC2 Console, chọn **Instances** -> Nhấp nút cam **Launch instances**.
2. **Cấu hình Instance 1 (AZ-a):**
   - **Name:** `fabric-suricata-appliance-1a`
   - **Application and OS Images:** Chọn `Ubuntu Server 22.04 LTS (HVM)` hoặc `Amazon Linux 2023`.
   - **Instance type:** Chọn `c6i.large` (2 vCPU, 4 GiB RAM - Tối ưu tính toán mạng).
   - **Key pair:** Chọn key pair quản trị của bạn (hoặc kết nối qua AWS Systems Manager Session Manager).
   - **Network settings (Nhấp Edit):**
     - **VPC:** `fabric-inspection-vpc`.
     - **Subnet:** Chọn `fabric-inspection-fw-1a`.
     - **Auto-assign public IP:** `Disable` (Máy chủ hoàn toàn riêng tư).
     - **Firewall (security groups):** Chọn `fabric-suricata-appliance-sg`.
   - **Storage:** Giữ nguyên 20 GiB gp3.
   - Nhấp **Launch instance**.
3. **Lặp lại cho Instance 2 (AZ-b):**
   - **Name:** `fabric-suricata-appliance-1b`.
   - **Subnet:** Chọn `fabric-inspection-fw-1b`.
   - Nhấp **Launch instance**.

---

### Bước 3: Tắt Source/Destination Check Trên Cả 2 ENIs (BẮT BUỘC)
> [!IMPORTANT]
> Mặc định AWS EC2 sẽ drop các gói tin có IP nguồn hoặc IP đích không khớp với IP của chính instance đó. Với firewall trung gian (Network Appliance), bắt buộc phải tắt tính năng kiểm tra này.

1. Tại danh sách **Instances**, chọn `fabric-suricata-appliance-1a`.
2. Nhấp menu **Actions** ở góc trên -> Chọn **Networking** -> Chọn **Change source/dest check**.
3. Bỏ tích chọn (hoặc chọn radio button **Stop**) -> Nhấp **Save**.
4. Lặp lại thao tác trên cho `fabric-suricata-appliance-1b`.

---

### Bước 4: Thiết Lập Giao Diện GENEVE & Cấu Hình Suricata
Sau khi kết nối vào máy chủ qua SSM Session Manager:
1. Tạo giao diện đường hầm GENEVE:
```bash
sudo ip link add name geneve0 type geneve id 0 remote <gwlb-endpoint-ip> dstport 6081
sudo ip link set geneve0 up
```
2. Cấu hình Suricata lắng nghe trên giao diện `geneve0` trong file `/etc/suricata/suricata.yaml`.
3. Bật dịch vụ Suricata:
```bash
sudo systemctl enable --now suricata
```

---

## 3. Xác Minh (Verification)

Kiểm tra Source/Dest Check đã tắt qua AWS CLI:
```bash
aws ec2 describe-instances \
  --region ap-southeast-1 \
  --filters "Name=tag:Name,Values=fabric-suricata-appliance-*" \
  --query 'Reservations[*].Instances[*].{Name:Tags[?Key==`Name`].Value | [0],SourceDestCheck:SourceDestCheck,State:State.Name}' \
  --output table
```
> Kết quả: `SourceDestCheck = False` cho cả 2 máy chủ.

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] 2 máy chủ Suricata EC2 ở trạng thái `running` tại 2 AZs độc lập (`1a` và `1b`).
- [ ] `SourceDestCheck` của cả 2 máy chủ đều được tắt thành công (`False`).

