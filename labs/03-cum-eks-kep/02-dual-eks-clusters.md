# 03.02 — Đặc Tả Khởi Tạo Hai Cụm EKS Riêng Biệt (Edge & Core)

> **Mã bài lab:** `03.02`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/03-eks/02-clusters-active.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả tài nguyên và cấu hình bảo mật cho hai cụm Amazon EKS độc lập (`fabric-edge-eks` trên Edge VPC và `fabric-core-eks` trên Core VPC) với phiên bản Kubernetes 1.37, mã hóa etcd bằng AWS KMS CMK, bật toàn bộ nhật ký Control Plane và cô lập giao diện mạng trong Subnets Private Nodes.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Vị Trí / VPC / AZ | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-eks-cluster-role` | `AWS::IAM::Role` | Global (IAM) | `arn:aws:iam::123456789012:role/fabric-eks-cluster-role` |
| `fabric-edge-eks` | `AWS::EKS::Cluster` | `fabric-edge-vpc` (`1a`, `1b`) | ARN: `arn:aws:eks:ap-southeast-1:123456789012:cluster/fabric-edge-eks`<br>Cluster SG: `sg-022cfbdb0ba1358b5` |
| `fabric-core-eks` | `AWS::EKS::Cluster` | `fabric-core-vpc` (`1a`, `1b`) | ARN: `arn:aws:eks:ap-southeast-1:123456789012:cluster/fabric-core-eks`<br>Cluster SG: `sg-06715dfa0f671c216` |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-edge-eks` / `fabric-core-eks` | Cụm EKS và IAM Role |
| `Project` | `aws-eks-secure-network-fabric` | IAM Role và cả 2 EKS Clusters |
| `Environment` | `prod` | IAM Role và cả 2 EKS Clusters |
| `ManagedBy` | `manual` | Quản trị tài nguyên EKS thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 IAM Cluster Service Role

- **Trust Policy:** `eks.amazonaws.com` (Action: `sts:AssumeRole`)
- **Attached Managed Policy:** `arn:aws:iam::aws:policy/AmazonEKSClusterPolicy`

### 4.2 Cấu Hình Chi Tiết Cụm EKS

| Thuộc Tính | Cụm `fabric-edge-eks` | Cụm `fabric-core-eks` | Lý Do Thiết Kế |
| :--- | :--- | :--- | :--- |
| **Kubernetes Version** | `1.37` | `1.37` | Phiên bản runtime thực tế đã kiểm nghiệm. |
| **VPC Binding** | `fabric-edge-vpc` (`10.40.0.0/16`) | `fabric-core-vpc` (`10.50.0.0/16`) | Phân tách ranh giới mạng Ingress và Core Data. |
| **Subnets** | `fabric-edge-nodes-1a`, `1b` | `fabric-core-nodes-1a`, `1b` | ENI quản trị chỉ đặt trong private subnets. |
| **KMS Encryption** | `alias/fabric-edge-eks-secrets` | `alias/fabric-core-eks-secrets` | Envelope encryption cho Kubernetes Secrets etcd. |
| **Endpoint Access** | Private = `true`, Public = `true` (Restricted) | Private = `true`, Public = `true` (Restricted) | Worker nodes dùng Private API, Admin dùng Public IP allowlist. |
| **Logging** | Bật đủ 5 loại (`api`, `audit`, `authenticator`, `controllerManager`, `scheduler`) | Bật đủ 5 loại (`api`, `audit`, `authenticator`, `controllerManager`, `scheduler`) | Nhật ký audit và troubleshooting theo chuẩn SRE. |

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `02.01` (Subnets Private Nodes sẵn sàng tại Edge và Core VPCs).
- Phụ thuộc vào `02.06` (Private VPC Endpoints cho ECR, S3, STS, logs sẵn sàng).
- Phụ thuộc vào `03.01` (KMS CMK cho Secrets đã kích hoạt).
- Là điều kiện tiên quyết cho `03.03` (Managed Node Groups) và `03.04` (Pod Identity & Add-ons).

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng thái EKS Clusters** | `aws eks describe-cluster --name fabric-edge-eks` và `fabric-core-eks` | `cluster.status: ACTIVE` cho cả 2 cụm. |
| **KMS Encryption Config** | Kiểm tra trường `encryptionConfig[0].provider.keyArn` | Khớp đúng ARN của 2 khóa KMS CMK tại `03.01`. |
| **Control Plane Logging** | Kiểm tra trường `logging.clusterLogging[0].types` | Đủ 5 loại: `api`, `audit`, `authenticator`, `controllerManager`, `scheduler` (`enabled: true`). |
| **Kubeconfig Contexts** | `kubectl config get-contexts` | Xuất hiện 2 context `fabric-edge` và `fabric-core`. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo chi phí:** Mỗi EKS Control Plane tính phí $0.10 USD/giờ ($0.20 USD/giờ cho 2 cụm).
- **Quy trình Rollback:**
  ```bash
  # Xóa 2 cụm EKS (Sau khi đã dọn sạch Node Groups và Ingress/Workloads)
  aws eks delete-cluster --region ap-southeast-1 --name fabric-edge-eks
  aws eks delete-cluster --region ap-southeast-1 --name fabric-core-eks

  # Xóa IAM Cluster Role
  aws iam detach-role-policy --role-name fabric-eks-cluster-role --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
  aws iam delete-role --role-name fabric-eks-cluster-role
  ```
