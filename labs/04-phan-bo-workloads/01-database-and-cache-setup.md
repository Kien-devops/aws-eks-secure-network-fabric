# 04.01 — Khởi Tạo Aurora PostgreSQL & ElastiCache Redis Tại Core Data Subnets

> **Mã bài lab:** `04.01`  
> **Trạng thái:** `DRAFT`  
> **Thời gian dự kiến:** 40 phút  
> **Chi phí ước tính:** ~$0.12 USD / giờ (Aurora Serverless v2 0.5 ACU + Redis cache)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — Subnets: `10.50.20.0/24`, `10.50.21.0/24`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành hạ tầng mạng Core VPC tại [Module 02](../02-ha-tang-mang-co-ban/README.md) và cụm Core EKS tại [Module 03](../03-cum-eks-kep/README.md).
- Data subnets (`fabric-core-data-1a`, `fabric-core-data-1b`) đã sẵn sàng.
- Đang mở phiên AWS Management Console tại Singapore `ap-southeast-1`.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để thực thi bài lab này:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:CreateDBSubnetGroup",
        "rds:CreateDBCluster",
        "rds:CreateDBInstance",
        "rds:DescribeDBClusters",
        "rds:DeleteDBCluster",
        "rds:DeleteDBInstance",
        "elasticache:CreateCacheSubnetGroup",
        "elasticache:CreateReplicationGroup",
        "elasticache:DescribeReplicationGroups",
        "elasticache:DescribeCacheClusters",
        "elasticache:DeleteReplicationGroup",
        "ec2:CreateSecurityGroup",
        "ec2:AuthorizeSecurityGroupIngress",
        "sqs:CreateQueue",
        "sqs:GetQueueAttributes",
        "sqs:TagQueue",
        "secretsmanager:CreateSecret",
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Aurora Serverless v2 (0.5 ACU) tiêu tốn ~$0.06/giờ. ElastiCache tiêu tốn ~$0.02/giờ. Cần theo dõi chặt chẽ ngân sách $50.00 USD.
- **Cảnh báo cô lập tầng dữ liệu (Zero Trust Data Isolation):** Cơ sở dữ liệu và Cache **CHỈ ĐƯỢC PHÉP ĐẶT TRONG CORE DATA SUBNETS**. Security Group của DB chỉ cho phép Inbound từ Core Node Subnet (`10.50.8.0/22`, `10.50.12.0/22`). Tuyệt đối cấm kết nối trực tiếp từ Edge VPC (`10.40.0.0/16`) hay Internet. Bất kỳ truy vấn nào từ Edge đều bắt buộc phải gọi qua API của `order-service` / `inventory-service`.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Khởi Tạo Security Group Cho Data Layer
Truy cập **VPC Console** tại Singapore `ap-southeast-1`:
1. Tại menu bên trái, chọn **Security groups** -> Nhấp **Create security group**.
2. **Details:**
   - **Security group name:** Nhập `fabric-core-data-sg`.
   - **Description:** Nhập `Allows Postgres 5432 and Redis 6379 from Core EKS Nodes only`.
   - **VPC:** Chọn `fabric-core-vpc`.
3. **Inbound rules:**
   - Nhấp **Add rule**:
     - Type: `PostgreSQL` | Protocol: `TCP` | Port: `5432`.
     - Source: `Custom` -> Nhập `10.50.8.0/22` (Core Node Subnet AZ-a).
     - Description: `PostgreSQL from Core Nodes 1a`.
   - Nhấp **Add rule**:
     - Type: `PostgreSQL` | Protocol: `TCP` | Port: `5432`.
     - Source: `Custom` -> Nhập `10.50.12.0/22` (Core Node Subnet AZ-b).
     - Description: `PostgreSQL from Core Nodes 1b`.
   - Nhấp **Add rule**:
     - Type: `Custom TCP` | Protocol: `TCP` | Port: `6379`.
     - Source: `Custom` -> Nhập `10.50.8.0/22`.
     - Description: `Redis from Core Nodes 1a`.
   - Nhấp **Add rule**:
     - Type: `Custom TCP` | Protocol: `TCP` | Port: `6379`.
     - Source: `Custom` -> Nhập `10.50.12.0/22`.
     - Description: `Redis from Core Nodes 1b`.
