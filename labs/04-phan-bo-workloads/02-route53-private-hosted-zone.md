# 04.02 — Đặc Tả Route 53 Private Hosted Zone Cho Nội Bộ Fabric

> **Mã bài lab:** `04.02`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/04-workloads/02-route53-phz.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả Private Hosted Zone `fabric.internal` trên Amazon Route 53 và liên kết đồng thời với Edge VPC và Core VPC nhằm cung cấp cơ chế Service Discovery nội bộ ổn định cho cơ sở dữ liệu, bộ nhớ đệm và API nội bộ giữa các microservices.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Vị Trí / VPC Liên Kết | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric.internal` | `AWS::Route53::HostedZone` (Private) | `fabric-edge-vpc`, `fabric-core-vpc` | `Z01140082R4J17K2K8E7` (Ví dụ ID runtime) |
| `db.fabric.internal` | `AWS::Route53::RecordSet` (CNAME) | `fabric.internal` | CNAME -> Aurora Writer Endpoint |
| `dbr.fabric.internal` | `AWS::Route53::RecordSet` (CNAME) | `fabric.internal` | CNAME -> Aurora Reader Endpoint |
| `redis.fabric.internal` | `AWS::Route53::RecordSet` (CNAME) | `fabric.internal` | CNAME -> ElastiCache Primary Endpoint |
| `redis-ro.fabric.internal` | `AWS::Route53::RecordSet` (CNAME) | `fabric.internal` | CNAME -> ElastiCache Replica Endpoint |
| `core.fabric.internal` | `AWS::Route53::RecordSet` (CNAME) | `fabric.internal` | CNAME -> Internal NLB DNS Name |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric.internal` | Route 53 Hosted Zone |
| `Project` | `aws-eks-secure-network-fabric` | Route 53 Hosted Zone |
| `Environment` | `prod` | Route 53 Hosted Zone |
| `ManagedBy` | `manual` | Quản trị phân giải tên miền thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Thuộc Tính Hosted Zone

- **Zone Name:** `fabric.internal`
- **Zone Type:** `Private Hosted Zone`
- **Associated VPCs:**
  - `fabric-edge-vpc` (`vpc-0468b18dddd1d4d2d`) tại Singapore (`ap-southeast-1`).
  - `fabric-core-vpc` (`vpc-09888cc991104c959`) tại Singapore (`ap-southeast-1`).
- **Yêu cầu VPC:** Cả hai VPC bắt buộc phải bật thuộc tính `enableDnsHostnames = true` và `enableDnsSupport = true`.

### 4.2 Ma Trận Bản Ghi DNS Nội Bộ (DNS Resource Record Sets)

| Record Name | Type | TTL | Target Value | Mục Đích Thiết Kế |
| :--- | :---: | :---: | :--- | :--- |
| `db.fabric.internal` | `CNAME` | 60s | Aurora PostgreSQL Writer Endpoint | Điểm truy cập ghi cho `core-service`. |
| `dbr.fabric.internal` | `CNAME` | 60s | Aurora PostgreSQL Reader Endpoint | Điểm truy cập đọc phân tán. |
| `redis.fabric.internal` | `CNAME` | 60s | ElastiCache Redis Primary Hostname | Đọc/ghi cache phiên và dữ liệu nóng. |
| `redis-ro.fabric.internal` | `CNAME` | 60s | ElastiCache Redis Replica Hostname | Đọc cache phân tải. |
| `core.fabric.internal` | `CNAME` | 60s | `fabric-core-internal-nlb` DNS Name | Điểm giao tiếp East-West từ `edge-frontend` sang `core-service`. |

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `02.01`: Cả Edge VPC và Core VPC phải được khởi tạo với DNS Hostnames & DNS Resolution bật.
- Phụ thuộc vào `04.01`: Cụm Aurora PostgreSQL và ElastiCache Redis phải sẵn sàng để lấy endpoint đích.
- Phụ thuộc vào `04.03`: Internal NLB của Core VPC phải sẵn sàng để trỏ bản ghi `core.fabric.internal`.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng thái Hosted Zone** | `aws route53 list-hosted-zones-by-name --dns-name fabric.internal` | Hosted zone tồn tại và có thuộc tính `Config.PrivateZone: true`. |
| **Xác thực Liên kết VPCs** | `aws route53 get-hosted-zone --id <ZoneId>` | Danh sách `VPCs` hiển thị đủ cả Edge VPC và Core VPC. |
| **Danh sách Record Sets** | `aws route53 list-resource-record-sets --hosted-zone-id <ZoneId>` | Hiển thị đủ các bản ghi CNAME: `db`, `dbr`, `redis`, `redis-ro`, `core`. |
| **Phân giải DNS từ Pod** | `kubectl exec -n fabric-apps <pod> -- nslookup db.fabric.internal` | Trả về đúng địa chỉ CNAME và IP phân giải của Aurora. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo lỗi phân giải:** Nếu thiếu association với Edge VPC, `edge-frontend` sẽ hoàn toàn mất liên lạc với `core-service`, gây đứt gãy luồng ứng dụng.
- **Quy trình Rollback:**
  ```bash
  # Xóa các bản ghi CNAME thủ công
  aws route53 change-resource-record-sets --hosted-zone-id <ZoneId> --change-batch file://delete-records.json

  # Gỡ bỏ association của fabric-core-vpc
  aws route53 disassociate-vpc-from-hosted-zone --hosted-zone-id <ZoneId> --vpc VPCRegion=ap-southeast-1,VPCId=<CoreVPCId>

  # Xóa Hosted Zone
  aws route53 delete-hosted-zone --id <ZoneId>
  ```
