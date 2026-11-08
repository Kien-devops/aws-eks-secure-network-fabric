# 11.03 — Mẫu Báo Cáo Phân Tích Sự Cố Sau Diễn Tập (Incident Post-Mortem Report)

> **Mã bài lab:** `11.03`
> **Trạng thái:** `RUNTIME_PASS`
> **Thời gian dự kiến:** 35 phút
> **Chi phí ước tính:** $0.00 USD (Static Documentation)
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)

---

## 1. Mục Tiêu (Objective)

Đặc tả mẫu báo cáo phân tích sự cố chuẩn SRE (Blameless Post-Mortem) sau các bài diễn tập GameDay mạng. Chuẩn hóa quy trình ghi nhận mốc thời gian thực tế, đo lường chỉ số MTTD/MTTR, phân tích nguyên nhân gốc rễ (5 Whys) và lập danh mục hành động khắc phục (Action Items) nhằm nâng cao độ tin cậy hệ thống.

---

## 2. Tài Nguyên (Resources)

| Tên Resource / Báo Cáo | Loại Resource | Nguồn Tham Chiếu | Đường Dẫn Lưu Trữ |
| :--- | :--- | :--- | :--- |
| `INCIDENT-POST-MORTEM-ASLR.md` | SRE Report | GameDay 10.02 (Asymmetric Routing) | `evidence/05-reports/INCIDENT-POST-MORTEM-ASLR.md` |
| `/aws/vpc/fabric-inspection-flow` | CloudWatch Log Group | Inspection VPC Flow Logs | CloudWatch Log Group |
| `/aws/suricata/fabric-inspection-eve` | CloudWatch Log Group | Suricata EVE Alert Logs | CloudWatch Log Group |
| `gameday-02-asymmetric-timeline.json` | Telemetry Data | GameDay 10.02 Evidence | `evidence/10-gameday/gameday-02-asymmetric-timeline.json` |

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `INC-FABRIC-*` | Tiêu chuẩn định danh sự cố |
| `Project` | `aws-eks-secure-network-fabric` | Tiêu chuẩn định danh dự án |
| `Environment` | `prod` | Phân vùng môi trường báo cáo |
| `ManagedBy` | `manual` | Quản lý quy trình tài liệu SRE thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Cấu Trúc Khung Báo Cáo Tiêu Chuẩn SRE (Post-Mortem Template)
* **Metadata Sự Cố:**
  - `Incident ID`: Mã sự cố (ví dụ: `INC-FABRIC-2026-001`).
  - `Severity`: Phân cấp mức độ ảnh hưởng (P1/P2/P3).
  - `Impacted Services`: Microservices bị ảnh hưởng (`edge-frontend`, `core-service`).
  - `SRE Metrics`: MTTD (Mean Time to Detect) và MTTR (Mean Time to Remediate).
* **Mốc Thời Gian (Timeline):**
  - $T_{fault}$: Mốc tiêm lỗi cấu hình mạng hoặc ngắt dịch vụ.
  - $T_{detect}$: Mốc hệ thống giám sát / on-call ghi nhận cảnh báo.
  - $T_{mitigate}$: Mốc thực thi giải pháp giảm thiểu tác động.
  - $T_{recover}$: Mốc toàn bộ lưu lượng nghiệp vụ phục hồi 100% (HTTP 200).
* **Phân Tích Nguyên Nhân Gốc Rễ (5 Whys):**
  1. *Tại sao `edge-frontend` timeout khi gọi `core-service`?* -> Gói TCP SYN-ACK bị drop tại Suricata 1b.
  2. *Tại sao Suricata 1b drop gói tin?* -> Gói SYN-ACK đến mà không có state SYN tương ứng (Out-of-State).
  3. *Tại sao SYN và SYN-ACK đi qua 2 appliance khác nhau?* -> TGW hash 5-tuple độc lập hai chiều.
  4. *Tại sao TGW không giữ tính đối xứng trên cùng một AZ?* -> `ApplianceModeSupport` trên Inspection attachment bị tắt (`disable`).
  5. *Giải pháp triệt để là gì?* -> Ép buộc cấu hình `appliance_mode_support = "enable"` trên IaC/Terraform và bổ sung Checkov policy kiểm soát.
* **Danh Mục Hành Động (Action Items):** Bảng phân công chi tiết với mức ưu tiên P0/P1/P2, người phụ trách và hạn hoàn thành.

---

## 5. Phụ Thuộc (Dependencies)

* [Module 10](../10-gameday-su-co-mang/README.md): Đã hoàn thành ít nhất một kịch bản GameDay có mốc thời gian và log thực tế.
* [Module 09](../09-toan-dien-observability/README.md): CloudWatch Logs và Metrics sẵn sàng trích xuất biểu đồ.

---

## 6. Kiểm Tra Đạt (Verification)

| Hạng Mục | Lệnh Kiểm Tra / Metric | Kỳ Vọng Đạt |
| :--- | :--- | :--- |
| **Tính Hiện Hữu Báo Cáo** | `test -f evidence/05-reports/INCIDENT-POST-MORTEM-ASLR.md` | Tệp tồn tại và có dung lượng hợp lệ |
| **Đầy Đủ 4 Mốc Thời Gian** | Kiểm tra trường $T_{fault}, T_{detect}, T_{mitigate}, T_{recover}$ | Đầy đủ định dạng ISO 8601 UTC và logic thời gian hợp lệ |
| **Tính Hợp Lệ SRE Metrics** | Kiểm tra $MTTD$ và $MTTR$ | $MTTD = T_{detect} - T_{fault}$, $MTTR = T_{recover} - T_{fault}$ |
| **Phân Tích 5 Whys & Actions** | Đọc nội dung phần 3 và phần 5 | Có 5 bước phân tích kỹ thuật và bảng Action Items có người nhận |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

> [!NOTE]
> Báo cáo Post-Mortem tuân thủ văn hóa Blameless (không quy kết trách nhiệm cá nhân), tập trung vào cải tiến kiến trúc và quy trình kỹ thuật.

### Kế Hoạch Quản Lý Báo Cáo
Tài liệu được quản lý phiên bản trong Git repository. Mọi chỉnh sửa được thực hiện thông qua Pull Request có review của Tech Lead và SRE Lead.