4. **Outbound rules:** Giữ nguyên default (All traffic).
5. **Tags:** Key: `Project` | Value: `aws-eks-secure-network-fabric`.
6. Nhấp **Create security group**.

---

### Bước 2: Tạo DB Subnet Group Cho RDS & ElastiCache Subnet Group
1. **Tạo RDS DB Subnet Group:**
   - Trên thanh tìm kiếm AWS Console, nhập `RDS` -> Chọn dịch vụ **RDS**.
   - Tại menu bên trái, chọn **Subnet groups** -> Nhấp nút cam **Create DB subnet group**.
   - **Name:** Nhập `fabric-core-rds-subnet-group`.
   - **Description:** Nhập `Core VPC data subnets for Aurora PostgreSQL`.
   - **VPC:** Chọn `fabric-core-vpc`.
   - **Add subnets:**
     - Availability Zones: Chọn cả 2 AZs: `ap-southeast-1a` và `ap-southeast-1b`.
     - Subnets: Chọn 2 subnets:
       - `fabric-core-data-1a` (`10.50.20.0/24`)
       - `fabric-core-data-1b` (`10.50.21.0/24`)
   - Nhấp **Create**.

2. **Tạo ElastiCache Subnet Group:**
   - Trên thanh tìm kiếm, nhập `ElastiCache` -> Chọn dịch vụ **ElastiCache**.
   - Tại menu bên trái, chọn **Subnet groups** -> Nhấp nút **Create subnet group**.
   - **Name:** Nhập `fabric-core-redis-subnet-group`.
   - **Description:** Nhập `Subnet group for Core Redis cache`.
   - **VPC ID:** Chọn `fabric-core-vpc`.
   - **Subnets:** Tích chọn 2 data subnets `fabric-core-data-1a` và `fabric-core-data-1b`.
   - Nhấp **Create**.

---

### Bước 3: Khởi Tạo Amazon Aurora PostgreSQL Serverless v2
Tại **RDS Console** -> Menu bên trái chọn **Databases** -> Nhấp nút cam **Create database**:
1. **Choose a database creation method:** Chọn **Standard create**.
2. **Engine options:**
   - Engine type: Chọn **Aurora (PostgreSQL Compatible)**.
   - Available versions: Chọn **Aurora PostgreSQL 16.x** (hoặc bản mới nhất).
3. **Templates:** Chọn **Dev/Test**.
4. **Settings:**
   - **DB cluster identifier:** Nhập `fabric-core-db`.
   - **Master username:** Nhập `postgresadmin`.
   - **Credentials management:** Chọn **Manage master credentials in AWS Secrets Manager** (Bảo mật tối đa, AWS tự sinh mật khẩu và xoay vòng tự động).
5. **Cluster storage configuration:** Chọn **Aurora Standard**.
6. **Instance configuration:**
   - DB instance class: Chọn **Serverless v2**.
   - **Serverless v2 capacity:**
     - **Minimum ACUs:** Nhập `0.5` (Tối thiểu 1 GiB RAM, tối ưu chi phí tối đa).
     - **Maximum ACUs:** Nhập `1.0` (Tối đa 2 GiB RAM).
7. **Availability & durability:**
   - Chọn **Create an Aurora Replica/Reader node in a different AZ** (Để đảm bảo Multi-AZ HA trên cả `ap-southeast-1a` và `ap-southeast-1b`).
8. **Connectivity:**
   - **Virtual Private Cloud (VPC):** Chọn `fabric-core-vpc`.
   - **DB subnet group:** Chọn `fabric-core-rds-subnet-group`.
   - **Public access:** Chọn **No** (Chỉ truy cập nội bộ).
   - **VPC security group (firewall):** Chọn **Choose existing** -> Chọn `fabric-core-data-sg` (Bỏ chọn default SG).
9. **Database authentication:** Chọn **Password and IAM database authentication**.
10. Nhấp nút cam **Create database** ở cuối trang.
11. Quá trình tạo cụm mất khoảng 8 đến 10 phút. Ghi nhận lại **Writer Endpoint** (dạng `fabric-core-db.cluster-xxxxxx.ap-southeast-1.rds.amazonaws.com`).

