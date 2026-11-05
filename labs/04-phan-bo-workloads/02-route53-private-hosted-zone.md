# 04.02 — Thiết Lập Route 53 Private Hosted Zone (internal.fabric)

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Cung cấp dịch vụ phân giải tên miền nội bộ giữa các VPC độc lập (Edge VPC và Core VPC).

---

## 1. Mục Tiêu Kỹ Thuật

- Khởi tạo **Route 53 Private Hosted Zone (PHZ)** với tên miền `internal.fabric`.
- Liên kết Hosted Zone với cả 2 VPCs:
  1. `fabric-edge-vpc`
  2. `fabric-core-vpc`
- Tạo bản ghi A Record phân giải tên miền `order.internal.fabric` trỏ về địa chỉ IP của Core Internal NLB.
- Đảm bảo Pod từ Edge EKS có thể phân giải trực tiếp IP của Core Backend mà không cần phơi lộ dịch vụ ra Internet.

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Khởi Tạo Private Hosted Zone
1. Trên thanh tìm kiếm AWS Console, nhập **Route 53** -> Chọn dịch vụ **Route 53**.
2. Tại menu bên trái, nhấp vào **Hosted zones** -> Nhấp nút cam **Create hosted zone**.
3. **Hosted zone configuration:**
   - **Domain name:** Nhập `internal.fabric`.
   - **Description:** Nhập `Private DNS hosted zone for internal microservices communication`.
   - **Type:** Chọn radio button **Private hosted zone**.
4. **VPCs to associate with the hosted zone:**
   - **Region:** Chọn `Asia Pacific (Singapore) (ap-southeast-1)`.
   - **VPC ID:** Chọn `fabric-edge-vpc`.
5. Nhấp nút cam **Create hosted zone**.

---

### Bước 2: Liên Kết Thêm Core VPC Vào Hosted Zone
1. Tại trang chi tiết Hosted Zone `internal.fabric` vừa tạo, mở tab **Hosted zone details** (hoặc mục **VPCs**).
2. Nhấp nút **Associate VPC**.
3. Chọn Region: `ap-southeast-1`.
4. Chọn VPC: `fabric-core-vpc`.
5. Nhấp **Associate VPC**.

---

### Bước 3: Tạo Bản Ghi DNS (DNS Records)
1. Trong Hosted Zone `internal.fabric`, nhấp vào nút **Create record**.
2. **Record 1 (Order Backend):**
   - **Record name:** Nhập `order` (tên miền đầy đủ sẽ là `order.internal.fabric`).
   - **Record type:** Chọn `A - Routes traffic to an IPv4 address and some AWS resources`.
   - **Alias:** Bật `Yes` -> Chọn Target là Core Internal Network Load Balancer (hoặc nhập địa chỉ IP nội bộ của NLB nếu cấu hình IP trực tiếp).
   - **Routing policy:** `Simple routing`.
   - Nhấp **Create records**.
3. **Record 2 (Auth Backend):**
   - Tạo bản ghi `auth.internal.fabric` trỏ về service Auth trong Edge cluster.

---

## 3. Xác Minh (Verification)

Kiểm tra thông tin Private Hosted Zone qua AWS CLI:
```bash
aws route53 list-hosted-zones-by-name \
  --dns-name internal.fabric \
  --query 'HostedZones[0].{Id:Id,Name:Name,PrivateZone:Config.PrivateZone}' \
  --output table
```
> Kết quả: `Name = internal.fabric.`, `PrivateZone = True`.

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Hosted Zone `internal.fabric` được tạo thành công với loại Private.
- [ ] Cả 2 VPCs (`fabric-edge-vpc` và `fabric-core-vpc`) đều được liên kết thành công.
- [ ] Bản ghi `order.internal.fabric` được tạo sẵn sàng phân giải sang Core Internal NLB.
