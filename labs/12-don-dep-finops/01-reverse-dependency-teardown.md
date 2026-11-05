# 12.01 — Quy Trình Hủy Tài Nguyên Theo Thứ Tự Phụ Thuộc Ngược (Reverse Teardown)

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console và AWS CLI.  
> **Áp dụng cho:** Hủy sạch toàn bộ tài nguyên đám mây sau khi kết thúc dự án mà không bị vướng lỗi phụ thuộc tài nguyên.

---

## 1. Mục Tiêu Kỹ Thuật

- Thực hiện xóa bỏ tài nguyên theo quy trình 6 tầng nghiêm ngặt nhằm tránh lỗi `DependencyViolation` hoặc kẹt ENI.
- Hủy bỏ các tài nguyên tính phí theo giờ đắt nhất trước tiên (EKS, Network Firewall, NAT Gateway, GWLB, EC2).

---

## 2. Thứ Tự Triển Khai 6 Tầng Chi Tiết

```text
[Tầng 1: L7 & Ingress]       --> Xóa ALB Ingress, ACM Certificate, Web ACL WAF
         |
         v
[Tầng 2: Workloads & EKS]     --> Xóa EKS Node Groups, EKS Clusters
         |
         v
[Tầng 3: Database & Cache]    --> Xóa Aurora Serverless v2, ElastiCache Redis, SQS
         |
         v
[Tầng 4: Firewalls & GWLB]    --> Xóa AWS Network Firewall, GWLBe, GWLB, Suricata EC2
         |
         v
[Tầng 5: Transit Gateway]     --> Xóa TGW Route Tables, TGW VPC Attachments, TGW
         |
         v
[Tầng 6: Network Base & IPs]  --> Nhả Elastic IPs, xóa NAT GW, IGW, Subnets, VPCs
```

---

## 3. Các Bước Thực Hiện Chi Tiết

### Bước 1: Xóa Lớp Ingress & Cụm EKS (Tầng 1 & 2)
1. Xóa Ingress trong cụm Kubernetes để AWS Load Balancer Controller tự hủy ALB:
   ```bash
   kubectl delete ingress fabric-edge-ingress
   ```
2. Xóa Node Groups:
   ```bash
   aws eks delete-nodegroup --cluster-name fabric-edge-eks --nodegroup-name fabric-edge-ng --region ap-southeast-1
   aws eks delete-nodegroup --cluster-name fabric-core-eks --nodegroup-name fabric-core-ng --region ap-southeast-1
   ```
3. Sau khi Node Groups đã xóa xong -> Xóa 2 EKS Clusters:
   ```bash
   aws eks delete-cluster --name fabric-edge-eks --region ap-southeast-1
   aws eks delete-cluster --name fabric-core-eks --region ap-southeast-1
   ```

---

### Bước 2: Xóa Cơ Sở Dữ Liệu & Hàng Đợi (Tầng 3)
1. Xóa Aurora DB Cluster (Bỏ qua Final Snapshot để xóa nhanh):
   ```bash
   aws rds delete-db-cluster --db-cluster-identifier fabric-core-aurora-db --skip-final-snapshot --region ap-southeast-1
   ```
2. Xóa Redis:
   ```bash
   aws elasticache delete-cache-cluster --cache-cluster-id fabric-core-redis --region ap-southeast-1
   ```
3. Xóa SQS Queue:
   ```bash
   aws sqs delete-queue --queue-url $(aws sqs get-queue-url --queue-name fabric-order-events.fifo --query 'QueueUrl' --output text --region ap-southeast-1) --region ap-southeast-1
   ```

---

### Bước 3: Xóa AWS Network Firewall & Cụm Suricata GWLB (Tầng 4)
1. Xóa Network Firewall:
   ```bash
   aws network-firewall delete-firewall --firewall-name fabric-egress-nfw --region ap-southeast-1
   ```
2. Xóa GWLB Endpoints & Endpoint Service:
   ```bash
   aws ec2 delete-vpc-endpoints --vpc-endpoint-ids <gwlbe-a-id> <gwlbe-b-id> --region ap-southeast-1
   aws ec2 delete-vpc-endpoint-service-configurations --service-ids <service-id> --region ap-southeast-1
   ```
3. Xóa GWLB & Terminate Suricata EC2:
   ```bash
   aws elbv2 delete-load-balancer --load-balancer-arn <gwlb-arn> --region ap-southeast-1
   aws ec2 terminate-instances --instance-ids <suricata-az-a-id> <suricata-az-b-id> --region ap-southeast-1
   ```

---

### Bước 4: Xóa Transit Gateway & 4 VPCs (Tầng 5 & 6)
1. Xóa 4 TGW VPC Attachments:
   ```bash
   aws ec2 delete-transit-gateway-vpc-attachment --transit-gateway-attachment-id <att-id> --region ap-southeast-1
   ```
2. Xóa Transit Gateway:
   ```bash
   aws ec2 delete-transit-gateway --transit-gateway-id <tgw-id> --region ap-southeast-1
   ```
3. Xóa 2 NAT Gateways và nhả 2 Elastic IPs:
   ```bash
   aws ec2 delete-nat-gateway --nat-gateway-id <nat-1a-id> --region ap-southeast-1
   aws ec2 delete-nat-gateway --nat-gateway-id <nat-1b-id> --region ap-southeast-1
   ```
   *(Chờ NAT Gateways chuyển sang trạng thái deleted rồi tiến hành giải phóng Elastic IPs)*.
4. Xóa Internet Gateway và xóa toàn bộ 4 VPCs: `fabric-edge-vpc`, `fabric-core-vpc`, `fabric-inspection-vpc`, `fabric-egress-vpc`.

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Tất cả tài nguyên thuộc 6 tầng được xóa sạch theo đúng thứ tự phụ thuộc ngược.
- [ ] Không có lệnh xóa nào bị treo hoặc báo lỗi phụ thuộc ENI.

