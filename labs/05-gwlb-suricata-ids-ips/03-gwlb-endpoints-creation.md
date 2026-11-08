# 05.03 — Đặc Tả Tạo Endpoint Service & Hai Zonal GWLB Endpoints Riêng Biệt (AZ-a, AZ-b)

> **Mã bài lab:** `05.03`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore) — Subnets: `fabric-insp-gwlbe-1a`, `fabric-insp-gwlbe-1b`
> **File bằng chứng:** `evidence/05-gwlb/03-zonal-gwlbe-active.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả VPC Endpoint Service và hai Zonal Gateway Load Balancer Endpoints (GWLBe) độc lập đặt tại hai vùng sẵn sàng `1a` và `1b` của Inspection VPC nhằm làm next-hop định tuyến đưa lưu lượng mạng vào cụm kiểm tra Suricata mà không phá vỡ tính đối xứng theo AZ.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Vị Trí / Subnet / AZ | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-gwlb-endpoint-service` | `AWS::EC2::VPCEndpointService` | `fabric-inspection-vpc` | Chờ runtime ID |
| `fabric-gwlbe-1a` | `AWS::EC2::VPCEndpoint` (GWLB) | `fabric-insp-gwlbe-1a` (`ap-southeast-1a`) | `vpce-0f16354ca5bb55c14` (Subnet: `subnet-0aebf9d83c8118058`) |
| `fabric-gwlbe-1b` | `AWS::EC2::VPCEndpoint` (GWLB) | `fabric-insp-gwlbe-1b` (`ap-southeast-1b`) | `vpce-0b48242bff7b44479` (Subnet: `subnet-0a1a561fe99bcc9fd`) |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-gwlb-endpoint-service` / `fabric-gwlbe-1a` / `fabric-gwlbe-1b` | Endpoint Service và 2 GWLB Endpoints |
| `Project` | `aws-eks-secure-network-fabric` | Endpoint Service và 2 GWLB Endpoints |
| `Environment` | `prod` | Endpoint Service và 2 GWLB Endpoints |
| `ManagedBy` | `manual` | Quản trị điểm kết nối mạng thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Cấu Hình GWLB Endpoint Service

- **Gateway Load Balancer:** Liên kết với `fabric-gwlb`.
- **Acceptance Required:** `false` (Không yêu cầu phê duyệt thủ công, tự động chấp nhận kết nối nội bộ).
- **Supported IP Address Types:** `ipv4`.

### 4.2 Cấu Hình Kỹ Thuật Zonal Endpoints (Bảo Toàn Tính Đối Xứng)

| Thuộc Tính | Endpoint AZ-a (`fabric-gwlbe-1a`) | Endpoint AZ-b (`fabric-gwlbe-1b`) | Lý Do Thiết Kế |
| :--- | :--- | :--- | :--- |
| **Endpoint Type** | `GatewayLoadBalancer` | `GatewayLoadBalancer` | Nhận và chuyển tiếp gói tin ở tầng mạng L3/L4. |
| **Target Service** | `fabric-gwlb-endpoint-service` | `fabric-gwlb-endpoint-service` | Điểm truy cập GWLB qua AWS PrivateLink. |
| **Subnet Binding** | `fabric-insp-gwlbe-1a` (`10.70.1.0/28`) | `fabric-insp-gwlbe-1b` (`10.70.1.16/28`) | Bắt buộc cô lập theo từng AZ đơn lẻ. |
| **Availability Zone** | `ap-southeast-1a` | `ap-southeast-1b` | Tránh hiện tượng định tuyến chéo AZ (cross-zone routing leak). |

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `05.02`: GWLB `fabric-gwlb` phải ở trạng thái `active` và có targets `healthy`.
- Phụ thuộc vào `02.01`: Subnets `fabric-insp-gwlbe-1a/b` sẵn sàng.
- Là điều kiện tiên quyết cho việc gắn route next-hop trong bảng định tuyến tại `05.04`.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng thái 2 Endpoints** | `aws ec2 describe-vpc-endpoints --filters "Name=tag:Name,Values=fabric-gwlbe-*"` | Cả 2 bản ghi đều có `State: available`. |
| **Xác thực Subnet Binding** | Kiểm tra trường `SubnetIds` của từng endpoint | `fabric-gwlbe-1a` chỉ trỏ về `subnet-0aebf9d83c8118058`; `fabric-gwlbe-1b` chỉ trỏ về `subnet-0a1a561fe99bcc9fd`. |
| **Acceptance Status** | `aws ec2 describe-vpc-endpoint-service-configurations` | `AcceptanceRequired: false`. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo tính toàn vẹn phiên (Session Stickiness):** Không gộp 2 subnet của 2 AZ vào cùng một GWLBe. Mỗi AZ bắt buộc phải có GWLBe riêng để đảm bảo TGW Appliance Mode giữ đối xứng cả chiều đi và về trên cùng một inspection firewall.
- **Quy trình Rollback:**
  ```bash
  # Xóa 2 GWLB Endpoints
  aws ec2 delete-vpc-endpoints --region ap-southeast-1 --vpc-endpoint-ids vpce-0f16354ca5bb55c14 vpce-0b48242bff7b44479

  # Xóa Endpoint Service
  aws ec2 delete-vpc-endpoint-service-configurations --region ap-southeast-1 --service-ids <ServiceId>
  ```
