# 03.03 — Đặc Tả Managed Node Groups Riêng Tư Cho Hai Cụm EKS

> **Mã bài lab:** `03.03`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore) — AZs: `ap-southeast-1a`, `ap-southeast-1b`
> **File bằng chứng:** `evidence/03-eks/03-nodes-ready.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả cấu hình hạ tầng tính toán riêng tư cho hai cụm EKS bằng Managed Node Groups (EC2 Spot `t3.medium`, Amazon Linux 2023) đặt trong các Subnets Private Nodes của Edge VPC và Core VPC với cơ chế quản trị không SSH thông qua AWS Systems Manager.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Vị Trí / VPC / AZ | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-eks-node-role` | `AWS::IAM::Role` | Global (IAM) | `arn:aws:iam::123456789012:role/fabric-eks-node-role` |
| `fabric-edge-ng-1` | `AWS::EKS::Nodegroup` | `fabric-edge-vpc` (`1a`, `1b`) | Cụm `fabric-edge-eks`<br>Subnets: `subnet-0e9f90d0d4e220d3a`, `subnet-034f4fc00bfd6cd09` |
| `fabric-core-ng-1` | `AWS::EKS::Nodegroup` | `fabric-core-vpc` (`1a`, `1b`) | Cụm `fabric-core-eks`<br>Subnets: `subnet-0124e28037a2e4118`, `subnet-0fe561d6217b04955` |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-edge-ng-1` / `fabric-core-ng-1` | Gán Name tag cho EC2 Worker Nodes |
| `Project` | `aws-eks-secure-network-fabric` | IAM Role và cả 2 Node Groups |
| `Environment` | `prod` | IAM Role và cả 2 Node Groups |
| `ManagedBy` | `manual` | Quản trị tài nguyên tính toán thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Cấu Hình IAM Node Role

- **Trust Policy:** `ec2.amazonaws.com` (Action: `sts:AssumeRole`)
- **Attached Managed Policies:**
  1. `arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy`
  2. `arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly`
  3. `arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy`
  4. `arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore` (Quản trị từ xa qua SSM Session Manager, không mở SSH port 22).

### 4.2 Cấu Hình Kỹ Thuật Node Groups

| Thuộc Tính | Node Group Edge (`fabric-edge-ng-1`) | Node Group Core (`fabric-core-ng-1`) | Lý Do Thiết Kế |
| :--- | :--- | :--- | :--- |
| **Instance Type** | `t3.medium` (2 vCPU, 4 GiB RAM) | `t3.medium` (2 vCPU, 4 GiB RAM) | Tối ưu hóa chi phí và tài nguyên cụm. |
| **Capacity Type** | `SPOT` | `SPOT` | Tiết kiệm chi phí lên tới 70% trong môi trường lab/dev. |
| **AMI Type** | `AL2023_x86_64_STANDARD` | `AL2023_x86_64_STANDARD` | Amazon Linux 2023 chuẩn hóa cho Kubernetes 1.37. |
| **Disk Size** | `20 GiB` (gp3) | `20 GiB` (gp3) | Đủ dung lượng lưu trữ cho container images và logs. |
| **Scaling Config** | Min: `2`, Desired: `2`, Max: `3` | Min: `2`, Desired: `2`, Max: `4` | Đảm bảo tính sẵn sàng cao (High Availability) trên 2 AZs. |
| **Subnet Placement** | `fabric-edge-nodes-1a/b` | `fabric-core-nodes-1a/b` | Tuyệt đối không cấp Public IP, bảo vệ khỏi Internet. |
| **Remote Access** | `Disabled` | `Disabled` | Tuân thủ Zero Trust, cấm mở cổng 22. |

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `02.01` (Private Node Subnets sẵn sàng).
- Phụ thuộc vào `02.06` (VPC Endpoints cho ECR, S3, STS, logs sẵn sàng để bootstrap node).
- Phụ thuộc vào `03.02` (Cụm EKS ở trạng thái `ACTIVE`).
- Là điều kiện tiên quyết cho `03.04` (Pod Identity & Add-ons) và [Module 04](../04-phan-bo-workloads/README.md).

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng thái Node Groups** | `aws eks describe-nodegroup --cluster-name <Cluster> --nodegroup-name <NodeGroup>` | `nodegroup.status: ACTIVE` cho cả 2 nhóm. |
| **Trạng thái Kubernetes Nodes** | `kubectl get nodes -o wide` trên cả 2 context `fabric-edge` và `fabric-core` | Mỗi cụm có đúng 2 nodes ở trạng thái `Ready`. |
| **Phân bổ Dải IP Subnet** | Kiểm tra Internal IP của nodes | Edge: thuộc dải `10.40.8.0/22`; Core: thuộc dải `10.50.8.0/22`. |
| **Trạng thái Pods Hệ Thống** | `kubectl get pods -n kube-system` | Pods `aws-node`, `coredns`, `kube-proxy` ở trạng thái `Running`. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo chi phí & gián đoạn:** EC2 Spot có thể bị thu hồi nếu thiếu capacity. Trong trường hợp cần tạm nghỉ phiên lab để tiết kiệm chi phí, có thể scale Desired = 0 và phục hồi Desired = 2 trước khi kiểm thử.
- **Quy trình Rollback:**
  ```bash
  # Xóa 2 Node Groups
  aws eks delete-nodegroup --region ap-southeast-1 --cluster-name fabric-edge-eks --nodegroup-name fabric-edge-ng-1
  aws eks delete-nodegroup --region ap-southeast-1 --cluster-name fabric-core-eks --nodegroup-name fabric-core-ng-1

  # Xóa IAM Node Role sau khi EC2 instances đã bị hủy
  aws iam detach-role-policy --role-name fabric-eks-node-role --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
  aws iam detach-role-policy --role-name fabric-eks-node-role --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
  aws iam detach-role-policy --role-name fabric-eks-node-role --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy
  aws iam detach-role-policy --role-name fabric-eks-node-role --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
  aws iam delete-role --role-name fabric-eks-node-role
  ```
