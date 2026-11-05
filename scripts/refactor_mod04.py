#!/usr/bin/env python3
"""Refactor Module 04 files: AWS LB Controller IP-targets for Core NLB, Private DNS, Workloads."""

from pathlib import Path

BASE = Path("E:/repo/project6/aws-eks-secure-network-fabric/labs/04-phan-bo-workloads")

# 01-database-and-cache-setup.md
(BASE / "01-database-and-cache-setup.md").write_text("""# 04.01 — Khởi Tạo Aurora PostgreSQL & ElastiCache Redis Tại Core Data Subnets

> **Mã bài lab:** `04.01`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 40 phút  
> **Chi phí ước tính:** ~$0.12 USD / giờ (Aurora Serverless v2 0.5 ACU + Redis cache.t4g.micro)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — Subnets: `10.50.20.0/24`, `10.50.21.0/24`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành hạ tầng mạng Core VPC tại [Module 02](../02-ha-tang-mang-co-ban/README.md) và cụm Core EKS tại [Module 03](../03-cum-eks-kep/README.md).
- Data subnets (`fabric-core-data-1a`, `fabric-core-data-1b`) đã sẵn sàng.

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
        "elasticache:CreateCacheSubnetGroup",
        "elasticache:CreateServerlessCache",
        "elasticache:DescribeServerlessCaches"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Aurora Serverless v2 (0.5 ACU) tiêu tốn ~$0.06/giờ. ElastiCache tiêu tốn ~$0.02/giờ. Cần tắt hoặc xóa khi kết thúc bài lab.
- **Cảnh báo cô lập dữ liệu (Data Isolation):** Cơ sở dữ liệu và Cache **CHỈ ĐƯỢC PHÉP ĐẶT TRONG CORE DATA SUBNETS**. Security Group của DB chỉ cho phép Inbound từ Core Node Subnet (`10.50.10.0/22`, `10.50.14.0/22`). Tuyệt đối cấm kết nối trực tiếp từ Edge VPC (`10.40.0.0/16`) hay Internet.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Tạo DB Subnet Group & Cache Subnet Group
1. Truy cập **RDS Console** -> **Subnet groups** -> **Create DB Subnet Group**:
   - Name: `fabric-core-rds-subnet-group`
   - VPC: `fabric-core-vpc`
   - Subnets: Chọn 2 Data Subnets `fabric-core-data-1a` và `fabric-core-data-1b`.
2. Truy cập **ElastiCache Console** -> **Subnet groups** -> Tạo `fabric-core-redis-subnet-group` trên cùng 2 Data subnets.

### Bước 2: Tạo Security Group Cho Data Layer
Tạo Security Group `fabric-core-data-sg` trong `fabric-core-vpc`:
- Inbound:
  - Port `5432` (PostgreSQL) từ CIDR Core Nodes: `10.50.10.0/22`, `10.50.14.0/22`.
  - Port `6379` (Redis) từ CIDR Core Nodes: `10.50.10.0/22`, `10.50.14.0/22`.
- Outbound: All traffic.

### Bước 3: Khởi Tạo Amazon Aurora PostgreSQL Serverless v2
1. **RDS Console** -> **Databases** -> **Create database**:
   - Engine type: `Aurora (PostgreSQL Compatible)`
   - Engine version: `Aurora PostgreSQL 16.x`
   - Templates: `Dev/Test`
   - DB cluster identifier: `fabric-core-db`
   - Master username: `postgresadmin`
   - Auto generate password: Chọn **Manage master credentials in AWS Secrets Manager**.
   - Capacity range: Min: `0.5 ACU`, Max: `1.0 ACU` (tối ưu chi phí).
   - Connectivity: Chọn `fabric-core-vpc`, DB Subnet group `fabric-core-rds-subnet-group`.
   - Public access: `No`.
   - Security group: `fabric-core-data-sg`.
2. Nhấp **Create database**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái cluster Aurora và Secrets Manager qua CLI:
```bash
aws rds describe-db-clusters --region ap-southeast-1 \
  --db-cluster-identifier fabric-core-db \
  --query 'DBClusters[0].{Id:DBClusterIdentifier,Status:Status,Endpoint:Endpoint,ServerlessV2Min:ServerlessV2ScalingConfiguration.MinCapacity}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Xóa cụm Aurora PostgreSQL và bỏ snapshot:
```bash
aws rds delete-db-cluster --region ap-southeast-1 \
  --db-cluster-identifier fabric-core-db \
  --skip-final-snapshot
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/04-workloads/01-aurora-db-status.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Cụm Aurora PostgreSQL Serverless v2 đạt trạng thái `available`.
- [ ] DB Subnet Group chỉ bao gồm các Data Subnets thuộc Core VPC.
- [ ] Master credentials được mã hóa và lưu trữ an toàn trong AWS Secrets Manager.
""", encoding="utf-8")

