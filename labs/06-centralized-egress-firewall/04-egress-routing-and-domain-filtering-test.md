# 06.04 — Hoàn Thiện Định Tuyến 3 Chặng Egress & Kiểm Thử Lọc Tên Miền (Allow vs Block)

> **Trạng thái:** Hướng dẫn thực hành chi tiết cấu hình định tuyến Egress và kiểm thử thực tế.  
> **Áp dụng cho:** Đóng kín chuỗi định tuyến 3 chặng qua Network Firewall và kiểm chứng khả năng ngăn chặn rò rỉ dữ liệu qua Internet.

---

## 1. Mục Tiêu Kỹ Thuật

- Cấu hình kiến trúc định tuyến **3 chặng (3-Hop Egress Routing)** trong Egress VPC:
  - **Chặng 1 (TGW Subnet RT):** Traffic `0.0.0.0/0` từ TGW bắt buộc đi vào Network Firewall Endpoint.
  - **Chặng 2 (Firewall Subnet RT):** Traffic `0.0.0.0/0` sau khi được duyệt chuyển sang NAT Gateway tương ứng cùng AZ.
  - **Chặng 3 (Public Subnet RT):** NAT Gateway chuyển ra Internet Gateway (IGW) và có route đường về cho `10.40.0.0/16` và `10.50.0.0/16` trỏ ngược lại TGW.
- Kiểm thử thực tế từ Core EKS Pod:
  - Cho phép tên miền hợp lệ (`github.com`, `quay.io`).
  - Drop lập tức các tên miền hoặc địa chỉ IP ngoài danh mục và kiểm tra log cảnh báo.

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Cấu Hình Bảng Định Tuyến Subnet TGW (`fabric-egress-tgw-rt`)
Tách làm 2 bảng định tuyến cho 2 AZ để trỏ đúng Firewall Endpoint tương ứng:
1. **Tại Subnet `fabric-egress-tgw-1a`:**
   - Route `0.0.0.0/0` -> Target: Chọn `Network Interface` hoặc `Gateway Load Balancer Endpoint / VPC Endpoint` của Firewall AZ-a (`vpce-...-1a`).
2. **Tại Subnet `fabric-egress-tgw-1b`:**
   - Route `0.0.0.0/0` -> Target: Chọn VPC Endpoint của Firewall AZ-b (`vpce-...-1b`).

---

### Bước 2: Cấu Hình Bảng Định Tuyến Subnet Firewall (`fabric-egress-fw-rt`)
1. **Tại Subnet `fabric-egress-nfw-1a`:**
   - Route `0.0.0.0/0` -> Target: Chọn `NAT Gateway` (`fabric-egress-nat-1a`).
2. **Tại Subnet `fabric-egress-nfw-1b`:**
   - Route `0.0.0.0/0` -> Target: Chọn `NAT Gateway` (`fabric-egress-nat-1b`).

---

### Bước 3: Cấu Hình Bảng Định Tuyến Subnet Public (`fabric-egress-public-rt`)
1. Route `0.0.0.0/0` -> Target: Chọn `Internet Gateway` (`fabric-egress-igw`).
2. Route `10.40.0.0/16` -> Target: Chọn `Transit Gateway` (`fabric-tgw`) (Đường về cho Edge VPC).
3. Route `10.50.0.0/16` -> Target: Chọn `Transit Gateway` (`fabric-tgw`) (Đường về cho Core VPC).

---

## 3. Kiểm Thử Thực Tế (Egress Domain Filtering Test)

Kết nối vào một Pod đang chạy trong cụm `fabric-core-eks`:

### 1. Kiểm thử tên miền nằm trong Allowlist (Thành công):
```bash
curl -Iv https://github.com
curl -Iv https://quay.io
```
> Kết quả mong đợi: Kết nối TLS thành công (HTTP 200 hoặc HTTP 301).

### 2. Kiểm thử tên miền hoặc IP bị chặn (Bị Drop):
```bash
curl -m 5 -Iv https://www.facebook.com
curl -m 5 http://1.1.1.1
```
> Kết quả mong đợi: `curl: (28) Connection timed out after 5001 milliseconds`.

---

## 4. Xác Minh Log Cảnh Báo (Verification)

Mở **CloudWatch Logs Insights**, truy vấn Log Group `/aws/network-firewall/fabric-egress-alerts`:
```sql
fields @timestamp, event.src_ip, event.dest_ip, event.dest_port, event.http.hostname, event.alert.action
| filter event.alert.action = "drop" or event.alert.action = "blocked"
| sort @timestamp desc
| limit 20
```
> Kết quả: Xuất hiện bản ghi drop chi tiết cho request gọi tới `www.facebook.com` hoặc `1.1.1.1`.

---

## 5. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Kiến trúc định tuyến 3 chặng Egress hoạt động hoàn hảo mà không bị vòng lặp.
- [ ] Tên miền cho phép truy cập thành công 100%.
- [ ] Tên miền và địa chỉ IP bị cấm bị chặn đứng và có log `DROP` trong CloudWatch Logs.

