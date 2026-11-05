# 11.03 — Mẫu Báo Cáo Phân Tích Sự Cố Sau Diễn Tập (Incident Post-Mortem Report)

> **Trạng thái:** Biểu mẫu báo cáo phân tích sự cố chuẩn SRE / DevSecOps.  
> **Áp dụng cho:** Tổng kết các kịch bản diễn tập GameDay mạng nâng cao.

---

# [MẪU BÁO CÁO] Phân Tích Sự Cố Mạng: Định Tuyến Bất Đối Xứng (Asymmetric Routing)

- **Mã sự cố:** `INC-FABRIC-2026-001`
- **Thời gian bắt đầu:** `2026-11-05T08:00:00Z`
- **Thời gian phát hiện (MTTD):** `3 phút`
- **Thời gian khôi phục (MTTR):** `1 phút 30 giây`
- **Mức độ nghiêm trọng:** `P1 - High Availability Impact`
- **Dịch vụ bị ảnh hưởng:** Toàn bộ giao tiếp East-West giữa Edge EKS và Core EKS.

---

## 1. Tóm Tắt Sự Cố (Executive Summary)
Trong quá trình diễn tập GameDay, tính năng Appliance Mode trên Inspection VPC Attachment bị vô hiệu hóa. Lưu lượng chiều đi từ Frontend Pod được TGW chuyển vào Suricata EC2 tại AZ-a, nhưng lưu lượng chiều về từ Order Backend bị chuyển nhầm sang AZ-b. Suricata AZ-b drop các gói tin do không có trạng thái phiên kết nối TCP ban đầu, dẫn đến tỷ lệ lỗi kết nối tăng lên ~50%.

---

## 2. Dòng Thời Gian Sự Cố (Timeline)
- **08:00:00Z:** Tắt Appliance Mode trên TGW VPC Attachment của Inspection VPC.
- **08:01:30Z:** k6 load test bắt đầu ghi nhận tỷ lệ connection timeout tăng vọt.
- **08:03:00Z:** Kỹ sư SRE quan sát `tcpdump` trên Suricata AZ-b thấy xuất hiện gói `SYN-ACK` đơn lẻ không có `SYN`.
- **08:04:30Z:** Kích hoạt lại `ApplianceModeSupport=enable` trên TGW Attachment.
- **08:05:00Z:** Tỷ lệ kết nối thành công phục hồi về 100% (HTTP 200). Kết thúc sự cố.

---

## 3. Phân Tích Nguyên Nhân Gốc Rễ (5 Whys Root Cause Analysis)
1. **Tại sao người dùng gặp lỗi timeout?** -> Do gói tin phản hồi TCP SYN-ACK bị Suricata drop.
2. **Tại sao Suricata drop gói tin?** -> Do Suricata tại AZ-b nhận gói SYN-ACK nhưng không thấy gói SYN trước đó trong bảng trạng thái (Out-of-State).
3. **Tại sao gói SYN-ACK lại sang AZ-b trong khi SYN ở AZ-a?** -> Do Transit Gateway băm flow độc lập trên chiều về và đẩy sang ENI ở AZ khác.
4. **Tại sao TGW không giữ đúng AZ ban đầu?** -> Do cờ `ApplianceModeSupport` đang ở trạng thái `disable`.
5. **Biện pháp ngăn chặn vĩnh viễn là gì?** -> Bật cờ `ApplianceModeSupport=enable` trên Inspection Attachment và kiểm định bằng Terraform Checkov rule.

---

## 4. Hành Động Khắc Phục & Phòng Ngừa (Action Items)
| Hành Động Cụ Thể | Người Thực Hiện | Hạn Chót | Trạng Thái |
|---|---|---|---|
| Khóa cứng cờ `appliance_mode_support = "enable"` trong mã nguồn Terraform | Platform Team | Ngay lập tức | DONE |
| Viết Checkov custom rule kiểm tra cờ Appliance Mode trên TGW Attachment | SecOps Team | 24h | DONE |