# 02-route53-private-hosted-zone.md
(BASE / "02-route53-private-hosted-zone.md").write_text("""# 04.02 — Cấu Hình Route 53 Private Hosted Zone (PHZ) Cho Nội Bộ Fabric

> **Mã bài lab:** `04.02`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 20 phút  
> **Chi phí ước tính:** ~$0.50 USD / hosted zone / tháng  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab tại [Module 02](../02-ha-tang-mang-co-ban/README.md).
- Cả `fabric-edge-vpc` và `fabric-core-vpc` đều đã bật `enableDnsHostnames` và `enableDnsSupport`.

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
        "route53:CreateHostedZone",
        "route53:AssociateVPCWithHostedZone",
        "route53:ChangeResourceRecordSets",
        "route53:GetHostedZone"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Route 53 Private Hosted Zone tính phí $0.50 USD/tháng cho mỗi zone.
- **Cảnh báo liên kết VPC:** Private Hosted Zone bắt buộc phải được liên kết (associated) với cả **Edge VPC** và **Core VPC** để các Pod ở Edge có thể phân giải trực tiếp tên miền nội bộ của các microservices ở Core (`order.fabric.internal`, `auth.fabric.internal`).

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Tạo Route 53 Private Hosted Zone
1. Truy cập **Route 53 Console** -> **Hosted zones** -> **Create hosted zone**.
2. **Hosted zone configuration:**
   - Domain name: `fabric.internal`
   - Description: `Private DNS resolution cho AWS EKS Secure Network Fabric`
   - Type: **Private hosted zone**
3. **VPCs to associate with the hosted zone:**
   - Region: `Asia Pacific (Singapore) (ap-southeast-1)`
   - VPC ID: Chọn `fabric-edge-vpc`
4. Nhấp **Create hosted zone**.

### Bước 2: Liên Kết Thêm Core EKS VPC
1. Sau khi zone được tạo, nhấp vào tab **Hosted zone details**.
2. Tại mục **VPCs**, nhấp **Associate VPC**.
3. Chọn Region: `ap-southeast-1` -> VPC ID: `fabric-core-vpc`.
4. Nhấp **Associate VPC**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra danh sách VPCs liên kết với Private Hosted Zone:
```bash
zone_id=$(aws route53 list-hosted-zones-by-name --dns-name fabric.internal --query 'HostedZones[0].Id' --output text)
aws route53 get-hosted-zone --id $zone_id --query '{Name:HostedZone.Name,VPCs:VPCs[*].VPCId}' --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Để xóa Private Hosted Zone:
```bash
aws route53 delete-hosted-zone --id $zone_id
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/04-workloads/02-route53-phz.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Private Hosted Zone `fabric.internal` được tạo thành công.
- [ ] Cả 2 VPCs `fabric-edge-vpc` và `fabric-core-vpc` đều được liên kết hợp lệ.
""", encoding="utf-8")

