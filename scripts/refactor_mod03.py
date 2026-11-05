#!/usr/bin/env python3
"""Refactor Module 03 files: Upgrade to EKS 1.31, fix bootstrapping dependencies, complete NetworkPolicy matrix."""

from pathlib import Path

BASE = Path("E:/repo/project6/aws-eks-secure-network-fabric/labs/03-cum-eks-kep")

# 01-kms-encryption-keys.md
(BASE / "01-kms-encryption-keys.md").write_text("""# 03.01 — Tạo Khóa Mã Hóa AWS KMS Customer Managed Key Cho EKS Secrets

> **Mã bài lab:** `03.01`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 20 phút  
> **Chi phí ước tính:** ~$1.00 USD / key / tháng ($2.00 USD cho 2 keys Edge & Core)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab thuộc [Module 02](../02-ha-tang-mang-co-ban/README.md).
- Quyền quản trị KMS và IAM trên AWS Account.

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
        "kms:CreateKey",
        "kms:CreateAlias",
        "kms:DescribeKey",
        "kms:EnableKeyRotation",
        "kms:PutKeyPolicy"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Mỗi khóa KMS CMK tính phí $1.00 USD/tháng cố định.
- **Cảnh báo Key Policy:** Key Policy bắt buộc phải cấp quyền `kms:Encrypt`, `kms:Decrypt`, `kms:DescribeKey` cho dịch vụ EKS thông qua service-linked role hoặc ARN cụm EKS. Nếu cấu hình sai, EKS control plane sẽ không thể mã hóa Kubernetes Secrets và tạo cluster thất bại.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Tạo Khóa KMS Cho Edge EKS Cluster
1. Truy cập **AWS KMS Console** tại Region Singapore (`ap-southeast-1`).
2. Chọn **Customer managed keys** -> Nhấp **Create key**:
   - Key type: `Symmetric`.
   - Key usage: `Encrypt and decrypt`.
3. **Add labels:**
   - Alias: `alias/fabric-edge-eks-secrets`.
   - Description: `KMS CMK ma hoa Kubernetes Secrets cho fabric-edge-eks`.
   - Tag: `Project=aws-eks-secure-network-fabric`.
4. **Key administrators:** Chọn IAM Role/User quản trị của bạn.
5. **Key deletion:** Cho phép quản trị viên xóa khóa.
6. **Key rotation:** Tích chọn **Automatically rotate this KMS key every year**.
7. Nhấp **Finish**.

### Bước 2: Tạo Khóa KMS Cho Core EKS Cluster
Thực hiện tương tự Bước 1:
- Alias: `alias/fabric-core-eks-secrets`.
- Description: `KMS CMK ma hoa Kubernetes Secrets cho fabric-core-eks`.
- Bật tính năng Automatic Key Rotation.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra 2 khóa KMS CMK vừa khởi tạo:
```bash
aws kms list-aliases --region ap-southeast-1 \
  --query 'Aliases[?starts_with(AliasName, `alias/fabric-`)].{Alias:AliasName,KeyId:TargetKeyId}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Lên lịch xóa khóa KMS (tối thiểu 7 ngày theo quy định AWS):
```bash
for alias in "alias/fabric-edge-eks-secrets" "alias/fabric-core-eks-secrets"; do
  key_id=$(aws kms describe-key --region ap-southeast-1 --key-id $alias --query 'KeyMetadata.KeyId' --output text 2>/dev/null)
  if [ -n "$key_id" ] && [ "$key_id" != "None" ]; then
    aws kms schedule-key-deletion --region ap-southeast-1 --key-id $key_id --pending-window-in-days 7
  fi
done
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/03-eks/01-kms-keys.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Cả 2 khóa KMS CMK (`alias/fabric-edge-eks-secrets` và `alias/fabric-core-eks-secrets`) ở trạng thái `Enabled`.
- [ ] Tính năng tự động xoay vòng khóa (Key Rotation) được kích hoạt thành công.
""", encoding="utf-8")

