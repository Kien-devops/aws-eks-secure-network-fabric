# Module 04: Phân Bổ Microservices (app3) & Định Danh Nội Bộ

## 1. Mục Tiêu Kỹ Thuật
- **Mục tiêu:**
  - Triển khai 5 microservices từ kho ứng dụng `app3` lên 2 cụm EKS theo nguyên tắc phân tách vùng tin cậy:
    - **Edge EKS:** `frontend` (giao diện tiếp nhận từ Internet) và `auth-service` (xác thực danh tính).
    - **Core EKS:** `order-service` (nghiệp vụ chính), `inventory-service` (kho hàng), `payment-worker` (thanh toán).
  - Khởi tạo Amazon Aurora PostgreSQL Serverless v2 và ElastiCache Redis trong Private Data Subnets của Core VPC.
  - Cấu hình Route 53 Private Hosted Zone (`internal.fabric`) gắn vào cả Edge VPC và Core VPC.
  - Thiết lập Internal Network Load Balancer (NLB) tại Core VPC có hỗ trợ TLS Termination.

---

## 2. Bố Trí Dịch Vụ & Luồng Gọi Nội Bộ

```text
[Edge EKS: frontend]
        | (HTTPS / TLS 1.3)
        v
[Route 53 Private Hosted Zone: order.internal.fabric]
        |
        v
[Core VPC: Internal NLB (Private Subnet 10.50.20.x)]
        |
        v
[Core EKS: order-service Pod]
        |
        +---> [Aurora PostgreSQL (Data Subnet 10.50.20.x)]
        +---> [ElastiCache Redis (Data Subnet 10.50.21.x)]
        +---> [AWS SQS (via VPC Endpoint nội bộ)]
```

---

## 3. Các Bước Thực Hiện Chi Tiết

### Bước 1: Khởi tạo Dịch Vụ Cơ Sở Dữ Liệu & Hàng Đợi (Core VPC)
1. Tạo Subnet Group cho Aurora PostgreSQL và ElastiCache Redis trong `Data Subnet`.
2. Tạo Aurora Cluster:
   - Engine: PostgreSQL (v15+)
   - Mode: Serverless v2 (0.5 - 2 ACUs)
3. Tạo SQS Queue: `fabric-order-events.fifo` và Dead-Letter Queue (DLQ).
4. Khởi tạo AWS Interface VPC Endpoint cho SQS trong Core VPC.

### Bước 2: Thiết lập Route 53 Private Hosted Zone
Tạo Private Hosted Zone với tên miền `internal.fabric` và liên kết với cả `fabric-edge-vpc` và `fabric-core-vpc`.

### Bước 3: Triển khai Ứng dụng qua GitOps (Argo CD)
1. Đẩy manifests từ repo `aws-eks-secure-network-fabric-app`:
   - `gitops/edge/`: Deploy `frontend` và `auth-service`.
   - `gitops/core/`: Deploy `order-service`, `inventory-service`, `payment-worker`.
2. Toàn bộ hình ảnh container tham chiếu bằng SHA digest bất biến (`@sha256:...`).

---

## 4. Xác Minh (Verification)
Từ một Pod trong Edge EKS, kiểm tra phân giải DNS nội bộ và kết nối tới Core NLB:
```bash
nslookup order.internal.fabric
curl -Iv https://order.internal.fabric/health --insecure
```

---

## 5. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] 5 microservices chạy ổn định trên đúng cluster phân bổ (Edge vs Core).
- [ ] Database Aurora PostgreSQL và Redis chỉ nhận traffic từ Core Private Node Subnets.
- [ ] Tên miền `internal.fabric` phân giải chính xác sang địa chỉ IP private của Core Internal NLB.
