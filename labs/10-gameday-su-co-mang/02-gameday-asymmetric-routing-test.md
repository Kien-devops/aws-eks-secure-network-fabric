# 10.02 — GameDay Kịch Bản 2: Lỗi Định Tuyến Bất Đối Xứng (Asymmetric Routing Failure)

> **Trạng thái:** Kịch bản diễn tập sự cố mạng có chủ đích (Controlled Chaos Test).  
> **Áp dụng cho:** Chứng minh tầm quan trọng sống còn của cờ TGW Appliance Mode trong mô hình tường lửa kiểm tra trạng thái đa AZ.

---

## 1. Mục Tiêu Kỹ Thuật

- **Tình huống sự cố:** Tắt tính năng **Appliance Mode** trên Inspection VPC Attachment:
  - Khi không có Appliance Mode, Transit Gateway sẽ băm (hash) gói tin chiều đi (SYN) vào một AZ ngẫu nhiên (ví dụ AZ-a), nhưng gói tin chiều về (SYN-ACK từ Core) có thể bị TGW chuyển sang ENI ở AZ-b.
- **Hành vi mong đợi:**
  - Máy chủ Suricata tại AZ-b nhận gói tin `SYN-ACK` nhưng không có bảng trạng thái phiên (State table) của gói `SYN` trước đó.
  - Suricata drop gói tin ngay lập tức (TCP Out-of-State / Out-of-Sequence Drop).
  - Người dùng ở Frontend gặp lỗi `Connection timed out` hoặc nhận cờ `TCP RST`.
- **Khắc phục:** Kích hoạt lại `ApplianceModeSupport = enable`, kết nối lập tức thông suốt.

---

## 2. Các Bước Thực Hiện Chi Tiết

### Bước 1: Tắt Appliance Mode (Fault Injection)
Chạy lệnh tắt cờ Appliance Mode qua AWS CLI:
```bash
aws ec2 modify-transit-gateway-vpc-attachment \
  --transit-gateway-attachment-id $(aws ec2 describe-transit-gateway-vpc-attachments --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-tgw-att-inspection" --query 'TransitGatewayVpcAttachments[0].TransitGatewayAttachmentId' --output text) \
  --options "ApplianceModeSupport=disable" \
  --region ap-southeast-1
```

---

### Bước 2: Quan Sát Hiện Tượng & Thu Thập Bằng Chứng
1. Từ `frontend` Pod, liên tục gửi requests tới Core Backend:
   ```bash
   for i in {1..30}; do
     curl -m 2 -Iv https://order.internal.fabric/health
     sleep 0.2
   done
   ```
2. Mở `tcpdump` trên 2 máy chủ Suricata:
   - Nhận diện tình trạng: Máy chủ AZ-a chỉ thấy gói `SYN` đi qua, nhưng gói `SYN-ACK` phản hồi lại rơi vào máy chủ AZ-b.
   - Suricata log ghi nhận: `TCP stream out-of-order drop`.
   - Frontend nhận tỷ lệ lỗi kết nối timeout tăng vọt lên ~50%.

---

### Bước 3: Khắc Phục Sự Cố (Recovery)
Kích hoạt lại Appliance Mode:
```bash
aws ec2 modify-transit-gateway-vpc-attachment \
  --transit-gateway-attachment-id <inspection-attachment-id> \
  --options "ApplianceModeSupport=enable" \
  --region ap-southeast-1
```
Gửi lại 30 requests: Tỷ lệ thành công trở lại **100% (HTTP 200)**.

---

## 3. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Bằng chứng bắt gói tin `tcpdump` chứng minh rõ ràng hiện tượng lệch AZ khi tắt Appliance Mode.
- [ ] Bằng chứng khôi phục thành công 100% khi bật lại Appliance Mode.

