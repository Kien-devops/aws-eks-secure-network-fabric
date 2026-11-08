# Module 04: Phân Bổ Workloads & Dịch Vụ Nội Bộ (Dual-Tier Microservices)

Module này cung cấp các đặc tả tài nguyên triển khai 2 microservices (`edge-frontend` và `core-service`), cơ sở dữ liệu Amazon Aurora Serverless v2, ElastiCache Redis, phân giải DNS Route 53 Private Hosted Zone và Core Internal NLB tự động quản lý IP targets qua AWS Load Balancer Controller.

---

## 1. Thứ Tự Phụ Thuộc (Dependency Tree)

```text
04.01 (Aurora PostgreSQL Serverless v2, ElastiCache Redis, SQS Queue)
  │
  ├──> 04.02 (Route 53 Private Hosted Zone: fabric.internal)
  │      │
  │      └──> 04.03 (Core Internal NLB: IP-targets qua AWS LB Controller)
  │             │
  └─────────────┴──> 04.04 (Triển khai Microservices GitOps: Argo CD)
```

---

## 2. Danh Mục Tài Nguyên (Resource Catalog)

| Tài Nguyên | Loại Resource | Số Lượng | Ghi Chú Kỹ Thuật |
| :--- | :--- | :---: | :--- |
| **Aurora PostgreSQL** | `AWS::RDS::DBCluster` | 1 | `fabric-core-db` (Serverless v2 0.5 - 1.0 ACU, Multi-AZ) |
| **ElastiCache Redis** | `AWS::ElastiCache::ReplicationGroup` | 1 | `fabric-core-redis` (1 Primary, 1 Replica, Multi-AZ) |
| **SQS Queues** | `AWS::SQS::Queue` | 2 | `fabric-order-events` (Main) và `fabric-order-events-dlq` (DLQ) |
| **Route 53 PHZ** | `AWS::Route53::HostedZone` | 1 | `fabric.internal` (Liên kết cả Edge VPC và Core VPC) |
| **DNS Records** | `AWS::Route53::RecordSet` | 5 | CNAME: `db`, `dbr`, `redis`, `redis-ro`, `core` |
| **Internal NLB** | `AWS::ElasticLoadBalancingV2::LoadBalancer` | 1 | `fabric-core-internal-nlb` (Scheme internal, TCP 443 -> 8082) |
| **Argo CD Apps** | `argoproj.io/v1alpha1::Application` | 2 | `fabric-edge-apps` và `fabric-core-apps` |
| **Microservices** | `k8s::Deployment` | 2 | `edge-frontend` (Edge EKS) và `core-service` (Core EKS) |

---

## 3. Danh Sách 4 Bài Lab Đặc Tả Chi Tiết

| Mã Lab | Tên Đặc Tả & Nội Dung Trọng Tâm | Trạng Thái | File Đặc Tả |
|---|---|:---:|---|
| **04.01** | **Aurora PostgreSQL & ElastiCache Redis:** Data layer cô lập tại Core Data Subnets. | `READY_TO_RUN` | [01-database-and-cache-setup.md](01-database-and-cache-setup.md) |
| **04.02** | **Route 53 Private Hosted Zone:** Phân giải `fabric.internal` nội bộ liên VPC. | `RUNTIME_PASS` | [02-route53-private-hosted-zone.md](02-route53-private-hosted-zone.md) |
| **04.03** | **Core Internal NLB (IP-targets):** AWS Load Balancer Controller tự động quản lý Pod IP. | `READY_TO_RUN` | [03-core-internal-nlb.md](03-core-internal-nlb.md) |
| **04.04** | **Triển Khai Microservices & GitOps:** Đồng bộ 2 microservices tuân thủ chuẩn phân vùng qua Argo CD. | `RUNTIME_PASS` | [04-microservices-gitops-deploy.md](04-microservices-gitops-deploy.md) |
