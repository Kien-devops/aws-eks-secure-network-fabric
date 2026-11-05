# 04.01 — Khởi Tạo Aurora PostgreSQL Serverless v2 & ElastiCache Redis

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Thiết lập lớp lưu trữ dữ liệu nghiệp vụ và bộ đệm tốc độ cao tại Private Data Subnets trong Core VPC.

---

## 1. Mục Tiêu Kỹ Thuật

- Khởi tạo **Amazon Aurora PostgreSQL Serverless v2** trong `fabric-core-vpc`:
  - Đặt trọn vẹn trong các Subnet riêng tư `fabric-core-data-1a` (`10.50.20.0/24`) và `fabric-core-data-1b` (`10.50.21.0/24`).
  - Cấu hình Security Group chỉ cho phép kết nối cổng TCP `5432` từ Core EKS Node Security Group.
- Khởi tạo cụm **ElastiCache Redis** (Cluster Mode Disabled, 1 Primary + 1 Replica) trong cùng Subnet Data.
- Khởi tạo hàng đợi **AWS SQS** `fabric-order-events.fifo` và hàng đợi lỗi Dead-Letter Queue (DLQ).

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Tạo DB Subnet Group & Security Group
1. Mở dịch vụ **RDS Console** tại Singapore (`ap-southeast-1`).
2. Chọn **Subnet groups** -> Nhấp **Create DB subnet group**:
   - **Name:** `fabric-core-db-subnet-group`
   - **VPC:** Chọn `fabric-core-vpc`
   - **Subnets:** Chọn `fabric-core-data-1a` và `fabric-core-data-1b`.
   - Nhấp **Create**.
3. Mở dịch vụ **EC2 Console** -> Tạo Security Group:
   - **Name:** `fabric-core-db-sg`
   - **VPC:** Chọn `fabric-core-vpc`
   - **Inbound Rules:** Cho phép Type `PostgreSQL` (Cổng 5432) từ Source là Security Group của Core EKS Worker Nodes (`fabric-core-node-sg`).

---

### Bước 2: Khởi Tạo Aurora PostgreSQL Serverless v2
1. Tại dịch vụ **RDS**, chọn **Databases** -> Nhấp nút cam **Create database**.
2. **Choose a database creation method:** Chọn `Standard create`.
3. **Engine options:** Chọn `Aurora (PostgreSQL Compatible)`.
4. **Engine Version:** Chọn bản ổn định (PostgreSQL 15+).
5. **Templates:** Chọn `Production` hoặc `Dev/Test`.
6. **Settings:**
   - **DB cluster identifier:** `fabric-core-aurora-db`
   - **Master username:** `postgres`
   - **Master password:** Thiết lập mật khẩu an toàn (lưu ý sẽ che giấu khi lưu evidence).
7. **Cluster storage configuration:** Chọn `Aurora Standard`.
8. **Instance configuration:**
   - Chọn `Serverless v2`.
   - Đặt phạm vi dung lượng (Capacity range): Min `0.5 ACU` - Max `2.0 ACU` (Tối ưu chi phí).
9. **Connectivity:**
   - **Virtual private cloud (VPC):** `fabric-core-vpc`.
   - **DB subnet group:** `fabric-core-db-subnet-group`.
   - **Public access:** `No` (Tuyệt đối không mở public).
   - **VPC security group:** Chọn `fabric-core-db-sg`.
10. Nhấp nút cam **Create database**.

---

### Bước 3: Khởi Tạo ElastiCache Redis
1. Mở dịch vụ **Amazon ElastiCache** tại `ap-southeast-1`.
2. Tạo Subnet Group: Chọn `fabric-core-vpc`, gán 2 Subnet Data `1a` và `1b`.
3. Tạo Redis Cluster:
   - **Cluster name:** `fabric-core-redis`
   - **Node type:** `cache.t4g.micro` (đủ cho thử nghiệm mạng và tiết kiệm chi phí).
   - **Number of replicas:** `1` (Đặt tại AZ khác với Primary để có tính dự phòng cao).
   - **Security Group:** Cho phép cổng `6379` từ Core Node SG.
   - Nhấp **Create**.

---

### Bước 4: Tạo AWS SQS Queue & DLQ
1. Mở dịch vụ **Amazon SQS** tại `ap-southeast-1`.
2. Tạo DLQ: Name `fabric-order-events-dlq.fifo` (FIFO queue).
3. Tạo Queue chính: Name `fabric-order-events.fifo` (FIFO queue) -> Bật Dead-letter queue trỏ tới DLQ vừa tạo với MaxReceiveCount = `3`.

---

## 3. Xác Minh (Verification)

Kiểm tra trạng thái Database qua AWS CLI:
```bash
aws rds describe-db-clusters \
  --db-cluster-identifier fabric-core-aurora-db \
  --region ap-southeast-1 \
  --query 'DBClusters[0].{Id:DBClusterIdentifier,Status:Status,Engine:Engine,Endpoint:Endpoint}' \
  --output table
```
> Kết quả: `Status = available`.

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Aurora PostgreSQL Serverless v2 ở trạng thái `available` với endpoint nằm trong dải `10.50.20.0/24`.
- [ ] ElastiCache Redis và SQS FIFO Queue sẵn sàng nhận kết nối từ Core EKS Pods.

