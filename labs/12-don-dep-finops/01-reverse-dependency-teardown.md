# 12.01 — Quy Trình Hủy Tài Nguyên Theo Thứ Tự Phụ Thuộc Ngược (Reverse Teardown)

> **Mã bài lab:** `12.01`
> **Trạng thái:** `READY_TO_RUN`
> **Thời gian dự kiến:** 60 phút
> **Chi phí ước tính:** $0.00 USD (Xóa tài nguyên giải phóng chi phí)
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)

---

## 1. Mục Tiêu (Objective)

Đặc tả quy trình thu hồi và xóa sạch toàn bộ tài nguyên hạ tầng AWS theo thứ tự phụ thuộc ngược 6 tầng (Reverse 6-Tier Teardown). Ngăn ngừa triệt để lỗi `DependencyViolation` và kẹt Elastic Network Interface (ENI), đảm bảo chi phí vận hành sau khi kết thúc dự án được đưa về mức $0.00 USD/ngày.

---

## 2. Tài Nguyên (Resources)

| Tầng Dọn Dẹp | Danh Mục Tài Nguyên Cần Hủy | Loại Resource | Phương Thức Xóa |
| :--- | :--- | :--- | :--- |
| **Tầng 1: L7 Ingress** | ALB Ingress, ACM Public Cert, WAFv2 Web ACL | `elasticloadbalancing`, `acm`, `wafv2` | Kubernetes ingress delete & AWS CLI |
| **Tầng 2: Workloads & EKS** | Managed Node Groups, EKS Control Planes | `eks:Nodegroup`, `eks:Cluster` | `aws eks delete-nodegroup`, `delete-cluster` |
| **Tầng 3: Data & Messaging** | Aurora Serverless v2, ElastiCache Redis, SQS | `rds:DBCluster`, `elasticache`, `sqs` | `aws rds delete-db-cluster`, `delete-queue` |
| **Tầng 4: Firewalls & GWLB** | AWS Network Firewall, GWLBe, GWLB, Suricata EC2 | `network-firewall`, `ec2:VpcEndpoint`, `ec2:Instance` | Delete Firewall, VPC Endpoints & Terminate EC2 |
| **Tầng 5: Transit Gateway** | TGW Route Tables, TGW VPC Attachments, TGW Core | `ec2:TransitGateway*` | Delete TGW Attachments, Route Tables & TGW |
| **Tầng 6: Network Base** | NAT Gateways, Elastic IPs, IGWs, Subnets, 4 VPCs | `ec2:NatGateway`, `ec2:EIP`, `ec2:Vpc` | Delete NAT GW, Release EIPs, Delete VPCs |

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-*` | Bộ lọc bắt buộc để nhận diện tài nguyên cần xóa |
| `Project` | `aws-eks-secure-network-fabric` | Bộ lọc bắt buộc để nhận diện tài nguyên cần xóa |
| `Environment` | `prod` | Phân vùng môi trường dọn dẹp |
| `ManagedBy` | `manual` | Quản lý quy trình teardown thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Sơ Đồ Trình Tự Hủy Phụ Thuộc Ngược 6 Tầng
```text
[Tầng 1: L7 & Ingress]       --> Xóa ALB Ingress, ACM Certificate, Web ACL WAF
          │
          ▼
[Tầng 2: Workloads & EKS]     --> Xóa EKS Node Groups, EKS Clusters (Tránh kẹt ENI)
          │
          ▼
[Tầng 3: Database & Cache]    --> Xóa Aurora Serverless v2, ElastiCache Redis, SQS
          │
          ▼
[Tầng 4: Firewalls & GWLB]    --> Xóa AWS Network Firewall, GWLBe, GWLB, Suricata EC2
          │
          ▼
[Tầng 5: Transit Gateway]     --> Xóa TGW Route Tables, TGW VPC Attachments, TGW
          │
          ▼
