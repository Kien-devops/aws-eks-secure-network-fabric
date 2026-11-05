# Module 04: Phân Bổ Workloads & Dịch Vụ Nội Bộ (app3 Microservices)

Module này hướng dẫn triển khai hệ thống 5 microservices (`frontend`, `auth-service`, `order-service`, `inventory-service`, `payment-worker`), cơ sở dữ liệu Amazon Aurora Serverless v2, ElastiCache Redis, phân giải DNS Route 53 Private Hosted Zone và Core Internal NLB tự động quản lý IP targets qua AWS Load Balancer Controller.

## Danh Sách Bài Lab

| Mã Lab | Tên Bài Lab & Nội Dung Trọng Tâm | Trạng Thái | File Hướng Dẫn |
|---|---|:---:|---|
| **04.01** | **Aurora PostgreSQL & ElastiCache Redis:** Data layer cô lập tại Core VPC. | `DRAFT` | [01-database-and-cache-setup.md](01-database-and-cache-setup.md) |
| **04.02** | **Route 53 Private Hosted Zone:** Phân giải `fabric.internal` nội bộ liên VPC. | `DRAFT` | [02-route53-private-hosted-zone.md](02-route53-private-hosted-zone.md) |
| **04.03** | **Core Internal NLB (IP-targets):** AWS Load Balancer Controller tự động quản lý Pod IP. | `DRAFT` | [03-core-internal-nlb.md](03-core-internal-nlb.md) |
| **04.04** | **Triển Khai Microservices & GitOps:** Đồng bộ 5 services tuân thủ chuẩn phân vùng. | `DRAFT` | [04-microservices-gitops-deploy.md](04-microservices-gitops-deploy.md) |