# 02-dual-eks-clusters.md
(BASE / "02-dual-eks-clusters.md").write_text("""# 03.02 — Khởi Tạo Hai Cụm Private EKS 1.31 Riêng Biệt (Edge & Core)

> **Mã bài lab:** `03.02`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** ~$0.10 USD / giờ / cluster (~$0.20 USD / giờ cho 2 cụm EKS)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành [03.01](01-kms-encryption-keys.md) và toàn bộ hạ tầng mạng [Module 02](../02-ha-tang-mang-co-ban/README.md) (bao gồm VPC Endpoints tại `02.06`).
- IAM Role cho EKS Cluster (`fabric-eks-cluster-role`) đã được tạo với policy `AmazonEKSClusterPolicy`.

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
        "eks:CreateCluster",
        "eks:DescribeCluster",
        "eks:UpdateClusterConfig",
        "eks:ListClusters",
        "iam:PassRole"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** EKS Control Plane tính phí $0.10 USD/giờ mỗi cụm (~$4.80 USD/ngày cho 2 cụm).
- **Cảnh báo Phiên Bản EKS:** **BẮT BUỘC DÙNG EKS 1.31** (hoặc 1.32). Phiên bản EKS 1.30 đã kết thúc hỗ trợ tiêu chuẩn (End of Standard Support) từ tháng 11/2025, AWS sẽ tính thêm phí mở rộng hỗ trợ (Extended Support Fee: $0.60/giờ).
- **Cảnh báo Endpoint Access:** Nhằm tuân thủ bảo mật tuyệt đối, Control Plane Endpoint được cấu hình:
  - `Private access: Enabled`
  - `Public access: Disabled` (hoặc chỉ mở Public kèm CIDR restriction tới IP VPN/Bastion của bạn).

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Tạo IAM Role Cho EKS Control Plane
1. Truy cập **IAM Console** -> **Roles** -> **Create role**.
2. Service: `EKS` -> Use case: `EKS - Cluster`.
3. Permissions policy: `AmazonEKSClusterPolicy`.
4. Role name: `fabric-eks-cluster-role`.

### Bước 2: Khởi Tạo Cụm `fabric-edge-eks` (EKS 1.31)
1. Truy cập **Amazon EKS Console** tại `ap-southeast-1` -> **Add cluster** -> **Create**.
2. **Configure cluster:**
   - Name: `fabric-edge-eks`
   - Kubernetes version: **`1.31`**
   - Cluster service role: `fabric-eks-cluster-role`
   - Secrets encryption: Chọn khóa KMS `alias/fabric-edge-eks-secrets`.
3. **Specify networking:**
   - VPC: `fabric-edge-vpc`
   - Subnets: Chọn 2 Private Subnets `fabric-edge-nodes-1a` và `fabric-edge-nodes-1b`.
   - Cluster endpoint access: Chọn **Private** (hoặc Public and private nếu quản trị từ máy local có IP allowlist).
4. **Configure logging:** Bật `API server`, `Audit`, `Authenticator`.
5. Nhấp **Create**. Quá trình tạo mất khoảng 10-15 phút.

### Bước 3: Khởi Tạo Cụm `fabric-core-eks` (EKS 1.31)
Thực hiện tương tự Bước 2 cho Core cluster:
- Name: `fabric-core-eks`
- Kubernetes version: **`1.31`**
- VPC: `fabric-core-vpc`
- Subnets: `fabric-core-nodes-1a` và `fabric-core-nodes-1b`
- Secrets encryption: Chọn khóa KMS `alias/fabric-core-eks-secrets`.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái sẵn sàng của 2 cụm EKS qua CLI:
```bash
aws eks describe-cluster --region ap-southeast-1 --name fabric-edge-eks \
  --query 'cluster.{Name:name,Version:version,Status:status,EndpointAccess:resourcesVpcConfig.endpointPublicAccess}' \
  --output table

aws eks describe-cluster --region ap-southeast-1 --name fabric-core-eks \
  --query 'cluster.{Name:name,Version:version,Status:status,EndpointAccess:resourcesVpcConfig.endpointPublicAccess}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Nếu cần xóa cụm EKS:
```bash
aws eks delete-cluster --region ap-southeast-1 --name fabric-edge-eks
aws eks delete-cluster --region ap-southeast-1 --name fabric-core-eks
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/03-eks/02-clusters-active.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Cả 2 cụm `fabric-edge-eks` và `fabric-core-eks` đạt trạng thái `ACTIVE`.
- [ ] Phiên bản Kubernetes chính xác là **`1.31`**.
- [ ] Tính năng KMS Secrets Encryption được kích hoạt với đúng Key Alias.
""", encoding="utf-8")

