# 10.03 — GameDay Kịch Bản 3: Tắt Cưỡng Bức Máy Chủ Tường Lửa (Suricata Appliance Failover)

> **Trạng thái:** Kịch bản diễn tập sự cố mạng có chủ đích (Controlled Chaos Test).  
> **Áp dụng cho:** Đo lường khả năng tự phục hồi của Gateway Load Balancer khi một node kiểm tra an ninh mạng bị sập đột ngột.

---

## 1. Mục Tiêu Kỹ Thuật

- **Tình huống sự cố:** Đột ngột tắt cưỡng bức (Stop hoặc Terminate) máy chủ ảo `fabric-suricata-appliance-1a` tại AZ-a trong khi lưu lượng đang hoạt động liên tục.
- **Hành vi mong đợi:**
  - GWLB phát hiện target không phản hồi health check trong vòng 10 - 15 giây (3 lần thất bại x 5s).
  - GWLB tự động đánh dấu Target là `unhealthy` và chuyển hướng toàn bộ lưu lượng mới sang `fabric-suricata-appliance-1b` tại AZ-b.
  - Sử dụng công cụ kiểm thử tải `k6` chạy liên tục để đo chính xác:
    - Số lượng requests bị ảnh hưởng trong thời gian failover.
    - Thời gian hệ thống tự phục hồi hoàn toàn (MTTR).

---

## 2. Các Bước Thực Hiện Chi Tiết

### Bước 1: Khởi Chạy Lưu Lượng Nền Liên Tục (Baseline Load)
Chạy script kiểm thử kết nối từ Edge Pod (tần suất 10 requests / giây):
```bash
k6 run --vus 5 --duration 2m scripts/connection-test.js
```

---

### Bước 2: Tắt Cưỡng Bức Máy Chủ Suricata AZ-a (Fault Injection)
Mở cửa sổ terminal khác hoặc trên AWS Console:
```bash
aws ec2 stop-instances \
  --instance-ids $(aws ec2 describe-instances --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-suricata-appliance-1a" --query 'Reservations[0].Instances[0].InstanceId' --output text) \
  --region ap-southeast-1
```
Ghi lại timestamp chính xác lúc gửi lệnh tắt: `T_fault`.

---

### Bước 3: Quan Sát Quá Trình GWLB Loại Bỏ Target Lỗi
1. Theo dõi trạng thái Target Group:
   ```bash
   watch -n 2 'aws elbv2 describe-target-health --target-group-arn <gwlb-tg-arn> --region ap-southeast-1 --output table'
   ```
2. Ghi lại timestamp khi trạng thái chuyển sang `unhealthy`: `T_detect`.
3. Ghi lại timestamp khi lưu lượng kết nối qua k6 trở lại tỷ lệ thành công 100%: `T_recover`.
4. Tính toán thời gian phục hồi: **MTTR = T_recover - T_fault** (Mong đợi: < 25 giây).

---

### Bước 4: Khởi Động Lại Máy Chủ (Recovery)
```bash
aws ec2 start-instances --instance-ids <suricata-az-a-instance-id> --region ap-southeast-1
```
Quan sát target tự động chuyển lại trạng thái `healthy` trên GWLB.

---

## 3. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] GWLB tự động chuyển tải sang máy chủ AZ-b khi AZ-a bị tắt.
- [ ] Bảng đo lường k6 ghi nhận rõ ràng số lượng failed requests và tỷ lệ phục hồi.
- [ ] Thời gian phục hồi MTTR đạt chuẩn dưới 30 giây.