# 03-core-internal-nlb.md
(BASE / "03-core-internal-nlb.md").write_text("""# 04.03 — Triển Khai Core Internal NLB Sử Dụng AWS Load Balancer Controller (IP-target)

> **Mã bài lab:** `04.03`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** ~$0.0225 USD / giờ cho Network Load Balancer tại Singapore  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành [03.04](04-eks-pod-identity-and-addons.md) với AWS Load Balancer Controller đã được cài đặt trên cụm `fabric-core-eks`.
- Private Hosted Zone `fabric.internal` đã sẵn sàng từ bài lab [04.02](02-route53-private-hosted-zone.md).

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

AWS Load Balancer Controller sử dụng EKS Pod Identity để gọi các API quản lý NLB:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:CreateLoadBalancer",
        "elasticloadbalancing:CreateTargetGroup",
        "elasticloadbalancing:RegisterTargets",
        "elasticloadbalancing:DeregisterTargets",
        "elasticloadbalancing:Describe*"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Network Load Balancer tính phí ~$0.0225 USD/giờ cộng với phí NLCU truyền dữ liệu.
- **Cảnh báo Kiến Trúc IP-Target (Không dùng IP thủ công):** Tuyệt đối **KHÔNG ĐƯỢC ĐĂNG KÝ POD IP BẰNG TAY** vào Target Group của NLB. Trong môi trường Kubernetes, Pod IP thay đổi liên tục khi Pod restart/reschedule. Bắt buộc phải để AWS Load Balancer Controller tự động quản lý vòng đời target thông qua Service manifest với annotation `nlb-ip`.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Triển Khai Kubernetes Service Với Annotation Quản Lý NLB
Tạo file manifest `core-internal-nlb.yaml`:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: core-internal-nlb
  namespace: fabric-apps
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "external"
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internal"
    service.beta.kubernetes.io/aws-load-balancer-subnets: "fabric-core-nodes-1a, fabric-core-nodes-1b"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
spec:
  type: LoadBalancer
  selector:
    app: order-service
  ports:
  - name: https-order
    port: 443
    targetPort: 8082
    protocol: TCP
```

Áp dụng manifest vào cụm Core EKS:
```bash
kubectl apply -f core-internal-nlb.yaml
```

### Bước 2: Kiểm Tra Trạng Thái Tạo Tự Động Của NLB Trên AWS Console
1. Truy cập **EC2 Console** -> **Load Balancers**.
2. Tìm Load Balancer kiểu Network có tiền tố `k8s-fabricap-coreinte-*`:
   - Xác nhận **Scheme** là `Internal`.
   - Xác nhận **VPC** là `fabric-core-vpc`.
   - Kiểm tra **Target Groups**: Xác nhận Target type là `IP` và các Pod IPs của `order-service` đang được đăng ký tự động và đạt trạng thái `healthy`.

### Bước 3: Cập Nhật DNS Record Trên Route 53 Private Hosted Zone
Gán CNAME/Alias record cho `order.fabric.internal` trỏ tới DNS Name của NLB:
```bash
nlb_dns=$(kubectl get svc core-internal-nlb -n fabric-apps -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
# Tạo bản ghi Route 53
aws route53 change-resource-record-sets --hosted-zone-id $zone_id --change-batch '{
  "Changes": [{
    "Action": "UPSERT",
    "ResourceRecordSet": {
      "Name": "order.fabric.internal",
      "Type": "CNAME",
      "TTL": 60,
      "ResourceRecords": [{"Value": "'"$nlb_dns"'"}]
    }
  }]
}'
```

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái Service và Target Health:
```bash
# 1. Kiểm tra Kubernetes Service
kubectl get svc core-internal-nlb -n fabric-apps -o wide

# 2. Kiểm tra AWS Target Group Health qua CLI
tg_arn=$(aws elbv2 describe-target-groups --region ap-southeast-1 --query 'TargetGroups[?contains(TargetGroupName, `coreinte`)].TargetGroupArn' --output text)
aws elbv2 describe-target-health --region ap-southeast-1 --target-group-arn $tg_arn --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Xóa Kubernetes Service để AWS Load Balancer Controller tự động dọn dẹp NLB và Target Group:
```bash
kubectl delete svc core-internal-nlb -n fabric-apps
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/04-workloads/03-core-nlb-status.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Core Internal NLB đạt trạng thái `active` với Scheme `internal`.
- [ ] Target type là `IP`, các Pod IPs được Controller đăng ký tự động ở trạng thái `healthy`.
- [ ] Bản ghi DNS `order.fabric.internal` phân giải thành công tới địa chỉ IP nội bộ của NLB.
""", encoding="utf-8")