# 03-managed-node-groups.md
(BASE / "03-managed-node-groups.md").write_text("""# 03.03 — Khởi Tạo Managed Node Groups Riêng Tư Cho Hai Cụm EKS

> **Mã bài lab:** `03.03`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 40 phút  
> **Chi phí ước tính:** ~$0.0416 USD / giờ / instance t3.medium (4 instances = ~$0.166 USD / giờ)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — Subnets: `nodes-1a`, `nodes-1b`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bài lab [03.02](02-dual-eks-clusters.md). Cả 2 cụm EKS đang ở trạng thái `ACTIVE`.
- **Yêu cầu kết nối bắt buộc:** Private VPC Endpoints tại lab [02.06](../02-ha-tang-mang-co-ban/06-private-vpc-endpoints.md) (ECR, S3, STS, EC2, Logs) HOẶC đường Egress NAT qua TGW phải sẵn sàng để các worker nodes bootstrap và join cluster.

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
        "eks:CreateNodegroup",
        "eks:DescribeNodegroup",
        "eks:ListNodegroups",
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PassRole"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** 4 EC2 instances `t3.medium` (2 nodes per cluster) tiêu tốn ~$4.00 USD/ngày.
- **Cảnh báo Node Subnet Placement:** Các worker node **chỉ được phép nằm trong Private Subnets** (`fabric-edge-nodes-1a/b` và `fabric-core-nodes-1a/b`). Tuyệt đối không đặt worker node vào Public subnet hoặc TGW subnet.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Tạo IAM Role Cho Worker Nodes
1. Truy cập **IAM Console** -> **Create role** -> Service: `EC2`.
2. Gán các AWS Managed Policies bắt buộc:
   - `AmazonEKSWorkerNodePolicy`
   - `AmazonEC2ContainerRegistryReadOnly`
   - `AmazonEKS_CNI_Policy`
   - `AmazonSSMManagedInstanceCore` (phục vụ kết nối an toàn qua SSM Session Manager, không cần SSH).
3. Đặt tên role: `fabric-eks-node-role`.

### Bước 2: Tạo Node Group Cho `fabric-edge-eks`
1. Tại **EKS Console** -> Chọn `fabric-edge-eks` -> Tab **Compute** -> Nhấp **Add node group**.
2. **Configure node group:**
   - Name: `fabric-edge-ng-1`
   - Node IAM role: Chọn `fabric-eks-node-role`
3. **Compute and scaling configuration:**
   - AMI type: `Amazon Linux 2023 (AL2023_x86_64_STANDARD)`
   - Capacity type: `On-Demand`
   - Instance types: `t3.medium`
   - Scaling: Min: `2`, Desired: `2`, Max: `3`
4. **Networking:**
   - Subnets: Chọn `fabric-edge-nodes-1a` và `fabric-edge-nodes-1b`.
5. Nhấp **Create**.

### Bước 3: Tạo Node Group Cho `fabric-core-eks`
Thực hiện tương tự Bước 2 cho Core cluster:
- Name: `fabric-core-ng-1`
- Subnets: Chọn `fabric-core-nodes-1a` và `fabric-core-nodes-1b`.
- Instance types: `t3.medium` (Min: `2`, Desired: `2`, Max: `4`).

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái các node groups và xác nhận các Kubernetes worker nodes đã `Ready`:
```bash
# 1. Kiểm tra trạng thái Node Group qua AWS CLI
aws eks describe-nodegroup --region ap-southeast-1 --cluster-name fabric-edge-eks --nodegroup-name fabric-edge-ng-1 \
  --query 'nodegroup.{Name:nodegroupName,Status:status,Desired:scalingConfig.desiredSize}' --output table

# 2. Cập nhật kubeconfig và kiểm tra danh sách Node qua kubectl
aws eks update-kubeconfig --region ap-southeast-1 --name fabric-edge-eks
kubectl get nodes -o wide
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Xóa Node Groups trước khi xóa cụm EKS:
```bash
aws eks delete-nodegroup --region ap-southeast-1 --cluster-name fabric-edge-eks --nodegroup-name fabric-edge-ng-1
aws eks delete-nodegroup --region ap-southeast-1 --cluster-name fabric-core-eks --nodegroup-name fabric-core-ng-1
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/03-eks/03-nodes-ready.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] 2 Node Groups ở trạng thái `ACTIVE`.
- [ ] Lệnh `kubectl get nodes` hiển thị đủ 2 worker nodes ở trạng thái `Ready` trên mỗi cụm.
- [ ] Worker nodes phân bố đồng đều trên cả 2 AZ: `ap-southeast-1a` và `ap-southeast-1b`.
""", encoding="utf-8")

