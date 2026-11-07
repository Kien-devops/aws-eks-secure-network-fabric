# BÁO CÁO PHÂN TÍCH SỰ CỐ MẠNG: ĐỊNH TUYẾN BẤT ĐỐI XỨNG (ASYMMETRIC ROUTING)

- **Mã sự cố (Incident ID):** `INC-FABRIC-2026-001`
- **Mức độ nghiêm trọng (Severity):** `P1 - High Availability Impact`
- **Thời gian bắt đầu (T_fault):** `2026-11-07T21:58:14Z`
- **Thời gian phát hiện (T_detect):** `2026-11-07T21:58:49Z`
- **Thời gian áp dụng sửa đổi (T_mitigate):** `2026-11-07T21:59:08Z`
- **Thời gian phục hồi hoàn toàn (T_recover):** `2026-11-07T22:01:29Z`
- **Chỉ số SRE:**
  - MTTD (Thời gian phát hiện): 35 giây
  - MTTR (Thời gian khôi phục hoàn toàn): 3 phút 15 giây
- **Người chủ trì điều tra:** Principal Network Architect & SRE Lead
- **Hệ thống bị ảnh hưởng:** Toàn bộ giao tiếp East-West giữa Edge EKS và Core EKS qua Transit Gateway và Suricata IDS/IPS.

---

## 1. Tóm Tắt Tác Động (Executive Summary)
Trong phiên diễn tập GameDay có kiểm soát tại Singapore (`ap-southeast-1`), một lỗi cấu hình nghiêm trọng đã được mô phỏng: tính năng **Appliance Mode Support** trên TGW Inspection Attachment (`tgw-attach-0fb21514974415f35`) bị vô hiệu hóa (`disable`). 
Sự cố làm phá vỡ tính đối xứng luồng lưu lượng (Flow Symmetry), khiến 100% các kết nối TCP mới giữa Frontend Pod và Order Service qua mạng trung gian bị timeout do thiết bị kiểm tra an ninh Stateful Suricata drop các gói tin không có trạng thái phiên ban đầu (TCP Out-of-State). Sự cố được phát hiện trong 35 giây và khắc phục triệt để trong 3 phút 15 giây bằng việc kích hoạt lại Appliance Mode trên AWS Transit Gateway.

---

## 2. Dòng Thời Gian Chi Tiết (Detailed Timeline)

| Thời Gian (UTC) | Sự Kiện Kỹ Thuật | Người / Hệ Thống |
|---|---|---|
| **21:58:14Z** | Tiêm lỗi: Vô hiệu hóa `ApplianceModeSupport` trên Inspection TGW Attachment. | Chaos Engineer |
| **21:58:30Z** | TGW Attachment chuyển sang trạng thái `available` với Appliance Mode disabled. | AWS TGW Controller |
| **21:58:49Z** | Chuỗi 40 requests kiểm thử liên tiếp thất bại 100% (cả 40 requests đều không nhận được SYN-ACK). | SRE On-call |
| **21:59:00Z** | Bắt gói tin xác nhận: Gói `SYN` được chuyển tới node 1a, nhưng gói phản hồi `SYN-ACK` bị TGW 5-tuple hash lệch sang node 1b và bị drop tại chỗ. | Network Architect |
| **21:59:08Z** | Thực thi lệnh khẩn cấp kích hoạt lại `ApplianceModeSupport = enable` trên TGW Attachment. | SRE On-call |
| **22:01:29Z** | TGW Attachment hoàn tất cập nhật. Chạy lại chuỗi 40 requests kiểm thử: 40/40 thành công tuyệt đối (HTTP 200 OK). | Toàn hệ thống |

---

## 3. Phân Tích Nguyên Nhân Gốc Rễ (5 Whys Root Cause Analysis)
1. **Tại sao kết nối giữa Edge và Core bị timeout?** -> Suricata drop gói tin phản hồi TCP SYN-ACK.
2. **Tại sao Suricata drop gói tin?** -> Gói tin đến node AZ-b mà không có bản ghi phiên ban đầu (Out-of-State / Missing Handshake).
3. **Tại sao gói tin chiều về lại rơi vào node AZ-b trong khi chiều đi qua node AZ-a?** -> TGW phân phối gói tin độc lập giữa 2 AZ trên hai chiều giao tiếp khi thiếu tính năng dính vùng.
4. **Tại sao TGW không giữ cố định AZ cho cùng một phiên TCP?** -> Thuộc tính `ApplianceModeSupport` trên TGW VPC Attachment bị tắt (`disable`).
5. **Biện pháp ngăn ngừa căn bản là gì?** -> Khóa cứng thuộc tính `appliance_mode_support = "enable"` trong mã nguồn Terraform và bổ sung chính sách Checkov / AWS Config Rule để cảnh báo hoặc tự động sửa (auto-remediation) nếu có bất kỳ thay đổi nào làm tắt tính năng này.

---

## 4. Bài Học Rút Ra (Lessons Learned)
- **Điểm làm tốt:** Quy trình phát hiện tự động đo lường tỷ lệ lỗi thông qua vòng lặp kiểm thử giúp khoanh vùng nguyên nhân trong 35 giây; playbook rollback bằng AWS CLI hoạt động nhanh chóng và chính xác.
- **Điểm cần cải thiện:** Cần cấu hình AWS Config Rule phát hiện trôi dạt cấu hình (drift detection) trên toàn bộ TGW attachments để tự động kích hoạt cảnh báo tới PagerDuty/Slack.
- **Yếu tố an toàn:** Sự cố được tiến hành trong môi trường cô lập, các bước khôi phục đã được kiểm thử trước và đạt tỷ lệ phục hồi 100%.

---

## 5. Danh Mục Hành Động Khắc Phục (Action Items)

| Mã Công Việc | Mô Tả Hành Động | Người Phụ Trách | Ưu Tiên | Hạn Chót | Trạng Thái |
|---|---|---|---|---|---|
| **ACT-01** | Khóa cứng `appliance_mode_support = "enable"` trong Terraform Module TGW. | DevOps Lead | P0 | 24h | **DONE** |
| **ACT-02** | Xây dựng Checkov rule chặn PR nếu `appliance_mode_support` khác `enable`. | SecOps | P1 | 48h | **DONE** |
| **ACT-03** | Tạo CloudWatch Alarm giám sát tỷ lệ Out-of-State Drops từ Suricata EVE logs. | SRE Team | P1 | 3 ngày | **DONE** |
