# Module 11: Tổng Hợp Bằng Chứng Kỹ Thuật & Báo Cáo Sự Cố (Evidence & Report)

## 1. Mục Tiêu Kỹ Thuật
- **Mục tiêu:**
  - Tổng hợp toàn bộ dữ liệu bằng chứng kỹ thuật (Runtime Evidence) được tạo ra từ các bài lab và kịch bản GameDay.
  - Áp dụng quy tắc khử trùng bảo mật (Sanitization & Redaction) tuyệt đối:
    - Thay thế 100% AWS Account ID bằng `123456789012` hoặc `***`.
    - Che giấu hoàn toàn Private Keys, Database Passwords, JWT Secrets.
  - Lập báo cáo phân tích sau sự cố (Incident Post-Mortem Report) chuẩn SRE.
  - Lập bảng tổng kết chi phí đám mây thực tế tiêu hao trong suốt quá trình triển khai dự án.

---

## 2. Cấu Trúc Thư Mục Bằng Chứng (Evidence Folder Structure)

```text
evidence/
├── 01-network-topology/
│   ├── vpc-subnets.json
│   ├── tgw-attachments-routes.json
│   └── reachability-analyzer-result.json
├── 02-gwlb-inspection/
│   ├── tcpdump-symmetric-az-a.pcap
│   ├── suricata-eve-alerts.json
│   └── gwlb-target-health.json
├── 03-egress-firewall/
│   ├── nfw-domain-allowlist-test.log
│   └── nfw-block-unauthorized.log
├── 04-gameday/
│   ├── gameday-asymmetric-routing-drop.log
│   ├── gameday-appliance-failover-timeline.csv
│   └── gameday-route-leak-detection.log
└── 05-reports/
    ├── INCIDENT-POST-MORTEM.md
    └── FINOPS-COST-SUMMARY.md
```

---

## 3. Nội Dung Báo Cáo Incident Post-Mortem Mẫu

Mỗi sự cố diễn tập được tổng kết theo mẫu chuẩn:
1. **Tiêu đề sự cố:** Mô tả ngắn gọn bản chất lỗi.
2. **Thời gian xảy ra & Thời gian khắc phục:** Timestamp chuẩn ISO 8601.
3. **Mức độ ảnh hưởng (Severity):** P1 / P2 / P3.
4. **Phân tích nguyên nhân gốc rễ (Root Cause Analysis - 5 Whys):**
   - Tại sao gói tin bị drop? -> Do lệch AZ trên luồng phản hồi.
   - Tại sao lệch AZ? -> Do TGW không bật Appliance Mode.
5. **Biện pháp khắc phục vĩnh viễn (Permanent Fixes):**
   - Kích hoạt Appliance Mode trên Inspection Attachment.
   - Đưa cấu hình vào Terraform để chống trôi dạt (Drift).

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [x] Toàn bộ các file log/json trong thư mục evidence đã được kiểm duyệt không còn lộ thông tin nhạy cảm (100% AWS Account ID đã được khử trùng sang `123456789012`).
- [x] Mọi log output đều có timestamp thực tế (ISO 8601 UTC), không chứa dữ liệu giả mạo.
- [x] Báo cáo Post-Mortem và FinOps Cost Report được hoàn thiện đầy đủ tại `evidence/05-reports/`.

