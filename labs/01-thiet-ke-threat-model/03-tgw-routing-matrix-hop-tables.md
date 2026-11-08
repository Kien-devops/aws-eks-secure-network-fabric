# Lab 01.03: Ma Trận Định Tuyến TGW & Bảng Bước Nhảy Gói Tin (Hop Tables)

**Mã tài liệu:** `LAB-01-03`
**Trạng thái:** `RUNTIME_PASS`
**Vùng áp dụng:** `ap-southeast-1` (Singapore) — AZs: `ap-southeast-1a`, `ap-southeast-1b`

---

## 1. Mục Tiêu (Objective)
Đặc tả ma trận định tuyến 4 phân vùng cô lập trên AWS Transit Gateway và bảng bước nhảy (Hop Tables) cho luồng East-West qua Suricata và luồng Egress qua Network Firewall.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Định Danh Runtime (Snapshot) | Attachment Liên Kết | Chức Năng Phân Đoạn |
| :--- | :--- | :--- | :--- |
| `fabric-tgw-edge-rt` | `tgw-rtb-004772ba5b83f2b17` | `fabric-edge-tgw-attachment` | Ép traffic sang Core qua Inspection; ra Internet qua Egress |
| `fabric-tgw-core-rt` | `tgw-rtb-03c493c67bc6dc820` | `fabric-core-tgw-attachment` | Ép traffic sang Edge qua Inspection; ra Internet qua Egress |
| `fabric-tgw-inspection-rt` | `tgw-rtb-01abf43ebf7f1b21f` | `fabric-insp-tgw-attachment` | Trả traffic sạch sau kiểm tra về Edge hoặc Core |
| `fabric-tgw-egress-rt` | `tgw-rtb-066c8310ab347bf30` | `fabric-egress-tgw-attachment` | Trả traffic phản hồi từ Internet về Edge hoặc Core |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Khóa (Key) | Giá Trị (Value) | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-tgw-*-rt` | Toàn bộ TGW Route Tables |
| `Project` | `aws-eks-secure-network-fabric` | Toàn bộ TGW Route Tables |
| `Environment` | `prod` | Toàn bộ TGW Route Tables |
| `ManagedBy` | `manual` | Thiết kế định tuyến trung tâm thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Bảng Ma Trận Định Tuyến Nguồn - Đích - Next Hop - AZ
| Nguồn (Source) | Đích (Destination CIDR) | Bảng Tra Cứu (Lookup RT) | Next Hop Target | AZ Affinity (Appliance Mode) |
| :--- | :--- | :--- | :--- | :---: |
| `edge-frontend` (`10.40.0.0/16`) | `10.50.0.0/16` (Core) | `fabric-tgw-edge-rt` | `fabric-insp-tgw-attachment` | **ENABLED (AZ-a/b)** |
| `core-service` (`10.50.0.0/16`) | `10.40.0.0/16` (Edge) | `fabric-tgw-core-rt` | `fabric-insp-tgw-attachment` | **ENABLED (AZ-a/b)** |
| `fabric-inspection-vpc` | `10.40.0.0/16` (Edge) | `fabric-tgw-inspection-rt` | `fabric-edge-tgw-attachment` | Symmetric AZ Return |
| `fabric-inspection-vpc` | `10.50.0.0/16` (Core) | `fabric-tgw-inspection-rt` | `fabric-core-tgw-attachment` | Symmetric AZ Forward |
| `edge-frontend` / `core-service` | `0.0.0.0/0` (Internet) | `edge-rt` / `core-rt` | `fabric-egress-tgw-attachment` | **ENABLED (AZ-a/b)** |
| `fabric-egress-vpc` | `10.40.0.0/16` / `10.50.0.0/16` | `fabric-tgw-egress-rt` | `edge-attachment` / `core-attachment` | Return Path to Spoke |

### 4.2 Bảng Bước Nhảy Luồng Đông - Tây (East-West Hop Table)
1. **Hop 1:** `edge-frontend` Pod (`10.40.10.x`) → gọi `https://core.fabric.internal:443`.
2. **Hop 2:** Edge Node Subnet RT (`10.50.0.0/16 -> fabric-tgw`).
3. **Hop 3:** TGW `fabric-tgw-edge-rt` (`10.50.0.0/16 -> fabric-insp-tgw-attachment`).
4. **Hop 4:** Inspection TGW Subnet RT (`10.50.0.0/16 -> GWLB Endpoint` cùng AZ).
5. **Hop 5:** GWLB forward qua GENEVE UDP 6081 tới Suricata EC2 Instance cùng AZ (Verdict: ALLOW).
6. **Hop 6:** GWLB Endpoint Subnet RT (`10.50.0.0/16 -> fabric-tgw`).
7. **Hop 7:** TGW `fabric-tgw-inspection-rt` (`10.50.0.0/16 -> fabric-core-tgw-attachment`).
8. **Hop 8:** Core Private Subnet → `fabric-core-internal-nlb` → `core-service` Pod (`10.50.20.y`).

---

## 5. Phụ Thuộc (Dependencies)
- Hoàn thành quy hoạch IP tại [Lab 01.02](02-cidr-ip-allocation-plan.md).

---

## 6. Kiểm Tra Đạt (Verification)
- [x] 4 TGW Route Tables độc lập triệt tiêu hoàn toàn khả năng Route Leak trực tiếp giữa Edge và Core.
- [x] Thiết kế cờ `ApplianceModeSupport = ENABLED` trên Inspection và Egress Attachments bảo đảm tính đối xứng hai chiều.
- [x] Bằng chứng runtime đã thu thập: [`evidence/01-threat-model/03-hop-tables-spec.json`](../../evidence/01-threat-model/03-hop-tables-spec.json).

---

## 7. Cảnh Báo An Toàn & Rollback Plan
- **Cảnh báo bất đối xứng (Asymmetric drop):** Nếu tắt Appliance Mode trên Inspection Attachment, gói tin TCP midstream sẽ bị Suricata drop ngay lập tức do lệch AZ (đã chứng minh tại GameDay 10.02).
- **Kế hoạch khôi phục (Rollback):** Đảm bảo cờ Appliance Mode luôn ở trạng thái `enable` trên mọi attachment kết nối tới cụm kiểm tra trạng thái.