---

### Bước 4: Khởi Tạo ElastiCache Redis Cluster
Tại **ElastiCache Console** -> Chọn **Valkey / Redis caches** -> Nhấp **Create cache**:
1. **Cluster deployment:** Chọn **Design your own cache** -> **Cluster mode disabled**.
2. **Cluster info:**
   - **Name:** Nhập `fabric-core-redis`.
   - **Node type:** Chọn `cache.t4g.micro` (Tối ưu chi phí).
   - **Number of replicas:** `1` (Đặt tại AZ còn lại); bật **Multi-AZ / automatic failover**.
3. **Connectivity:**
   - **Location:** Chọn **Amazon VPC**.
   - **Subnet group:** Chọn `fabric-core-redis-subnet-group`.
   - **Security groups:** Chọn `fabric-core-data-sg`.
4. Security → bật **Encryption at rest**, **Encryption in transit**; chọn Redis AUTH hoặc RBAC phù hợp client. Lưu credential vào Secrets Manager, không ghi vào Git/evidence. Client dùng `rediss://` và kiểm tra chứng chỉ.
5. Nhấp **Create**. Ghi **Primary endpoint** từ replication group; không coi field `CacheClusters[0].Endpoint` là endpoint cluster-mode-disabled.

### Bước 5: Tạo SQS và DLQ trên Console

1. SQS → Queues → Create queue → **Standard**, tên `fabric-order-events-dlq`. Encryption: bật SSE-SQS; Message retention 14 ngày → Create.
2. Create queue → Standard → tên `fabric-order-events`; bật SSE-SQS. Visibility timeout phải lớn hơn thời gian xử lý tối đa của worker (ban đầu 120 giây, điều chỉnh theo contract ứng dụng); long polling 20 giây.
3. Dead-letter queue → Enabled → chọn `fabric-order-events-dlq`, maximum receives 5 → Create. DLQ → Redrive allow policy → By queue → chỉ cho queue nguồn vừa tạo.
4. Sao chép **Queue URL**, **Queue ARN**, **DLQ ARN**; tag cả hai `Project=aws-eks-secure-network-fabric`. Queue policy không mở public. Worker phải idempotent vì Standard queue giao ít nhất một lần; chỉ DeleteMessage sau commit xử lý thành công.

### Bước 6: Quyền workload và secret — hoàn tất trước 04.04

1. IAM → Roles → Create role → custom trust `pods.eks.amazonaws.com` với `sts:AssumeRole` và `sts:TagSession` như 03.04; tạo role riêng Order, Inventory, Payment.
2. IAM → Policies → Create policy → JSON: Order chỉ `sqs:SendMessage`, `sqs:GetQueueAttributes` trên ARN queue nguồn; Payment chỉ `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:ChangeMessageVisibility`, `sqs:GetQueueAttributes` trên queue nguồn. Inventory không được quyền SQS nếu contract không cần.
3. Secret access: chỉ `secretsmanager:GetSecretValue` trên ARN secret ứng dụng tương ứng; `kms:Decrypt` chỉ key mã hóa secret nếu dùng CMK và key policy cho phép. Không dùng master DB user cho app.
4. EKS Core → Access → Pod Identity associations → Create: namespace `fabric-apps`, ServiceAccount `order-service`, `inventory-service`, `payment-worker` → role tương ứng. Manifest app phải tạo các ServiceAccount cùng tên và SDK hỗ trợ Pod Identity.
5. Từ admin pod/job chạy trong Core có quyền mạng DB, kết nối endpoint Aurora trực tiếp với TLS `verify-full` và RDS CA bundle; tạo database/schema, user app có quyền tối thiểu, migration có phiên bản. Không mở SG DB cho máy quản trị Internet. Dừng nếu repo app chưa có migration/command; không tự đặt schema.
6. Secrets Manager → Store a new secret → lưu DB user app và cache credential theo schema cấu hình app; chọn KMS key và tag dự án. App đọc secret bằng AWS SDK lúc khởi động, không in giá trị. Phương án này cần endpoint `secretsmanager` trong Core: VPC → Endpoints → Create → AWS services → `com.amazonaws.ap-southeast-1.secretsmanager` → Core VPC → hai VPCE subnet → bật Private DNS → SG 443 từ Core → Create.
7. Config không nhạy cảm gồm DB endpoint/port, Redis endpoint, Queue URL và Region đưa vào ConfigMap; secret ARN đưa vào cấu hình riêng. App phải reconnect/retry có backoff và reload credential khi rotation; kiểm thử trước khi bật tự động rotation cho user app.

