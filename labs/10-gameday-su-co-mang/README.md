# Module 10: GameDay Sự Cố Mạng

Chỉ diễn tập trong cửa sổ được phép, sau baseline thành công, sao lưu cấu hình và chuẩn bị rollback. Các bài còn DRAFT; chưa có kết quả runtime. Mỗi bài giữ walkthrough Console, kiểm tra, evidence và rollback riêng.

| Bài | Tiêm lỗi | Kiểm chứng / phục hồi |
|---|---|---|
| [10.01 Route leak](01-gameday-route-leak-test.md) | Thay route Edge→Core sang direct attachment | Policy không có “inspection tag”; đo bypass/asymmetry bằng capture và routes, khôi phục target Inspection |
| [10.02 Asymmetric routing](02-gameday-asymmetric-routing-test.md) | Tắt appliance mode Inspection | Cần traffic/placement hai AZ; không tái hiện thì ghi NOT_REPRODUCED, không ép tỷ lệ lỗi 50%; bật lại và đo kết nối mới |
| [10.03 Appliance loss](03-gameday-suricata-appliance-loss.md) | Stop một appliance, không terminate | Cross-zone và healthy target còn lại là tiền đề; đo thời gian thực, phiên cũ no_rebalance có thể lỗi; start và kiểm tra cả hai services |
| [10.04 IPS drop](04-gameday-firewall-malicious-drop.md) | Marker plaintext riêng TCP 8084 | Control→marker→control, EVE SID 2026001 action blocked; MVP không đọc payload HTTPS; cleanup namespace/SG/policy tạm |
| [10.05 NAT return loss](05-gameday-nat-return-failure.md) | Xóa route Core trên public NAT table **một AZ** | Baseline/controls 06.04, route diff và logs; phục hồi đúng NFW endpoint cùng AZ, không bypass thẳng TGW |

Nghiệm thu: lưu timestamps fault/detect/mitigate/recover, MTTD/MTTR thật, ảnh hưởng phiên cũ/mới, log/capture theo flow, cấu hình trước/sau và rollback thành công. Timeout, thiếu logs hoặc kết quả ví dụ không đủ ghi PASS. Thời gian healthcheck không phải cam kết thời gian failover.
