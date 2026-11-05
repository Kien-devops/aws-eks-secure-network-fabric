# 04.03 — Khởi Tạo Core Internal Network Load Balancer (NLB) & TLS Termination

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Cung cấp điểm tiếp nhận lưu lượng nội bộ chịu tải cao, độ trễ cực thấp trong Core VPC phục vụ các dịch vụ Backend.

---

## 1. Mục Tiêu Kỹ Thuật

- Khởi tạo **Internal Network Load Balancer (NLB)** đặt tại các Subnet riêng tư của Core VPC (`fabric-core-vpc`).
- Thiết lập Listener tiếp nhận kết nối TLS qua cổng **TCP `443`**.
- Gắn Target Group chuyển tiếp lưu lượng vào các Pods của `order-service` trên cụm `fabric-core-eks`.
- Kích hoạt tính năng **Cross-Zone Load Balancing** để đảm bảo phân bổ tải đồng đều giữa 2 Availability Zones (`ap-southeast-1a` và `ap-southeast-1b`).

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Tạo Target Group Cho Order Service
1. Mở dịch vụ **EC2 Console** tại `ap-southeast-1` -> Menu bên trái chọn **Target groups**.
2. Nhấp **Create target group**:
   - **Target type:** Chọn `IP addresses` (phục vụ AWS VPC CNI direct pod routing).
   - **Target group name:** `fabric-core-order-tg`.
   - **Protocol:** Chọn `TCP` hoặc `TLS`.
   - **Port:** `8080` (hoặc cổng HTTP của order-service).
   - **IP address type:** `IPv4`.
   - **VPC:** Chọn `fabric-core-vpc`.
   - **Health checks:**
     - Health check protocol: `HTTP`.
     - Health check path: `/health` (hoặc `/actuator/health`).
   - Nhấp **Next** -> Nhấp **Create target group**.

---

### Bước 2: Tạo Internal Network Load Balancer
1. Tại EC2 Console, menu bên trái chọn **Load balancers** -> Nhấp **Create load balancer**.
2. Tại mục **Network Load Balancer**, nhấp **Create**.
3. **Basic configuration:**
   - **Load balancer name:** `fabric-core-internal-nlb`.
   - **Scheme:** Chọn radio button **Internal** (Chỉ hoạt động trong mạng nội bộ).
   - **IP address type:** `IPv4`.
4. **Network mapping:**
   - **VPC:** Chọn `fabric-core-vpc`.
   - **Mappings:** Chọn cả 2 Availability Zones:
     - `ap-southeast-1a`: Chọn subnet `fabric-core-node-1a` (hoặc `fabric-core-data-1a`).
     - `ap-southeast-1b`: Chọn subnet `fabric-core-node-1b`.
5. **Security groups:**
   - Chọn Security Group cho phép Inbound cổng `443` từ dải Edge VPC (`10.40.0.0/16`).
6. **Listeners and routing:**
   - **Protocol:** Chọn `TLS` (hoặc `TCP` nếu mã hóa end-to-end tại Pod).
   - **Port:** `443`.
   - **Default action:** Chuyển tiếp tới Target group `fabric-core-order-tg`.
7. Nhấp nút cam **Create load balancer**.

---

### Bước 3: Bật Cross-Zone Load Balancing
1. Chọn `fabric-core-internal-nlb` trong danh sách Load Balancers.
2. Mở tab **Attributes** ở bảng chi tiết bên dưới -> Nhấp **Edit**.
3. Tại mục **Cross-zone load balancing**: Bật tùy chọn **On**.
4. Nhấp **Save changes**.

---

## 3. Xác Minh (Verification)

Kiểm tra trạng thái Load Balancer qua AWS CLI:
```bash
aws elbv2 describe-load-balancers \
  --names fabric-core-internal-nlb \
  --region ap-southeast-1 \
  --query 'LoadBalancers[0].{Name:LoadBalancerName,Scheme:Scheme,VpcId:VpcId,DNSName:DNSName,State:State.Code}' \
  --output table
```
> Kết quả: `Scheme = internal`, `State = active`.

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] NLB ở trạng thái `active` với cấu hình Scheme là `internal`.
- [ ] Listener cổng 443 sẵn sàng chuyển tiếp tới Target Group của order-service.
