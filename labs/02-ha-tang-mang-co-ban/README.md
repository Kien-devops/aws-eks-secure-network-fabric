# Module 02: Hạ Tầng Mạng Cơ Bản (Foundation Network & Transit Gateway)

Module này hướng dẫn khởi tạo nền tảng hạ tầng mạng đa VPC trên AWS Region Singapore (`ap-southeast-1`), kết nối thông qua AWS Transit Gateway theo mô hình phân tách miền định tuyến (Route Domain Segmentation).

## Danh Sách Bài Lab

| Mã Lab | Tên Bài Lab & Nội Dung Trọng Tâm | Trạng Thái | File Hướng Dẫn |
|---|---|:---:|---|
| **02.01** | **Khởi Tạo 4 VPCs & Subnets Đa AZ:** 4 VPCs độc lập, 26 subnets chuẩn hóa theo AZ A/B. | `DRAFT` | [01-four-vpcs-and-subnets.md](01-four-vpcs-and-subnets.md) |
| **02.02** | **Cấu Hình AWS Transit Gateway (TGW):** ASN 64512, tắt mặc định Route Propagation. | `DRAFT` | [02-transit-gateway-setup.md](02-transit-gateway-setup.md) |
| **02.03** | **TGW Attachments & Appliance Mode:** 4 attachments, bật Appliance Mode trên Inspection & Egress. | `DRAFT` | [03-tgw-route-tables-and-attachments.md](03-tgw-route-tables-and-attachments.md) |
| **02.04** | **Bảng Định Tuyến Subnet:** Chaining các tuyến đường từ VPC private qua TGW. | `DRAFT` | [04-subnet-route-tables-chaining.md](04-subnet-route-tables-chaining.md) |
| **02.05** | **Centralized VPC Flow Logs:** Tập trung hóa nhật ký gói tin về CloudWatch Logs 7 ngày. | `DRAFT` | [05-vpc-flow-logs-cloudwatch.md](05-vpc-flow-logs-cloudwatch.md) |
| **02.06** | **Private VPC Endpoints:** S3 Gateway, ECR, STS, Logs, EC2 endpoints cho Private EKS. | `DRAFT` | [06-private-vpc-endpoints.md](06-private-vpc-endpoints.md) |
