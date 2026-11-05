# Module 12: Dọn Dẹp Hạ Tầng Triệt Để & Tối Ưu Chi Phí (Reverse Teardown - $0.00)

## 1. Mục Tiêu Kỹ Thuật
- **Mục tiêu:**
  - Thực hiện quy trình hủy toàn bộ tài nguyên đám mây theo **Thứ tự phụ thuộc ngược (Reverse Cleanup Dependency Order)**.
  - Ngăn ngừa tình trạng lỗi không xóa được tài nguyên do vướng phụ thuộc mạng (ví dụ: ENI của ALB, NAT Gateway, GWLB, Network Firewall hoặc EKS Nodes vẫn còn bám vào VPC).
  - Sử dụng công cụ kiểm kê tự động qua AWS MCP (`aws-api-mcp/call_aws`) để xác nhận không còn tài nguyên nào tính phí ngầm đang chạy, đưa hóa đơn phát sinh về **$0.00 USD**.

---

## 2. Thứ Tự Phụ Thuộc Ngược (Reverse Dependency Order)

Quy trình dọn dẹp bắt buộc phải tuân theo 6 tầng thứ tự:

```text
[Tầng 1: L7 & Ingress]       --> Xóa AWS WAF Association, ALB, ACM Certificate, Route 53 Records
         |
         v
[Tầng 2: Workloads & K8s]     --> Xóa Argo CD apps, Pods, Services (NLB/ALB), EKS Node Groups, EKS Clusters
         |
         v
[Tầng 3: Data & Storage]      --> Xóa Aurora PostgreSQL Serverless v2, ElastiCache Redis, SQS Queues
         |
         v
[Tầng 4: Firewalls & GWLB]    --> Xóa AWS Network Firewall, GWLB Endpoints (GWLBe), GWLB, Suricata EC2 instances
         |
         v
[Tầng 5: Transit Gateway]     --> Xóa TGW Route Tables, TGW VPC Attachments, Transit Gateway
         |
         v
[Tầng 6: Network Base & IAM]  --> Hủy Elastic IPs, NAT Gateways, Internet Gateways, Subnets, VPCs, KMS Keys/IAM Roles
```

---

## 3. Các Lệnh Thực Thi Dọn Dẹp & Kiểm Tra Tồn Dư

### Bước 1: Dọn dẹp Cụm EKS và Workloads
```bash
aws eks delete-nodegroup --cluster-name fabric-edge-eks --nodegroup-name <ng-name> --region ap-southeast-1
aws eks delete-nodegroup --cluster-name fabric-core-eks --nodegroup-name <ng-name> --region ap-southeast-1
aws eks delete-cluster --name fabric-edge-eks --region ap-southeast-1
aws eks delete-cluster --name fabric-core-eks --region ap-southeast-1
```

### Bước 2: Dọn dẹp Cụm Tường Lửa & GWLB
```bash
# Xóa AWS Network Firewall
aws network-firewall delete-firewall --firewall-name fabric-egress-nfw --region ap-southeast-1
# Xóa GWLB & Target Group
aws elbv2 delete-load-balancer --load-balancer-arn <gwlb-arn> --region ap-southeast-1
# Terminate máy chủ Suricata
aws ec2 terminate-instances --instance-ids <suricata-instance-ids> --region ap-southeast-1
```

### Bước 3: Dọn dẹp Transit Gateway & VPCs
1. Xóa các VPC Attachments:
   ```bash
   aws ec2 delete-transit-gateway-vpc-attachment --transit-gateway-attachment-id <attachment-id> --region ap-southeast-1
   ```
2. Xóa Transit Gateway:
   ```bash
   aws ec2 delete-transit-gateway --transit-gateway-id <tgw-id> --region ap-southeast-1
   ```
3. Xóa NAT Gateways, nhả Elastic IPs, và xóa 4 VPCs.

---

## 4. Xác Minh Tồn Dư Tự Động (Zero Residual Check)
Chạy script kiểm kê tự động qua AWS MCP để đảm bảo tài khoản đã sạch 100%:
```bash
# Kiểm tra VPCs còn tồn tại
aws ec2 describe-vpcs --region ap-southeast-1 --query 'Vpcs[*].{Id:VpcId,Name:Tags[?Key==`Name`].Value | [0]}' --output table

# Kiểm tra Load Balancers
aws elbv2 describe-load-balancers --region ap-southeast-1 --query 'LoadBalancers[*].LoadBalancerName' --output table

# Kiểm tra NAT Gateways
aws ec2 describe-nat-gateways --region ap-southeast-1 --query 'NatGateways[?State!=`deleted`].NatGatewayId' --output table

# Kiểm tra EKS Clusters
aws eks list-clusters --region ap-southeast-1 --output table
```
> Kết quả mong đợi: Toàn bộ danh sách rỗng (Empty list).

---

## 5. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Không còn bất kỳ tài nguyên mạng, máy chủ ảo, cụm EKS hay tường lửa nào tồn tại trên `ap-southeast-1`.
- [ ] Tất cả Elastic IPs đã được giải phóng (Released) tránh phát sinh phí nhàn rỗi.
- [ ] Báo cáo kiểm kê cuối cùng xác nhận chi phí tồn dư duy trì ở mức **$0.00**.