# 04-eks-pod-identity-and-addons.md
(BASE / "04-eks-pod-identity-and-addons.md").write_text("""# 03.04 — Cấu Hình EKS Pod Identity & Cài Đặt Managed Add-ons

> **Mã bài lab:** `03.04`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 30 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab [03.02](02-dual-eks-clusters.md) và [03.03](03-managed-node-groups.md).
- Các worker nodes đã ở trạng thái `Ready`.

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
        "eks:CreateAddon",
        "eks:DescribeAddon",
        "eks:CreatePodIdentityAssociation",
        "eks:DescribePodIdentityAssociation",
        "iam:CreateRole",
        "iam:AttachRolePolicy"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD (EKS Pod Identity agent và Core Managed Add-ons miễn phí).
- **Cảnh báo công nghệ:** Sử dụng **EKS Pod Identity** thay thế cho kiến trúc IRSA cũ (IAM Roles for Service Accounts). Pod Identity mang lại độ trễ thấp hơn, quản trị IAM Role đơn giản hơn và không yêu cầu quản lý OIDC Identity Provider thủ công trên IAM.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Cài Đặt EKS Pod Identity Agent Add-on
1. Tại **EKS Console** -> Chọn `fabric-edge-eks` -> Tab **Add-ons** -> **Get more add-ons**.
2. Chọn **EKS Pod Identity Agent** -> Version mới nhất -> Nhấp **Create**.
3. Lặp lại thao tác trên cho cụm `fabric-core-eks`.

### Bước 2: Cài Đặt Các Managed Add-ons Cốt Lõi
Cài đặt bổ sung các add-ons sau cho cả 2 cụm:
1. `vpc-cni` (Hỗ trợ cấu hình AWS VPC CNI NetworkPolicy)
2. `coredns`
3. `kube-proxy`
4. `aws-ebs-csi-driver`

### Bước 3: Tạo IAM Role & Pod Identity Association
Tạo IAM Role cho AWS Load Balancer Controller và EBS CSI Driver, sau đó liên kết thông qua Pod Identity:
1. **EKS Console** -> Chọn cụm -> Tab **Access** -> Mục **Pod Identity associations** -> Nhấp **Create**.
2. Chọn Namespace: `kube-system`.
3. Nhập Service Account: `aws-load-balancer-controller`.
4. Chọn IAM Role tương ứng có quyền quản lý NLB/ALB.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra danh sách Add-ons và Pod Identity Associations:
```bash
# 1. Liệt kê các add-ons trên Edge EKS
aws eks list-addons --region ap-southeast-1 --cluster-name fabric-edge-eks --output table

# 2. Liệt kê Pod Identity Associations
aws eks list-pod-identity-associations --region ap-southeast-1 --cluster-name fabric-edge-eks --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Để gỡ bỏ Pod Identity association hoặc Add-on:
```bash
aws eks delete-pod-identity-association --region ap-southeast-1 --cluster-name fabric-edge-eks --association-id <id>
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/03-eks/04-addons-status.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Add-on `eks-pod-identity-agent` đạt trạng thái `ACTIVE`.
- [ ] Add-on `vpc-cni` phiên bản mới nhất hỗ trợ native NetworkPolicy.
- [ ] Pod Identity Associations được liên kết chính xác với ServiceAccount.
""", encoding="utf-8")

