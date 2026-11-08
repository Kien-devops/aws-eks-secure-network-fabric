# 04.01 — Đặc Tả Aurora PostgreSQL & ElastiCache Redis Tại Core Data Subnets

> **Mã bài lab:** `04.01`
> **Trạng thái tài liệu:** `READY_TO_RUN`
> **Vùng triển khai:** `ap-southeast-1` (Singapore) — Subnets: `10.50.20.0/24`, `10.50.21.0/24`
> **File bằng chứng:** `evidence/04-workloads/01-database-and-cache.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả tài nguyên tầng lưu trữ dữ liệu riêng tư bao gồm cụm cơ sở dữ liệu Amazon Aurora PostgreSQL Serverless v2, bộ đệm phân tán Amazon ElastiCache Redis và hàng đợi Amazon SQS được cô lập hoàn toàn bên trong Core Data Subnets, chỉ cho phép `core-service` truy cập.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Vị Trí / Subnet / AZ | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-core-data-sg` | `AWS::EC2::SecurityGroup` | `fabric-core-vpc` | Chờ runtime ID |
| `fabric-core-rds-subnet-group` | `AWS::RDS::DBSubnetGroup` | `fabric-core-data-1a`, `1b` | Chờ runtime ID |
| `fabric-core-redis-subnet-group` | `AWS::ElastiCache::SubnetGroup` | `fabric-core-data-1a`, `1b` | Chờ runtime ID |
| `fabric-core-db` | `AWS::RDS::DBCluster` | Multi-AZ Serverless v2 | `fabric-core-db.cluster-***.ap-southeast-1.rds.amazonaws.com` |
| `fabric-core-redis` | `AWS::ElastiCache::ReplicationGroup` | Multi-AZ (1 primary, 1 replica) | Primary Endpoint: `rediss://...` |
| `fabric-order-events` | `AWS::SQS::Queue` | Regional (`ap-southeast-1`) | `arn:aws:sqs:ap-southeast-1:123456789012:fabric-order-events` |
| `fabric-order-events-dlq` | `AWS::SQS::Queue` | Regional (`ap-southeast-1`) | `arn:aws:sqs:ap-southeast-1:123456789012:fabric-order-events-dlq` |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-core-*` / `fabric-order-events` | Toàn bộ tài nguyên DB, Cache, SQS, Security Groups |
| `Project` | `aws-eks-secure-network-fabric` | Toàn bộ tài nguyên DB, Cache, SQS, Security Groups |
| `Environment` | `prod` | Toàn bộ tài nguyên DB, Cache, SQS, Security Groups |
| `ManagedBy` | `manual` | Quản trị tài nguyên tầng lưu trữ thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Security Group Bảo Vệ Tầng Dữ Liệu (`fabric-core-data-sg`)

- **Inbound Rules:**
  - `TCP 5432` (PostgreSQL) từ Core Node Subnets (`10.50.8.0/22`, `10.50.12.0/22`).
  - `TCP 6379` (Redis) từ Core Node Subnets (`10.50.8.0/22`, `10.50.12.0/22`).
- **Nguyên tắc cô lập:** Tuyệt đối cấm kết nối trực tiếp từ Edge VPC (`10.40.0.0/16`) hay Internet. Toàn bộ truy vấn dữ liệu phải do `core-service` thực thi.

### 4.2 Cấu Hình Amazon Aurora PostgreSQL Serverless v2

- **Cluster Identifier:** `fabric-core-db`
- **Engine Type:** `Aurora (PostgreSQL Compatible)` version `16.x`
- **Instance Type:** Serverless v2 (Dải ACU: Min `0.5` ACU = 1 GiB RAM, Max `1.0` ACU = 2 GiB RAM).
- **High Availability:** Bật multi-AZ replica trên `ap-southeast-1a` và `ap-southeast-1b`.
- **Public Access:** `No`.
- **Credentials:** Tự động sinh và lưu trữ trong AWS Secrets Manager (`rds-db-credentials`).

### 4.3 Cấu Hình Amazon ElastiCache Redis

- **Replication Group Identifier:** `fabric-core-redis`
- **Node Type:** `cache.t4g.micro` (1 Primary + 1 Read Replica, tự động failover).
- **Mã hóa:** `At-Rest Encryption: Enabled`, `In-Transit Encryption: Enabled` (TLS `rediss://`).

### 4.4 Cấu Hình Hàng Đợi Amazon SQS

- **Queue Name:** `fabric-order-events` (Standard Queue).
- **Dead-Letter Queue:** `fabric-order-events-dlq` (Max receives = 5, retention = 14 ngày).
- **Mã hóa:** SSE-SQS (KMS-managed).

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `02.01`: Subnets `fabric-core-data-1a/b` và Core VPC CIDR.
- Phụ thuộc vào `02.04`: Bảng định tuyến `fabric-core-data-rt` cô lập không có đường ra Internet hay TGW.
- Phụ thuộc vào `02.06`: SQS VPC Endpoint và Secrets Manager VPC Endpoint trong Core VPC.
- Là điều kiện tiên quyết cho việc phân giải DNS tại `04.02` và triển khai microservices tại `04.04`.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng thái Aurora Cluster** | `aws rds describe-db-clusters --db-cluster-identifier fabric-core-db` | `Status: available`, `ServerlessV2Min: 0.5`. |
| **Trạng thái ElastiCache** | `aws elasticache describe-replication-groups --replication-group-id fabric-core-redis` | `Status: available`, `TransitEncryptionEnabled: true`. |
| **Trạng thái SQS Queues** | `aws sqs get-queue-attributes --queue-url <url> --attribute-names All` | Queue hoạt động, liên kết đúng Dead-Letter Queue. |
| **Bảo vệ Security Group** | Kiểm tra ingress rules của `fabric-core-data-sg` | Chỉ chấp nhận kết nối 5432 & 6379 từ Core Node Subnets. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo chi phí:** Aurora Serverless v2 và ElastiCache tiêu tốn chi phí cố định theo giờ. Tạm dừng (Pause/Stop) cụm RDS khi không dùng đến.
- **Quy trình Rollback:**
  ```bash
  # Xóa Aurora DB Cluster (Bỏ qua Final Snapshot cho môi trường lab)
  aws rds delete-db-cluster --region ap-southeast-1 --db-cluster-identifier fabric-core-db --skip-final-snapshot

  # Xóa ElastiCache Replication Group
  aws elasticache delete-replication-group --region ap-southeast-1 --replication-group-id fabric-core-redis

  # Xóa SQS Queues
  aws sqs delete-queue --region ap-southeast-1 --queue-url <QueueUrl>
  aws sqs delete-queue --region ap-southeast-1 --queue-url <DLQUrl>

  # Xóa Security Group
  aws ec2 delete-security-group --region ap-southeast-1 --group-id <DataSGId>
  ```
