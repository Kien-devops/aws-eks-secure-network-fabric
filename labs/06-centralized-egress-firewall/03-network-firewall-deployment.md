# 06.03 — Đặc Tả Triển Khai AWS Network Firewall Tại Egress VPC & Bật Appliance Mode

> **Mã bài lab:** `06.03`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore) — Subnets: `fabric-egress-fw-1a`, `fabric-egress-fw-1b`
> **File bằng chứng:** `evidence/06-firewall/03-firewall-endpoints.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả tài nguyên AWS Network Firewall triển khai đa AZ trong Centralized Egress VPC kèm cơ chế ghi nhật ký Alert/Flow tập trung về CloudWatch Logs và kích hoạt Appliance Mode trên TGW Attachment nhằm đảm bảo phiên kết nối ra Internet được xử lý đối xứng.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Vị Trí / Subnet / AZ | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-egress-nfw` | `AWS::NetworkFirewall::Firewall` | `fabric-egress-vpc` (`1a`, `1b`) | Status: `READY`<br>Policy: `fabric-egress-fw-policy` |
| `fabric-egress-fw-vpce-1a` | `AWS::EC2::VPCEndpoint` | `fabric-egress-fw-1a` (`ap-southeast-1a`) | `vpce-008c9b7972ba12c2c` (Subnet: `subnet-0c7142131794aa34c`) |
| `fabric-egress-fw-vpce-1b` | `AWS::EC2::VPCEndpoint` | `fabric-egress-fw-1b` (`ap-southeast-1b`) | `vpce-0a4193a072d8c041f` (Subnet: `subnet-05ce922d28724c2f9`) |
| `/aws/network-firewall/fabric-egress-alerts` | `AWS::Logs::LogGroup` | Regional (`ap-southeast-1`) | Retention: `7 days` |
| `/aws/network-firewall/fabric-egress-flows` | `AWS::Logs::LogGroup` | Regional (`ap-southeast-1`) | Retention: `7 days` |
| `fabric-egress-tgw-attachment` | `AWS::EC2::TransitGatewayVpcAttachment` | `fabric-egress-vpc` | `tgw-attach-0646bdfa31c6c8e66` (`ApplianceMode: enable`) |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-egress-nfw` / `fabric-egress-tgw-attachment` | Network Firewall, TGW Attachment |
| `Project` | `aws-eks-secure-network-fabric` | Network Firewall, Log Groups |
| `Environment` | `prod` | Network Firewall, Log Groups |
| `ManagedBy` | `manual` | Quản trị hạ tầng tường lửa thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Cấu Hình Kỹ Thuật AWS Network Firewall

- **Firewall Policy:** `fabric-egress-fw-policy`
- **VPC Binding:** `fabric-egress-vpc` (`10.80.0.0/16`)
- **Subnet Mappings (Zonal Placement):**
  - `ap-southeast-1a`: `fabric-egress-fw-1a` (`10.80.1.0/28`) -> Sinh endpoint `vpce-008c9b7972ba12c2c`.
  - `ap-southeast-1b`: `fabric-egress-fw-1b` (`10.80.1.16/28`) -> Sinh endpoint `vpce-0a4193a072d8c041f`.
- **Logging Configuration:**
  - `ALERT` Logs -> Đẩy về `/aws/network-firewall/fabric-egress-alerts` (Retention 7 ngày).
  - `FLOW` Logs -> Đẩy về `/aws/network-firewall/fabric-egress-flows` (Retention 7 ngày).

### 4.2 Cấu Hình TGW Attachment Appliance Mode

- **Attachment Name:** `fabric-egress-tgw-attachment`
- **ApplianceModeSupport:** `enable` (Bắt buộc để TGW chuyển tiếp lưu lượng hai chiều của cùng một phiên qua cùng một AZ endpoint).

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `06.01`: Cụm NAT Gateways sẵn sàng.
- Phụ thuộc vào `06.02`: Firewall Policy `fabric-egress-fw-policy` ở trạng thái `ACTIVE`.
- Phụ thuộc vào `02.01`: Subnets `fabric-egress-fw-1a/b` sẵn sàng.
- Là điều kiện tiên quyết cho việc gắn next-hop trong bảng định tuyến tại `06.04`.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng thái Network Firewall** | `aws network-firewall describe-firewall --firewall-name fabric-egress-nfw` | `FirewallStatus.Status: READY`, `ConfigurationSyncStateSummary: IN_SYNC`. |
| **Firewall Endpoints per AZ** | Kiểm tra danh sách `SyncStates` trong chi tiết firewall | Có đủ 2 endpoints `vpce-008c9b7972ba12c2c` (1a) và `vpce-0a4193a072d8c041f` (1b). |
| **Logging Delivery** | `aws network-firewall describe-logging-configuration --firewall-name fabric-egress-nfw` | Cả 2 log types `ALERT` và `FLOW` đều trỏ đúng CloudWatch Log Groups. |
| **TGW Appliance Mode** | `aws ec2 describe-transit-gateway-vpc-attachments --transit-gateway-attachment-ids tgw-attach-0646bdfa31c6c8e66` | `ApplianceModeSupport: enable`. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo chi phí cao:** AWS Network Firewall tính phí ~$0.395 USD/giờ/endpoint (~$18.96 USD/ngày cho 2 AZs). Cần xóa firewall ngay khi hoàn tất thử nghiệm.
- **Quy trình Rollback:**
  ```bash
  # Xóa AWS Network Firewall
  aws network-firewall delete-firewall --region ap-southeast-1 --firewall-name fabric-egress-nfw

  # Xóa CloudWatch Log Groups
  aws logs delete-log-group --region ap-southeast-1 --log-group-name /aws/network-firewall/fabric-egress-alerts
  aws logs delete-log-group --region ap-southeast-1 --log-group-name /aws/network-firewall/fabric-egress-flows
  ```
