# 10.05 — GameDay Kịch Bản 5: Mất Tuyến Đường Về Tại Cổng Ra Tập Trung (NAT Return-Path Loss)

> **Trạng thái:** Kịch bản diễn tập sự cố mạng có chủ đích (Controlled Chaos Test).  
> **Áp dụng cho:** Chẩn đoán sự cố mạng chiều đi thì gửi được nhưng chiều phản hồi bị drop (Blackhole) tại NAT Gateway.

---

## 1. Mục Tiêu Kỹ Thuật

- **Tình huống sự cố:** Một kỹ sư vô tình xóa route `10.50.0.0/16` (Core VPC) trong bảng định tuyến `fabric-egress-public-rt` của Egress VPC.
  - Chiều đi: Gói tin từ Core EKS vẫn đến được Internet qua TGW -> Network Firewall -> NAT Gateway -> IGW.
  - Chiều về: Gói tin phản hồi từ Server Internet gửi về IP công khai của NAT Gateway, NAT thực hiện DNAT chuyển về IP gốc `10.50.10.x`. Tuy nhiên, bảng định tuyến tại Public Subnet không biết đường về `10.50.0.0/16` nên gói tin bị drop tại NAT Gateway.
- **Hành vi mong đợi:** Workload bị treo khi tải dữ liệu từ Internet; VPC Flow Logs ghi nhận traffic outbound thành công nhưng không có gói tin inbound quay lại.
- **Khắc phục:** Bổ sung lại route trỏ về Transit Gateway Attachment.

---

## 2. Các Bước Thực Hiện Chi Tiết

### Bước 1: Xóa Tuyến Đường Về (Fault Injection)
1. Mở **VPC Console** -> **Route tables** -> Chọn `fabric-egress-public-rt`.
2. Mở tab **Routes** -> Nhấp **Edit routes**.
3. Xóa dòng chứa destination: `10.50.0.0/16` -> Nhấp **Save changes**.

---

### Bước 2: Quan Sát Hiện Tượng & Điều Tra Bằng Flow Logs
1. Từ Core EKS Pod, thử tải gói phần mềm từ Internet:
   ```bash
   curl -Iv --connect-timeout 5 https://github.com
   ```
   > Hiện tượng: `curl: (28) Connection timed out after 5001 milliseconds`.
2. Truy vấn VPC Flow Logs của Egress VPC:
   - Gói tin SYN từ `10.50.10.x` ra `github.com` được ghi nhận `ACCEPT`.
   - Không thấy gói tin phản hồi từ Public IP của NAT quay lại `10.50.10.x`.
   - Kết luận điều tra: Mất định tuyến đường về (Return-path failure).

---

### Bước 3: Khôi Phục Tuyến Đường (Incident Resolution)
1. Mở lại bảng định tuyến `fabric-egress-public-rt`.
2. Nhấp **Edit routes** -> **Add route**:
   - **Destination:** `10.50.0.0/16`.
   - **Target:** Chọn `Transit Gateway` (`fabric-tgw`).
3. Nhấp **Save changes**.
4. Chạy lại lệnh `curl`: Kết nối TLS tới `github.com` thành công lập tức.

---

## 3. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Xác định chính xác nguyên nhân mất tuyến đường về qua phân tích VPC Flow Logs.
- [ ] Thời gian phát hiện và khôi phục sự cố được đo lường cụ thể với timestamp.
