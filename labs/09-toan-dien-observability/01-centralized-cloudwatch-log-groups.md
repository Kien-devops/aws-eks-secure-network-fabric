# 09.01 — Đặc Tả Khởi Tạo & Quản Trị Hệ Thống CloudWatch Log Groups Tập Trung

> **Mã bài lab:** `09.01`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/09-observability/log-groups-inventory.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả danh mục 8 CloudWatch Log Groups tập trung bao quát toàn bộ các tầng mạng VPC Flow Logs, Transit Gateway Flow Logs, Suricata EVE JSON và AWS Network Firewall với chính sách lưu trữ 7 ngày nhằm phục vụ giám sát và tối ưu chi phí FinOps.

---

## 2. Tài Nguyên (Resources)

| Tên Logical Log Group | Loại Resource | Vị Trí / Khu Vực | Retention (Snapshot) |
| :--- | :--- | :--- | :---: |
| `/aws/vpc/fabric-edge-flow` | `AWS::Logs::LogGroup` | Regional (`ap-southeast-1`) | 7 days |
| `/aws/vpc/fabric-core-flow` | `AWS::Logs::LogGroup` | Regional (`ap-southeast-1`) | 7 days |
| `/aws/vpc/fabric-inspection-flow` | `AWS::Logs::LogGroup` | Regional (`ap-southeast-1`) | 7 days |
| `/aws/vpc/fabric-egress-flow` | `AWS::Logs::LogGroup` | Regional (`ap-southeast-1`) | 7 days |
| `/aws/tgw/fabric-tgw-flow` | `AWS::Logs::LogGroup` | Regional (`ap-southeast-1`) | 7 days |
| `/aws/network-firewall/fabric-egress-alerts` | `AWS::Logs::LogGroup` | Regional (`ap-southeast-1`) | 7 days |
| `/aws/network-firewall/fabric-egress-flows` | `AWS::Logs::LogGroup` | Regional (`ap-southeast-1`) | 7 days |
| `/aws/suricata/fabric-inspection-eve` | `AWS::Logs::LogGroup` | Regional (`ap-southeast-1`) | 7 days |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `/aws/*` | Toàn bộ 8 Log Groups |
| `Project` | `aws-eks-secure-network-fabric` | Toàn bộ 8 Log Groups |
| `Environment` | `prod` | Toàn bộ 8 Log Groups |
| `ManagedBy` | `manual` | Quản trị nhật ký giám sát thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Chính Sách Lưu Trữ (Retention Policy)

- **Retention Period:** `7 days (1 week)` trên toàn bộ 8 log groups.
- **Mục đích FinOps:** Tránh tích lũy dung lượng nạp lớn, giữ tổng chi phí lưu trữ CloudWatch dưới ngưỡng ngân sách quy định ($50.00 USD).
- **Log Class:** `Standard` (Cho phép phân tích chuyên sâu qua CloudWatch Logs Insights).
- **Mã Hóa:** Default AWS KMS encryption.

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `02.01` (4 VPCs đã khởi tạo).
- Là điều kiện tiên quyết thu thập nhật ký cho `02.05` (VPC Flow Logs), `06.03` (Network Firewall Logs), `09.02` (Suricata Aggregation), và `09.03` (Insights Queries).

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Số Lượng Log Groups** | `aws logs describe-log-groups --log-group-name-prefix "/aws/"` | Hiển thị đủ 8 Log Groups có tiền tố `fabric`. |
| **Cấu Hình Retention** | Kiểm tra trường `retentionInDays` của 8 groups | Tất cả đều có giá trị chính xác là `7`. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo tích lũy chi phí:** Tuyệt đối không để `Never Expire` trên log groups của môi trường lab vì lưu lượng flow logs và Suricata EVE logs có thể sinh ra hàng GB mỗi ngày.
- **Quy trình Rollback:**
  ```bash
  # Xóa toàn bộ 8 Log Groups
  for lg in /aws/vpc/fabric-edge-flow /aws/vpc/fabric-core-flow /aws/vpc/fabric-inspection-flow /aws/vpc/fabric-egress-flow /aws/tgw/fabric-tgw-flow /aws/network-firewall/fabric-egress-alerts /aws/network-firewall/fabric-egress-flows /aws/suricata/fabric-inspection-eve; do
    aws logs delete-log-group --region ap-southeast-1 --log-group-name "$lg" 2>/dev/null || true
  done
  ```
