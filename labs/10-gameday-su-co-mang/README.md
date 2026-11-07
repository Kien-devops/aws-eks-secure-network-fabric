# Module 10: GameDay Sự Cố Mạng

Đã hoàn thành diễn tập thực tế trên toàn bộ 5 kịch bản sự cố mạng với runtime evidence có timestamp đầy đủ, tuân thủ nguyên tắc Zero Fake Data. Mọi cấu hình đã được rollback về trạng thái an toàn ban đầu và kiểm chứng thông suốt 100%.

| Bài | Tiêm lỗi | Kiểm chứng / phục hồi | Trạng thái |
|---|---|---|---|
| [10.01 Route leak](01-gameday-route-leak-test.md) | Thay route Edge→Core sang direct attachment | Đo lường bypass/asymmetry, khôi phục target Inspection (`tgw-attach-0fb21514974415f35`), MTTD 5.7s, MTTR 14.6s | **COMPLETED** |
| [10.02 Asymmetric routing](02-gameday-asymmetric-routing-test.md) | Tắt appliance mode Inspection | Tắt Appliance Mode phân tích rủi ro stateful packet drop, bật lại thành công, 40/40 requests HTTP 200 | **COMPLETED** |
| [10.03 Appliance loss](03-gameday-suricata-appliance-loss.md) | Ngắt kiểm tra máy chủ `fabric-suricata-1a` | GWLB phát hiện target unhealthy sau 32s, failover mượt sang 1b (HTTP 200), khôi phục cả 2 healthy (MTTR 89s) | **COMPLETED** |
| [10.04 IPS drop](04-gameday-firewall-malicious-drop.md) | Marker plaintext riêng TCP 8084 | Control (200) → Marker (Dropped by Suricata IPS) → Control (200), EVE alert SID 2026001 action blocked | **COMPLETED** |
| [10.05 NAT return loss](05-gameday-nat-return-failure.md) | Xóa route Core trên public NAT table một AZ | Ghi nhận 40% drops (Blackhole một chiều) qua NAT-1a, tái lập route Core -> NFW endpoint phục hồi 10/10 200 | **COMPLETED** |

Nghiệm thu: Đã lưu trữ đầy đủ 15 tệp bằng chứng trong `evidence/10-gameday/` bao gồm mốc timestamps thật ($T_{fault}, T_{detect}, T_{mitigate}, T_{recover}$), chỉ số MTTD/MTTR, raw JSON EVE alerts, route tables và kết quả kiểm thử. Toàn bộ hệ thống an toàn và hoạt động chuẩn mực.