> Master secret do RDS quản lý chỉ phục vụ bootstrap quản trị. Phần IAM đầu bài là danh sách thao tác cho người triển khai, không phải policy gán nguyên khối cho workload. Aurora writer + reader và Redis primary + replica đều có phí; giá minh họa đầu bài không phải tổng chi phí HA. Xem Pricing Calculator Singapore trước Create.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái cluster Aurora và Secrets Manager qua CLI:
```bash
# 1. Kiểm tra trạng thái Aurora Cluster và Writer Endpoint
aws rds describe-db-clusters --region ap-southeast-1 \
  --db-cluster-identifier fabric-core-db \
  --query 'DBClusters[0].{Id:DBClusterIdentifier,Status:Status,Endpoint:Endpoint,ServerlessV2Min:ServerlessV2ScalingConfiguration.MinCapacity}' \
  --output table

# 2. Kiểm tra mật khẩu tự động được tạo trong Secrets Manager
aws secretsmanager list-secrets --region ap-southeast-1 \
  --filters Key=name,Values=rds-db-credentials \
  --query 'SecretList[*].{Name:Name,ARN:ARN}' \
  --output table

# 3. Endpoint và các cờ bảo mật Redis replication group
aws elasticache describe-replication-groups --region ap-southeast-1 \
  --replication-group-id fabric-core-redis \
  --query 'ReplicationGroups[0].{Id:ReplicationGroupId,Status:Status,Endpoint:NodeGroups[0].PrimaryEndpoint,Transit:TransitEncryptionEnabled,AtRest:AtRestEncryptionEnabled,Failover:AutomaticFailover}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Xóa cụm Aurora PostgreSQL và ElastiCache khi hoàn tất bài lab:
```bash
# Chỉ sau khi đã cho phép mất dữ liệu lab: xóa từng reader/writer instance trước,
# chờ instance biến mất rồi mới xóa cluster. Production phải có snapshot/backup.
# Xóa Aurora DB Cluster (Bỏ qua Final Snapshot chỉ cho dữ liệu lab bỏ được)
aws rds delete-db-cluster --region ap-southeast-1 \
  --db-cluster-identifier fabric-core-db \
  --skip-final-snapshot

# Xóa replication group provisioned, không xóa riêng member của group.
# Quyết định final snapshot trước khi chạy; dữ liệu lab bỏ được mới bỏ snapshot.
aws elasticache delete-replication-group --region ap-southeast-1 \
  --replication-group-id fabric-core-redis
```

Nếu cần giữ Redis backup, thêm `--final-snapshot-identifier <tên-snapshot-duy-nhất>`. Nếu lỗi giữa chừng: dừng writers, ghi resource IDs đã tạo, chỉ xóa tài nguyên của lần chạy sau khi quyết định giữ dữ liệu. IAM → Pod Identity associations/policies, Secrets Manager, SQS queue/DLQ và subnet/SG groups phải đối chiếu ownership, xử lý theo 12.01; không xóa role/secret dùng chung.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/04-workloads/01-database-and-cache.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] DB Subnet Group và Cache Subnet Group nằm trọn vẹn trong 2 Data Subnets `fabric-core-data-1a/b`.
- [ ] Security Group `fabric-core-data-sg` chỉ mở cổng 5432 và 6379 cho Core Node Subnets (`10.50.8.0/22`, `10.50.12.0/22`).
- [ ] Aurora PostgreSQL Serverless v2 ở trạng thái `available` với dải capacity 0.5 - 1.0 ACU.
- [ ] Tính năng Public Access bị tắt (`No`) trên toàn bộ tầng dữ liệu.