# 04-microservices-gitops-deploy.md
(BASE / "04-microservices-gitops-deploy.md").write_text("""# 04.04 — Triển Khai Microservices & Đồng Bộ GitOps (Argo CD)

> **Mã bài lab:** `04.04`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab từ [04.01](01-database-and-cache-setup.md) đến [04.03](03-core-internal-nlb.md).
- Repository ứng dụng `aws-eks-secure-network-fabric-app` đã có sẵn các manifests và Kustomize overlays.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Bài lab tương tác với cụm EKS thông qua Argo CD và `kubectl`, không yêu cầu quyền gọi trực tiếp AWS API.

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD.
- **Cảnh báo phân bổ kiến trúc (Workload Separation):**
  - Cụm **Edge EKS** CHỈ CHỨA: `frontend` và `auth-service`.
  - Cụm **Core EKS** CHỈ CHỨA: `order-service`, `inventory-service`, `payment-worker`.
  - Tuyệt đối không deploy chéo dịch vụ nghiệp vụ sang cụm Edge để đảm bảo nguyên tắc phân tách vùng tin cậy.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Tham Chiếu Runbooks Triển Khai Tại Repo Ứng Dụng
Các bước chi tiết được chuẩn hóa tại 4 tài liệu runbook trong repository `aws-eks-secure-network-fabric-app`:
1. [Build & Publish Images Runbook](../../../aws-eks-secure-network-fabric-app/docs/runbooks/build-images.md)
2. [GitOps Deployment Runbook](../../../aws-eks-secure-network-fabric-app/docs/runbooks/gitops-deploy.md)
3. [NetworkPolicy Enforcement Runbook](../../../aws-eks-secure-network-fabric-app/docs/runbooks/network-policy.md)
4. [Rollback & Cleanup Runbook](../../../aws-eks-secure-network-fabric-app/docs/runbooks/rollback-cleanup.md)

### Bước 2: Triển Khai Workloads Lên Edge EKS
Áp dụng Kustomize overlay cho Edge EKS:
```bash
kubectl apply -k https://github.com/Kien-devops/aws-eks-secure-network-fabric-app.git/gitops/overlays/edge-prod
```

### Bước 3: Triển Khai Workloads Lên Core EKS
Áp dụng Kustomize overlay cho Core EKS:
```bash
kubectl apply -k https://github.com/Kien-devops/aws-eks-secure-network-fabric-app.git/gitops/overlays/core-prod
```

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra danh sách Pods đang chạy trên cả 2 cụm EKS:
```bash
# Kiểm tra Edge EKS
kubectl get pods -n fabric-apps -l 'app in (frontend, auth-service)' -o wide

# Kiểm tra Core EKS
kubectl get pods -n fabric-apps -l 'app in (order-service, inventory-service, payment-worker)' -o wide
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Hoàn tác deployment nếu ứng dụng phát sinh lỗi:
```bash
kubectl rollout undo deployment/frontend -n fabric-apps
kubectl rollout undo deployment/order-service -n fabric-apps
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/04-workloads/04-gitops-pods-status.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Toàn bộ 5 microservices đạt trạng thái `Running` (1/1) trên đúng cụm EKS quy định.
- [ ] Không có hiện tượng Pod rơi vào trạng thái `CrashLoopBackOff`.
- [ ] Frontend gọi sang Order Service thành công qua Route 53 `order.fabric.internal`.
""", encoding="utf-8")

# Update README.md for Module 04
(BASE / "README.md").write_text("""# Module 04: Phân Bổ Workloads & Dịch Vụ Nội Bộ (app3 Microservices)

Module này hướng dẫn triển khai hệ thống 5 microservices (`frontend`, `auth-service`, `order-service`, `inventory-service`, `payment-worker`), cơ sở dữ liệu Amazon Aurora Serverless v2, ElastiCache Redis, phân giải DNS Route 53 Private Hosted Zone và Core Internal NLB tự động quản lý IP targets qua AWS Load Balancer Controller.

## Danh Sách Bài Lab

| Mã Lab | Tên Bài Lab & Nội Dung Trọng Tâm | Trạng Thái | File Hướng Dẫn |
|---|---|:---:|---|
| **04.01** | **Aurora PostgreSQL & ElastiCache Redis:** Data layer cô lập tại Core VPC. | `DRAFT` | [01-database-and-cache-setup.md](01-database-and-cache-setup.md) |
| **04.02** | **Route 53 Private Hosted Zone:** Phân giải `fabric.internal` nội bộ liên VPC. | `DRAFT` | [02-route53-private-hosted-zone.md](02-route53-private-hosted-zone.md) |
| **04.03** | **Core Internal NLB (IP-targets):** AWS Load Balancer Controller tự động quản lý Pod IP. | `DRAFT` | [03-core-internal-nlb.md](03-core-internal-nlb.md) |
| **04.04** | **Triển Khai Microservices & GitOps:** Đồng bộ 5 services tuân thủ chuẩn phân vùng. | `DRAFT` | [04-microservices-gitops-deploy.md](04-microservices-gitops-deploy.md) |
""", encoding="utf-8")

print("Module 04 rewritten successfully.")
