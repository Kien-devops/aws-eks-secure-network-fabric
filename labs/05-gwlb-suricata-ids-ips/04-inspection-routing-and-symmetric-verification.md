# 05.04 — Hoàn Thiện Định Tuyến Kiểm Tra & Kiểm Chứng Symmetric Flow Bằng tcpdump

> **Trạng thái:** Hướng dẫn thực hành chi tiết cấu hình định tuyến và kiểm chứng dòng chảy gói tin đối xứng.  
> **Áp dụng cho:** Đóng kín chuỗi dịch vụ kiểm tra an ninh mạng và xác thực cờ Appliance Mode hoạt động chính xác qua bắt gói tin runtime.

---

## 1. Mục Tiêu Kỹ Thuật

- Cập nhật các bảng định tuyến trong Inspection VPC để chuyển tiếp lưu lượng qua 2 điểm cuối `gwlbe-1a` và `gwlbe-1b`:
  - Subnet TGW Route Table -> Chuyển tiếp dải `10.50.0.0/16` (Core) và `10.40.0.0/16` (Edge) vào GWLBe.
  - Subnet GWLBe Route Table -> Chuyển tiếp lưu lượng sau kiểm tra quay trở lại Transit Gateway Attachment.
- Bắt gói tin (`tcpdump`) trực tiếp trên giao diện `geneve0` của cả 2 máy chủ Suricata EC2.
- Kiểm chứng **Symmetric Routing**: Xác nhận 100% gói tin của một phiên TCP (cả SYN, SYN-ACK, ACK, Data) đều đi qua cùng một máy chủ trong cùng một AZ (`ap-southeast-1a` hoặc `ap-southeast-1b`).

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Cập Nhật Bảng Định Tuyến Subnet TGW Tại Inspection VPC
Tách làm 2 bảng định tuyến cho 2 AZ để trỏ đúng GWLBe tương ứng:
1. **Bảng định tuyến `fabric-inspection-tgw-rt-1a` (Gắn với subnet `fabric-inspection-tgw-1a`):**
   - Route `10.50.0.0/16` -> Target: Chọn `Gateway Load Balancer Endpoint` (`vpce-...` của AZ-a).
   - Route `10.40.0.0/16` -> Target: Chọn `Gateway Load Balancer Endpoint` (`vpce-...` của AZ-a).
2. **Bảng định tuyến `fabric-inspection-tgw-rt-1b` (Gắn với subnet `fabric-inspection-tgw-1b`):**
   - Route `10.50.0.0/16` -> Target: Chọn `Gateway Load Balancer Endpoint` (`vpce-...` của AZ-b).
   - Route `10.40.0.0/16` -> Target: Chọn `Gateway Load Balancer Endpoint` (`vpce-...` của AZ-b).

---

### Bước 2: Cập Nhật Bảng Định Tuyến Subnet GWLBe
Mở bảng định tuyến `fabric-inspection-gwlbe-rt` (gắn với cả 2 subnet `gwlbe-1a` và `gwlbe-1b`):
1. Route `10.50.0.0/16` -> Target: Chọn `Transit Gateway` (`fabric-tgw`).
2. Route `10.40.0.0/16` -> Target: Chọn `Transit Gateway` (`fabric-tgw`).
3. Nhấp **Save changes**.

---

## 3. Kiểm Chứng Định Tuyến Đối Xứng (Symmetric Routing Verification)

### Bước 1: Bật Lắng Nghe Bắt Gói Tin Trên Cả 2 Máy Chủ Suricata
Mở 2 cửa sổ terminal SSM Session Manager:
- **Terminal 1 (Máy chủ AZ-a):**
  ```bash
  sudo tcpdump -ni geneve0 "port 443" -vv
  ```
- **Terminal 2 (Máy chủ AZ-b):**
  ```bash
  sudo tcpdump -ni geneve0 "port 443" -vv
  ```

### Bước 2: Kích Hoạt Lưu Lượng Từ Edge EKS
Từ Pod `frontend` trong cụm `fabric-edge-eks`:
```bash
for i in {1..20}; do
  curl -k -s -o /dev/null -w "%{http_code}\n" https://order.internal.fabric/health
  sleep 0.5
done
```

### Bước 3: Quan Sát Kết Quả tcpdump
- Nếu phiên kết nối khởi tạo tại AZ-a: Toàn bộ gói tin `SYN` (chiều đi từ Edge) và `SYN-ACK` (chiều về từ Core) đều xuất hiện trên **cùng một máy chủ AZ-a**.
- Máy chủ AZ-b không xuất hiện các gói tin lẻ loi của phiên này (không có hiện tượng SYN ở A nhưng ACK ở B).
- Khi Appliance Mode được bật, TGW duy trì băm flow (5-tuple hash) đi vào cùng một ENI Attachment ở cả 2 chiều.

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Giao tiếp giữa Edge Pod và Core Backend thành công 100% (HTTP 200).
- [ ] Bằng chứng log `tcpdump` chứng minh đường truyền đối xứng tuyệt đối (Symmetric Flow PASS).
- [ ] Không có gói tin TCP Out-of-Order hoặc TCP Reset phát sinh do lệch AZ.
