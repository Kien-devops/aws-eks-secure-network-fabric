# 05.02 — Đặc Tả Gateway Load Balancer (GWLB) & Target Group GENEVE

> **Mã bài lab:** `05.02`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/05-gwlb/02-gwlb-healthy.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả tài nguyên AWS Gateway Load Balancer (GWLB) và Target Group giao thức GENEVE (UDP 6081) đa AZ nhằm phân phối lưu lượng gói tin mạng trong suốt (bump-in-the-wire) tới cụm máy chủ Suricata với cơ chế kiểm tra sức khỏe độc lập qua cổng HTTP 80.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Vị Trí / Subnet / AZ | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-suricata-tg` | `AWS::ElasticLoadBalancingV2::TargetGroup` | `fabric-inspection-vpc` | Protocol: `GENEVE:6081`<br>Targets: `i-089127472b112deff`, `i-091e84ae2b923eea2` |
| `fabric-gwlb` | `AWS::ElasticLoadBalancingV2::LoadBalancer` | `fabric-insp-fw-1a`, `1b` | Type: `gateway`, State: `active`<br>VPC: `vpc-0c94a30a1a915fc0f` |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-gwlb` / `fabric-suricata-tg` | GWLB và Target Group |
| `Project` | `aws-eks-secure-network-fabric` | GWLB và Target Group |
| `Environment` | `prod` | GWLB và Target Group |
| `ManagedBy` | `manual` | Quản trị hạ tầng GWLB thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Cấu Hình Target Group GENEVE (`fabric-suricata-tg`)

- **Target Type:** `instance`
- **Protocol & Port:** `GENEVE` (UDP 6081).
- **VPC:** `fabric-inspection-vpc` (`10.70.0.0/16`).
- **Health Check Specification:**
  - Protocol: `HTTP` (Path: `/`, Port: Override `80`).
  - Healthy / Unhealthy Threshold: `2` / `2`.
  - Timeout: `5s`, Interval: `10s` (Hỗ trợ phát hiện lỗi và failover nhanh trong GameDay).
  - Success Codes: `200`.

### 4.2 Cấu Hình Gateway Load Balancer (`fabric-gwlb`)

- **Load Balancer Type:** `gateway`
- **IP Address Type:** `ipv4`
- **Subnet Mappings:**
  - `ap-southeast-1a`: `fabric-insp-fw-1a` (`subnet-0b743a1b6492b62ce`)
  - `ap-southeast-1b`: `fabric-insp-fw-1b` (`subnet-00621165b37f9a04e`)
- **Attributes:**
  - `load_balancing.cross_zone.enabled: true` (Đảm bảo cân bằng tải chéo AZ khi một appliance gặp sự cố).
- **Default Action:** Chuyển tiếp (Forward) 100% lưu lượng tới `fabric-suricata-tg`.

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `05.01`: Cả hai máy ảo Suricata EC2 phải đang chạy và trả về HTTP 200 trên cổng 80.
- Phụ thuộc vào `02.01`: Subnets `fabric-insp-fw-1a/b` sẵn sàng.
- Là điều kiện tiên quyết bắt buộc để khởi tạo GWLB VPC Endpoint Service và Endpoints tại `05.03`.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng thái GWLB** | `aws elbv2 describe-load-balancers --names fabric-gwlb` | `State.Code: active`, `Type: gateway`. |
| **Sức khỏe Targets** | `aws elbv2 describe-target-health --target-group-arn <TGArn>` | Cả 2 instances `i-089127472b112deff` và `i-091e84ae2b923eea2` đều có `TargetHealth.State: healthy`. |
| **Cross-Zone Attribute** | Kiểm tra load balancer attributes | `load_balancing.cross_zone.enabled: true`. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo tính tương thích Health Check:** Tuyệt đối không dùng giao thức GENEVE để kiểm tra sức khỏe của Target Group vì GWLB không hỗ trợ probe GENEVE tự sinh, bắt buộc dùng TCP hoặc HTTP.
- **Quy trình Rollback:**
  ```bash
  # Xóa GWLB
  aws elbv2 delete-load-balancer --region ap-southeast-1 --load-balancer-arn <GWLBArn>

  # Xóa Target Group sau khi GWLB đã hủy
  aws elbv2 delete-target-group --region ap-southeast-1 --target-group-arn <TargetGroupArn>
  ```
