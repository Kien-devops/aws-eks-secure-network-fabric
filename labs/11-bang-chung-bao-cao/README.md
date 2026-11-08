# Module 11 — Tổng Hợp Bằng Chứng Kỹ Thuật & Báo Cáo Sự Cố (Evidence & Reports)

## 1. Tổng Quan Module

Module 11 đặc tả quy chuẩn thu thập bằng chứng runtime, kiểm toán an toàn khử trùng dữ liệu nhạy cảm (Zero Secret Leak), quy trình phân tích sự cố SRE (Blameless Post-Mortem) và báo cáo quản trị tài chính đám mây FinOps. Đảm bảo toàn bộ bằng chứng có dấu thời gian ISO 8601 UTC và tuân thủ nguyên tắc Zero Fake Data.

---

## 2. Thứ Tự Phụ Thuộc (Dependency Tree)

```text
[Module 00 -> 10 Hoàn Tất & Thu Thập Log]
                  │
                  ▼
[11.01 Thu Thập Bằng Chứng Kỹ Thuật Runtime (Timestamp)]
                  │
                  ▼
[11.02 Kiểm Toán Vệ Sinh Dữ Liệu & Khử Trùng (Sanitization)]
                  │
                  ▼
[11.03 Mẫu Báo Cáo Phân Tích Sự Cố Chuẩn SRE (Post-Mortem)]
                  │
                  ▼
[11.04 Đo Lường Chi Phí Thực Tế & Tối Ưu Hóa FinOps]
```

---

## 3. Danh Mục Bài Lab & Trạng Thái

| Mã Bài | Tên Bài Lab | Nội Dung Kỹ Thuật Chính | Trạng Thái | File Đặc Tả |
| :--- | :--- | :--- | :--- | :--- |
| **11.01** | Runtime Evidence Collection | Thu thập tự động telemetry, routing, firewall và healthcheck qua AWS CLI kèm ISO 8601 timestamp | `RUNTIME_PASS` | [01-runtime-evidence-collection.md](01-runtime-evidence-collection.md) |
| **11.02** | Evidence Sanitization Audit | Kiểm toán 5 lớp an ninh, khử trùng 100% AWS Account ID sang `123456789012`, loại bỏ khóa bí mật | `RUNTIME_PASS` | [02-evidence-sanitization-audit.md](02-evidence-sanitization-audit.md) |
| **11.03** | Incident Post-Mortem Template | Soạn thảo báo cáo phân tích sự cố SRE Blameless cho GameDay 10.02, tính MTTD/MTTR và 5 Whys | `RUNTIME_PASS` | [03-incident-post-mortem-template.md](03-incident-post-mortem-template.md) |
| **11.04** | FinOps Cost Report | Tổng hợp cước phí AWS thực tế qua Cost Explorer (~$17.64 USD) và đối soát hạn mức ngân sách $50 USD | `RUNTIME_PASS` | [04-finops-cost-report.md](04-finops-cost-report.md) |

---

## 4. Danh Mục Tập Tin Bằng Chứng & Báo Cáo (Artifacts Inventory)

| Đường Dẫn Tập Tin | Loại Dữ Liệu | Nguồn Trích Xuất | Mô Tả Kỹ Thuật |
| :--- | :--- | :--- | :--- |
| `evidence/01-network-topology/` | JSON Data | EC2 / VPC / TGW APIs | Sơ đồ topology 4 VPCs, 16 subnets và bảng định tuyến TGW |
| `evidence/02-gwlb-inspection/` | JSON & PCAP | ELBv2 & EC2 Suricata | Trạng thái GWLB target health và packet captures đối xứng AZ |
| `evidence/03-egress-firewall/` | JSON & Log | AWS Network Firewall | Trạng thái Ready của NFW và log domain filtering allowlist |
| `evidence/05-reports/SANITIZATION-AUDIT-REPORT.md` | Báo cáo Markdown | Script kiểm toán 5 lớp | Chứng chỉ vệ sinh dữ liệu, xác nhận 0 rò rỉ secret / account ID |
| `evidence/05-reports/INCIDENT-POST-MORTEM-ASLR.md` | Báo cáo Markdown | GameDay 10.02 Telemetry | Báo cáo SRE Post-Mortem sự cố định tuyến bất đối xứng |
| `evidence/05-reports/FINOPS-COST-REPORT.md` | Báo cáo Markdown | AWS Cost Explorer | Báo cáo chi phí thực tế $17.64 USD kèm 4 chiến lược tối ưu FinOps |