[Tầng 6: Network Base & IPs]  --> Nhả Elastic IPs, xóa NAT GW, IGW, Subnets, 4 VPCs
```

### 4.2 Lệnh Thực Thi Teardown Từng Tầng (CLI Execution)
1. **Tầng 1 — L7 Ingress & WAF:**
   ```bash
   kubectl delete ingress fabric-edge-ingress -n fabric-apps --context fabric-edge
   aws wafv2 delete-web-acl --region ap-southeast-1 --name fabric-edge-web-acl --scope REGIONAL --id <WEB_ACL_ID> --lock-token <TOKEN>
   ```
2. **Tầng 2 — EKS Node Groups & Clusters:**
   ```bash
   aws eks delete-nodegroup --region ap-southeast-1 --cluster-name fabric-edge-eks --nodegroup-name fabric-edge-ng-1
   aws eks delete-nodegroup --region ap-southeast-1 --cluster-name fabric-core-eks --nodegroup-name fabric-core-ng-1
   # Chờ Node Groups xóa xong (3-5 phút) rồi xóa Control Planes:
   aws eks delete-cluster --region ap-southeast-1 --name fabric-edge-eks
   aws eks delete-cluster --region ap-southeast-1 --name fabric-core-eks
   ```
3. **Tầng 3 — Database & Cache:**
   ```bash
   aws rds delete-db-cluster --region ap-southeast-1 --db-cluster-identifier fabric-core-db --skip-final-snapshot
   aws elasticache delete-replication-group --region ap-southeast-1 --replication-group-id fabric-core-redis
   aws sqs delete-queue --region ap-southeast-1 --queue-url <ORDER_QUEUE_URL>
   ```
4. **Tầng 4 — Firewalls & GWLB:**
   ```bash
   aws network-firewall delete-firewall --region ap-southeast-1 --firewall-name fabric-egress-nfw
   aws ec2 terminate-instances --region ap-southeast-1 --instance-ids i-09dfd64e9a8f1ca33 i-079730fdf83f4fbb4
   aws elbv2 delete-load-balancer --region ap-southeast-1 --load-balancer-arn <GWLB_ARN>
   ```
5. **Tầng 5 — Transit Gateway:**
   ```bash
   aws ec2 delete-transit-gateway-vpc-attachment --region ap-southeast-1 --transit-gateway-attachment-id <TGW_ATTACH_ID>
   aws ec2 delete-transit-gateway --region ap-southeast-1 --transit-gateway-id <TGW_ID>
   ```
6. **Tầng 6 — NAT Gateways, EIPs & VPCs:**
   ```bash
   aws ec2 delete-nat-gateway --region ap-southeast-1 --nat-gateway-id nat-090956bda19ee8ee4
   aws ec2 release-address --region ap-southeast-1 --allocation-id <EIP_ALLOC_ID>
   aws ec2 delete-vpc --region ap-southeast-1 --vpc-id <VPC_ID>
   ```

---

## 5. Phụ Thuộc (Dependencies)

* Đã hoàn tất toàn bộ các bài lab kiểm thử từ Module 00 đến Module 10.
* Đã thu thập và lưu trữ toàn bộ bằng chứng runtime tại [Module 11](../11-bang-chung-bao-cao/README.md).
* Tài khoản quản trị AWS có quyền xóa tài nguyên (`AdministratorAccess` hoặc policy dọn dẹp chuyên dụng).

---

## 6. Kiểm Tra Đạt (Verification)

| Hạng Mục | Lệnh Kiểm Tra / Metric | Kỳ Vọng Đạt |
| :--- | :--- | :--- |
| **Không Còn EKS Clusters** | `aws eks list-clusters --region ap-southeast-1` | Danh sách rỗng hoặc không chứa cụm `fabric-` |
| **Không Còn NAT Gateways** | `aws ec2 describe-nat-gateways --query 'NatGateways[?State!=`deleted`]'` | 0 NAT Gateways hoạt động |
| **Không Còn VPCs Dự Án** | `aws ec2 describe-vpcs --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric"` | 0 VPCs tồn tại |
| **Không Còn ENI Kẹt** | `aws ec2 describe-network-interfaces --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric"` | 0 Network Interfaces tồn dư |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

> [!CAUTION]
> Quá trình Teardown là thao tác **HỦY DIỆT VĨNH VIỄN** (Irreversible Action). Toàn bộ dữ liệu cơ sở dữ liệu, chứng chỉ và cấu hình mạng sẽ bị xóa bỏ. Chỉ thực hiện khi đã sao lưu đầy đủ bằng chứng vào thư mục `evidence/`.

### Kế Hoạch Tái Thiết Lập (Re-Provisioning Plan)
Dự án không hỗ trợ rollback tức thì sau khi xóa. Nếu cần dựng lại môi trường, thực hiện lại tuần tự từ Module 00 theo tài liệu kiến trúc hoặc triển khai tự động qua các module IaC/Terraform.
