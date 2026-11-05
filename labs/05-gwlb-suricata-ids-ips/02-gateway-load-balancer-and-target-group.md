# 05.02 — Khởi Tạo Gateway Load Balancer (GWLB) & Target Group GENEVE (Cổng 6081)

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Thiết lập cụm cân bằng tải tầng mạng trong suốt Gateway Load Balancer để điều phối luồng dữ liệu tới cụm Suricata.

---

## 1. Mục Tiêu Kỹ Thuật

- Khởi tạo Target Group với giao thức **GENEVE (Cổng 6081)** và đăng ký 2 máy chủ Suricata EC2.
- Khởi tạo **AWS Gateway Load Balancer (GWLB)** mang tên `fabric-gwlb` đặt tại các Subnet `Firewall EC2 Subnet` của Inspection VPC (`ap-southeast-1a` và `ap-southeast-1b`).
- Cấu hình cơ chế Health Check (TCP hoặc HTTP) để GWLB tự động phát hiện và loại bỏ node Suricata bị lỗi.

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Tạo Target Group Cho Gateway Load Balancer
1. Mở dịch vụ **EC2 Console** tại `ap-southeast-1` -> Menu bên trái chọn **Target groups** -> Nhấp **Create target group**.
2. **Basic configuration:**
   - **Target type:** Chọn **Instances**.
   - **Target group name:** `fabric-gwlb-tg`.
   - **Protocol:** Chọn **GENEVE** (Port tự động gán là `6081`).
   - **IP address type:** `IPv4`.
   - **VPC:** Chọn `fabric-inspection-vpc`.
3. **Health checks:**
   - **Health check protocol:** Chọn `TCP` (hoặc `HTTP`).
   - **Health check port:** Nhập `80` (hoặc cổng health check do script trên Suricata cung cấp).
   - **Advanced health check settings:**
     - Healthy threshold: `3`.
     - Unhealthy threshold: `3`.
     - Timeout: `5` giây.
     - Interval: `10` giây (để phát hiện lỗi nhanh).
4. Nhấp **Next**.
5. **Register targets:**
   - Tích chọn cả 2 máy chủ: `fabric-suricata-appliance-1a` và `fabric-suricata-appliance-1b`.
   - Cổng giữ nguyên: `6081`.
   - Nhấp nút **Include as pending below**.
6. Nhấp nút cam **Create target group**.

---

### Bước 2: Tạo Gateway Load Balancer (GWLB)
1. Tại EC2 Console, menu bên trái chọn **Load balancers** -> Nhấp nút cam **Create load balancer**.
2. Tại mục **Gateway Load Balancer**, nhấp **Create**.
3. **Basic configuration:**
   - **Load balancer name:** `fabric-gwlb`.
   - **IP address type:** `IPv4`.
4. **Network mapping:**
   - **VPC:** Chọn `fabric-inspection-vpc`.
   - **Mappings:** Chọn cả 2 Availability Zones:
     - `ap-southeast-1a`: Chọn subnet `fabric-inspection-fw-1a`.
     - `ap-southeast-1b`: Chọn subnet `fabric-inspection-fw-1b`.
5. **Listeners and routing:**
   - Listener mặc định là `GENEVE` (cổng 6081).
   - **Default action:** Chọn Target group `fabric-gwlb-tg` vừa tạo.
6. **Tags:** `Project` = `aws-eks-secure-network-fabric`, `Environment` = `dev`.
7. Nhấp nút cam **Create load balancer**.

---

## 3. Xác Minh (Verification)

Kiểm tra trạng thái sức khỏe (Health status) của Target Group qua AWS CLI:
```bash
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups --names fabric-gwlb-tg --query 'TargetGroups[0].TargetGroupArn' --output text --region ap-southeast-1) \
  --region ap-southeast-1 \
  --output table
```
> Kết quả: Cả 2 máy chủ đều có `TargetHealth.State = healthy`.

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Gateway Load Balancer `fabric-gwlb` ở trạng thái `active`.
- [ ] Cả 2 máy chủ Suricata EC2 đều vượt qua kiểm tra sức khỏe (`healthy`) trên Target Group GENEVE.

