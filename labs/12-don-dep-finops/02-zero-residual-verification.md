# 12.02 — Kiểm Kê Tồn Dư Và Đối Soát Chi Phí Sau Cleanup

> **Mã bài lab:** `12.02`
> **Trạng thái:** `READY_TO_RUN`
> **Thời gian dự kiến:** 45 phút
> **Chi phí ước tính:** $0.00 USD (Read-Only API Calls)
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)

---

## 1. Mục Tiêu (Objective)

Đặc tả quy trình kiểm kê tồn dư và đối soát chi phí sau khi thực hiện Teardown toàn diện hạ tầng AWS. Đảm bảo 100% tài nguyên tính phí theo giờ thuộc dự án (EKS, NAT, NFW, TGW, RDS, GWLB) đã được thu hồi triệt để, phát hiện các tài nguyên snapshot/log còn giữ và xác thực báo cáo chi phí hướng tới $0.00 USD/ngày.

---

## 2. Tài Nguyên (Resources)

| Nhóm Tài Nguyên Kiểm Kê | Dịch Vụ AWS | Lệnh / API Đối Soát | Kết Quả Mong Đợi |
| :--- | :--- | :--- | :--- |
| **Compute & Clusters** | Amazon EKS & EC2 | `eks:ListClusters`, `ec2:DescribeInstances` | 0 cụm `fabric-`, 0 EC2 running |
| **Load Balancing & Ingress** | Elastic Load Balancing | `elbv2:DescribeLoadBalancers` | 0 Load Balancers `fabric-` |
| **Network & Transit** | VPC, NAT, TGW, NFW | `ec2:DescribeVpcs`, `network-firewall:ListFirewalls` | 0 VPCs dự án, 0 NFW, 0 NAT active |
| **Data & Storage** | Aurora RDS, ElastiCache, SQS | `rds:DescribeDBClusters`, `elasticache:DescribeReplicationGroups` | 0 DB clusters, 0 Redis groups |
| **Logs, Storage & ECR** | CloudWatch, S3, ECR | `logs:DescribeLogGroups`, `ecr:DescribeRepositories` | Log retention 7 days, image repos archived |
| **IAM, KMS & Secrets** | IAM, KMS, Secrets Manager | `kms:ListKeys`, `secretsmanager:ListSecrets` | Keys scheduled deletion, 0 active secrets |

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-*` | Bộ lọc đối soát tồn dư tài nguyên |
| `Project` | `aws-eks-secure-network-fabric` | Bộ lọc đối soát tồn dư tài nguyên |
| `Environment` | `prod` | Phân vùng môi trường kiểm kê |
| `ManagedBy` | `manual` | Quản lý quy trình kiểm toán thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Bảng Kiểm Kê Tồn Dư Toàn Diện (Zero Residual Audit Matrix)

| Nhóm Dịch Vụ | Tài Nguyên Cần Rà Soát | Phương Pháp Kiểm Tra | Tiêu Chí Đạt (Pass Criteria) |
| :--- | :--- | :--- | :--- |
| **EKS & Compute** | `fabric-edge-eks`, `fabric-core-eks`, Worker Nodes | AWS CLI `eks list-clusters`, `ec2 describe-instances` | Không còn cluster `fabric-` hoặc node running |
| **VPC & Routing** | 4 VPCs, 16 Subnets, TGW Attachments | AWS CLI `ec2 describe-vpcs --filters Name=tag:Project...` | 0 VPC IDs thuộc dự án |
| **Firewall & NAT** | `fabric-egress-nfw`, NAT Gateways 1a/1b | AWS CLI `network-firewall list-firewalls`, `describe-nat-gateways` | Trạng thái `deleted` hoặc rỗng |
| **Data & Messaging** | `fabric-core-db`, Redis, SQS (`edge-frontend`, `core-service`) | AWS CLI `rds describe-db-clusters`, `elasticache describe-replication-groups` | Không còn database instance tính phí |
| **Network Interfaces** | ENIs gắn với ALB, NLB, EKS, NAT, NFW | AWS CLI `ec2 describe-network-interfaces` | Không còn ENI kẹt (Available/In-use) của dự án |
| **Billing & Usage** | AWS Cost Explorer Daily Unblended Cost | AWS CLI `ce get-cost-and-usage` | Chi phí phát sinh ngày $T+1$ tiệm cận $0.00 USD |

### 4.2 Lệnh Rà Soát Nhanh Qua AWS CLI (Read-Only)
```bash
# 1. Kiểm tra VPC
aws ec2 describe-vpcs --region ap-southeast-1 \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query 'Vpcs[*].VpcId' --output text

# 2. Kiểm tra EKS Clusters
aws eks list-clusters --region ap-southeast-1 \
  --query 'clusters[?contains(@, `fabric`)]' --output text

# 3. Kiểm tra Load Balancers
aws elbv2 describe-load-balancers --region ap-southeast-1 \
  --query 'LoadBalancers[?contains(LoadBalancerName, `fabric`)].LoadBalancerName' --output text

# 4. Kiểm tra Network Interfaces (ENI)
aws ec2 describe-network-interfaces --region ap-southeast-1 \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query 'NetworkInterfaces[*].NetworkInterfaceId' --output text
```

---

## 5. Phụ Thuộc (Dependencies)

* [Lab 12.01](01-reverse-dependency-teardown.md): Đã hoàn tất quy trình xóa tài nguyên 6 tầng.
* Tài khoản IAM có quyền Read-Only trên toàn bộ các dịch vụ EC2, EKS, RDS, ElastiCache, Network Firewall, WAF, SQS, Cost Explorer.

---

## 6. Kiểm Tra Đạt (Verification)

| Hạng Mục | Lệnh Kiểm Tra / Metric | Kỳ Vọng Đạt |
| :--- | :--- | :--- |
| **Compute / Network Sạch** | Chạy các lệnh kiểm tra AWS CLI | Không phát hiện tài nguyên tồn dư của dự án |
| **Không Còn ENI Kẹt** | `describe-network-interfaces` | Trả về danh sách rỗng cho tag `Project` |
| **Báo Cáo Nghiệm Thu** | Tạo tệp `ZERO-RESIDUAL-CERTIFICATE.md` | Đầy đủ bảng đối soát 6 nhóm dịch vụ và chữ ký SRE |
| **Hóa Đơn Sau Teardown** | Đối soát AWS Cost Explorer sau 24h | Chi phí ngày tiếp theo chỉ gồm lưu trữ retained (nếu có), chi phí compute = $0.00 |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

> [!NOTE]
> Bài kiểm kê là hoạt động Read-Only hoàn toàn an toàn. Nếu phát hiện tài nguyên tồn dư (ví dụ ENI kẹt hoặc snapshot sót), quay lại [Lab 12.01](01-reverse-dependency-teardown.md) để thực hiện xử lý cục bộ.

### Báo Cáo Chứng Nhận Tồn Dư
Kết quả kiểm kê được lưu trữ tại `evidence/05-reports/ZERO-RESIDUAL-CERTIFICATE.md` làm căn cứ nghiệm thu bàn giao hạ tầng.