# 05-k8s-network-policy-baseline.md
(BASE / "05-k8s-network-policy-baseline.md").write_text("""# 03.05 — Thiết Lập Ma Trận Kubernetes NetworkPolicy Hoàn Chỉnh (Zero Trust)

> **Mã bài lab:** `03.05`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bài lab [03.04](04-eks-pod-identity-and-addons.md).
- VPC CNI NetworkPolicy controller đã được kích hoạt trên EKS bằng cách đặt biến môi trường:
  ```bash
  kubectl set env daemonset aws-node -n kube-system ENABLE_NETWORK_POLICY=true
  ```

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Bài lab tương tác trực tiếp với Kubernetes API qua `kubectl`, không yêu cầu gọi AWS API.

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD.
- **Cảnh báo Ma Trận Cô Lập (Isolation Matrix):** Default-deny nếu cấu hình thiếu sẽ cắt đứt CoreDNS hoặc ngắt liên lạc giữa các microservices! Bắt buộc phải áp dụng đầy đủ quy tắc cho:
  - Cho phép DNS (port 53 UDP/TCP).
  - `frontend` chỉ được gọi `auth-service` (8081) và `order-service` (8082).
  - `order-service` chỉ được gọi Aurora PostgreSQL (5432), Redis (6379), và AWS SQS VPCE (443).
  - `payment-worker` chỉ được gọi SQS VPCE (443) và Aurora PostgreSQL (5432).

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Kích Hoạt Tính Năng NetworkPolicy Trên AWS VPC CNI
Chạy lệnh kích hoạt NetworkPolicy agent trong daemonset `aws-node`:
```bash
kubectl set env daemonset aws-node -n kube-system ENABLE_NETWORK_POLICY=true
kubectl rollout status daemonset aws-node -n kube-system
```

### Bước 2: Triển Khai Default Deny Cho Namespace Ứng Dụng
Tạo file manifest `default-deny-all.yaml`:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: fabric-apps
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
# Cho phép phân giải DNS trong cụm
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-egress
  namespace: fabric-apps
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

### Bước 3: Triển Khai Ma Trận Cho Phép Chi Tiết Giữa Các Microservices
Áp dụng các policy chi tiết:

1. **Frontend NetworkPolicy (Edge Cluster):**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-policy
  namespace: fabric-apps
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector: {} # Cho phép Ingress từ ALB qua Ingress Controller
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - ipBlock:
        cidr: 10.50.0.0/16 # Cho phép gọi sang Core VPC qua TGW / Core NLB
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 8081
    - protocol: TCP
      port: 8082
```

2. **Order & Payment NetworkPolicy (Core Cluster):**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: order-service-policy
  namespace: fabric-apps
spec:
  podSelector:
    matchLabels:
      app: order-service
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - ipBlock:
        cidr: 10.40.0.0/16 # Chỉ nhận kết nối từ Edge VPC
    ports:
    - protocol: TCP
      port: 8082
  egress:
  - to:
    - ipBlock:
        cidr: 10.50.20.0/23 # Data subnets (Aurora DB: 5432, Redis: 6379)
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
  - to:
    - ipBlock:
        cidr: 10.50.30.0/23 # SQS VPCE: 443
    ports:
    - protocol: TCP
      port: 443
```

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái áp dụng NetworkPolicy:
```bash
kubectl get networkpolicies -n fabric-apps -o wide
```

Thử nghiệm kiểm tra drop gói tin khi vi phạm policy:
```bash
# Thử kết nối từ pod không được cấp quyền tới database
kubectl run test-pod --rm -it --image=busybox -n fabric-apps -- nc -zvw 3 10.50.20.15 5432 || echo "NetworkPolicy DROP confirmed!"
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Trong trường hợp cần gỡ bỏ NetworkPolicy để khắc phục sự cố:
```bash
kubectl delete networkpolicies --all -n fabric-apps
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/03-eks/05-network-policy-verification.log`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Tính năng native NetworkPolicy hoạt động trên AWS VPC CNI.
- [ ] Quy tắc default-deny ngăn chặn thành công các kết nối trái phép giữa các pods.
- [ ] Pods hợp lệ kết nối thành công tới đúng các cổng nghiệp vụ (53, 443, 5432, 6379, 8081, 8082).
""", encoding="utf-8")

# Update README.md for Module 03
(BASE / "README.md").write_text("""# Module 03: Cụm Kubernetes EKS Kép (Dual EKS Clusters 1.31)

Module này hướng dẫn triển khai 2 cụm Amazon EKS riêng tư (Private Clusters) trên phiên bản Kubernetes **1.31** mới nhất, mã hóa bằng AWS KMS Secrets, kết nối thông qua EKS Pod Identity và kiểm soát Zero Trust bằng AWS VPC CNI NetworkPolicy.

## Danh Sách Bài Lab

| Mã Lab | Tên Bài Lab & Nội Dung Trọng Tâm | Trạng Thái | File Hướng Dẫn |
|---|---|:---:|---|
| **03.01** | **Tạo Khóa KMS CMK:** Mã hóa Kubernetes Secrets độc lập cho Edge và Core. | `DRAFT` | [01-kms-encryption-keys.md](01-kms-encryption-keys.md) |
| **03.02** | **Khởi Tạo Cụm EKS Kép 1.31:** Cụm riêng tư `fabric-edge-eks` và `fabric-core-eks`. | `DRAFT` | [02-dual-eks-clusters.md](02-dual-eks-clusters.md) |
| **03.03** | **Managed Node Groups:** Worker nodes AL2023 phân bố đa AZ, cấu hình SSM. | `DRAFT` | [03-managed-node-groups.md](03-managed-node-groups.md) |
| **03.04** | **EKS Pod Identity & Add-ons:** Pod Identity Agent, VPC CNI, EBS CSI Driver. | `DRAFT` | [04-eks-pod-identity-and-addons.md](04-eks-pod-identity-and-addons.md) |
| **03.05** | **K8s NetworkPolicy Baseline:** Ma trận Zero Trust pod-to-pod, default deny. | `DRAFT` | [05-k8s-network-policy-baseline.md](05-k8s-network-policy-baseline.md) |
""", encoding="utf-8")

print("Module 03 rewritten successfully.")
