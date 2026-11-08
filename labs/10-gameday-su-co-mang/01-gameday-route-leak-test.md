# 10.01 — Đặc Tả GameDay Kịch Bản 1: Sự Cố Rò Rỉ Tuyến Đường (Route Leak Attack / Drift)

> **Mã bài lab:** `10.01`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/10-gameday/gameday-01-route-leak-timeline.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả kịch bản diễn tập GameDay 10.01 tiêm lỗi định tuyến có kiểm soát (Fault Injection) bằng cách cấu hình sai static route trỏ trực tiếp sang Core VPC để cố tình bypass cụm Suricata IDS/IPS, nhằm đo lường MTTD/MTTR và kiểm chứng khả năng phòng thủ đa tầng (Defense-in-Depth).

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Vị Trí / Bảng Áp Dụng | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-tgw-edge-rt` | `AWS::EC2::TransitGatewayRouteTable` | Transit Gateway | Tuyến `10.50.0.0/16` bị tiêm lỗi |
| `fabric-core-tgw-attachment` | `AWS::EC2::TransitGatewayVpcAttachment` | Core VPC Attachment | Điểm trỏ sai bypass inspection |
| `fabric-insp-tgw-attachment` | `AWS::EC2::TransitGatewayVpcAttachment` | Inspection VPC Attachment | `tgw-attach-0fb21514974415f35` (Điểm trỏ chuẩn) |
| Timeline & Evidence | `Artifact::Evidence` | `evidence/10-gameday/` | `gameday-01-route-leak-timeline.json` |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-*-gameday` | Tài nguyên kiểm thử GameDay |
| `Project` | `aws-eks-secure-network-fabric` | Tài nguyên kiểm thử GameDay |
| `Environment` | `prod` | Tài nguyên kiểm thử GameDay |
| `ManagedBy` | `manual` | Quản trị kịch bản sự cố thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Quy Trình Tiêm Lỗi (Fault Injection Protocol)

- **Trạng thái chuẩn (Baseline):** Tuyến `10.50.0.0/16` trong `fabric-tgw-edge-rt` trỏ tới `fabric-insp-tgw-attachment` (`tgw-attach-0fb21514974415f35`).
- **Tiêm Lỗi (Fault State):** Thay thế route `10.50.0.0/16` trỏ thẳng sang `fabric-core-tgw-attachment` (bỏ qua Inspection VPC). Ghi nhận mốc thời gian $T_{fault}$ (`2026-11-07T21:57:31.892Z`).
- **Hệ quả Kiến trúc:** Chiều đi (Forward) đi thẳng sang Core VPC nhưng chiều về (Return) từ Core VPC vẫn trỏ sang Inspection VPC theo thiết kế, gây ra tình trạng bất đối xứng luồng (Asymmetric Flow) và làm đứt gãy phiên kết nối TCP.

### 4.2 Quy Trình Khắc Phục (Remediation Protocol)

- Khôi phục lại route `10.50.0.0/16` trỏ về `fabric-insp-tgw-attachment` ($T_{mitigate}$).
- Xác minh kết nối giữa `edge-frontend` và `core-service` phục hồi hoàn toàn ($T_{recover}$).

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `02.03`: Các TGW Attachments và Route Tables đang hoạt động.
- Phụ thuộc vào `04.04`: Microservices `edge-frontend` và `core-service` đang chạy.
- Phụ thuộc vào `05.04`: Luồng định tuyến East-West chuẩn đã được cắt chuyển.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Xác Nhận Route Leak** | `aws ec2 search-transit-gateway-routes --transit-gateway-route-table-id <EdgeRTId>` | Route `10.50.0.0/16` trỏ sang Core Attachment trong giai đoạn test. |
| **Bất Đối Xứng Luồng** | Thực hiện `curl -Iv https://core.fabric.internal/healthz` từ `edge-frontend` | Gặp lỗi timeout hoặc connection reset do thiếu gói tin phản hồi đối xứng. |
| **Chỉ Số MTTD / MTTR** | Phân tích file `gameday-01-route-leak-timeline.json` | $MTTD = 5.71s$, $MTTR = 14.60s$ (đáp ứng tiêu chuẩn phản ứng sự cố nhanh). |
| **Phục Hồi Hoàn Toàn** | Gọi lại `curl -Iv https://core.fabric.internal/healthz` | Trả về `HTTP/2 200 OK`. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo phạm vi ảnh hưởng (Blast Radius):** Chỉ thực hiện thay đổi trên đúng route `10.50.0.0/16` của `fabric-tgw-edge-rt`. Tuyệt đối không xóa attachment hay thay đổi các route khác của TGW.
- **Quy trình Rollback:**
  ```bash
  # Ép buộc khôi phục ngay lập tức route về Inspection Attachment
  aws ec2 replace-transit-gateway-route --region ap-southeast-1 \
    --transit-gateway-route-table-id <EdgeTgwRtId> \
    --destination-cidr-block "10.50.0.0/16" \
    --transit-gateway-attachment-id tgw-attach-0fb21514974415f35
  ```
