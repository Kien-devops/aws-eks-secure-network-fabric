# 10.01 — GameDay Kịch Bản 1: Sự Cố Rò Rỉ Tuyến Đường (Route Leak Attack / Drift)

> **Trạng thái:** Kịch bản diễn tập sự cố mạng có chủ đích (Controlled Chaos Test).  
> **Áp dụng cho:** Đánh giá khả năng phòng thủ đa tầng khi bảng định tuyến bị cấu hình sai hoặc bị rò rỉ tuyến đường trực tiếp.

---

## 1. Mục Tiêu Kỹ Thuật

- **Tình huống sự cố:** Một kỹ sư vô tình hoặc một tiến trình tự động cấu hình sai thêm route trực tiếp `10.50.0.0/16` vào bảng `fabric-tgw-rt-edge` trỏ thẳng tới Core Attachment (bỏ qua Inspection VPC).
- **Hành vi mong đợi:**
  - Mặc dù TGW định tuyến thẳng tới Core VPC, nhưng gói tin **bắt buộc vẫn phải bị chặn** ở tầng tiếp theo:
    1. Kubernetes NetworkPolicy trong Core EKS từ chối kết nối nếu không có tag phiên hoặc cổng cho phép.
    2. Network ACLs hoặc Security Groups kiểm tra chặt chẽ luồng truy cập.
  - Sử dụng **VPC Reachability Analyzer** và **VPC Flow Logs** để phát hiện ra sự trôi dạt (Drift) này.
- **Biện pháp khắc phục (Recovery):** Xóa route sai và khôi phục target qua Inspection Attachment.

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Gieo Rắc Lỗi Định Tuyến (Fault Injection)
1. Mở **VPC Console** -> **Transit gateway route tables** -> Chọn `fabric-tgw-rt-edge`.
2. Mở tab **Routes** -> Nhấp **Create static route**:
   - **CIDR:** Nhập `10.50.0.0/16`.
   - **Attachment:** Chọn `fabric-tgw-att-core` (Trỏ thẳng sang Core, bỏ qua Inspection).
   - Nhấp **Create static route**.

---

### Bước 2: Quan Sát Hiện Tượng & Thu Thập Telemetry
1. Từ `frontend` Pod, gửi request tới `order-service`:
   ```bash
   curl -Iv --connect-timeout 3 https://order.internal.fabric/health
   ```
2. Mở **CloudWatch Logs Insights**, truy vấn Log Group `/aws/vpc/fabric-core-flow`:
   - Quan sát xem lưu lượng có bị `REJECT` bởi Core NACL hoặc Core Node Security Group hay không.
3. Chạy lại **VPC Reachability Analyzer**:
   - Nhận diện đường dẫn hiển thị bất thường: Luồng không còn đi qua `GWLB Endpoint`.

---

### Bước 3: Khắc Phục Sự Cố (Incident Resolution)
1. Quay lại bảng định tuyến `fabric-tgw-rt-edge`.
2. Sửa lại route `10.50.0.0/16`: Chuyển target trở lại `fabric-tgw-att-inspection`.
3. Nhấp **Save**.

---

## 3. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Ghi lại bằng chứng log chứng minh hành vi chặn của tầng bảo vệ thứ hai khi tuyến đường bị rò rỉ.
- [ ] Thời gian phát hiện và khôi phục (MTTR) được ghi nhận đầy đủ với timestamp.

