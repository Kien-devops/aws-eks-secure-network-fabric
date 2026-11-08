# 03.04 — Đặc Tả EKS Pod Identity & Cài Đặt Managed Add-ons

> **Mã bài lab:** `03.04`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/03-eks/04-addons-status.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả cấu hình phân quyền AWS IAM cho Pods thông qua chuẩn EKS Pod Identity (loại bỏ OIDC/IRSA phức tạp) và triển khai các EKS Managed Add-ons cốt lõi kèm cờ Native NetworkPolicy trên cả hai cụm EKS.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Vị Trí / Cụm Áp Dụng | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-aws-lb-controller-role` | `AWS::IAM::Role` | Global (IAM) | `arn:aws:iam::123456789012:role/fabric-aws-lb-controller-role` |
| `fabric-ebs-csi-driver-role` | `AWS::IAM::Role` | Global (IAM) | `arn:aws:iam::123456789012:role/fabric-ebs-csi-driver-role` |
| `vpc-cni` | `AWS::EKS::Addon` | `fabric-edge-eks`, `fabric-core-eks` | Phiên bản `v1.22.4-eksbuild.10` |
| `eks-pod-identity-agent` | `AWS::EKS::Addon` | `fabric-edge-eks`, `fabric-core-eks` | Phiên bản `v1.4.1-eksbuild.3` |
| `coredns` | `AWS::EKS::Addon` | `fabric-edge-eks`, `fabric-core-eks` | Phiên bản `v1.14.7-eksbuild.22` |
| `kube-proxy` | `AWS::EKS::Addon` | `fabric-edge-eks`, `fabric-core-eks` | Phiên bản `v1.37.0-eksbuild.32` |
| `aws-ebs-csi-driver` | `AWS::EKS::Addon` | `fabric-edge-eks`, `fabric-core-eks` | Phiên bản `v1.67.2-eksbuild.1` |
| Pod Identity Assoc (Edge LB) | `AWS::EKS::PodIdentityAssociation` | `fabric-edge-eks` (`kube-system/aws-load-balancer-controller`) | `a-pzqcm9dikmbnkjczp` |
| Pod Identity Assoc (Edge CSI) | `AWS::EKS::PodIdentityAssociation` | `fabric-edge-eks` (`kube-system/ebs-csi-controller-sa`) | `a-jemn2vtszgyyw9nlc` |
| Pod Identity Assoc (Core CSI) | `AWS::EKS::PodIdentityAssociation` | `fabric-core-eks` (`kube-system/ebs-csi-controller-sa`) | `a-rqgv9gfbniu2xc4td` |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-*-role` | Toàn bộ IAM Roles và Add-ons hỗ trợ tag |
| `Project` | `aws-eks-secure-network-fabric` | Toàn bộ IAM Roles và Add-ons |
| `Environment` | `prod` | Toàn bộ IAM Roles và Add-ons |
| `ManagedBy` | `manual` | Quản trị định danh và tiện ích mở rộng thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 IAM Trust Policy Cho EKS Pod Identity

- **Trusted Service Principal:** `pods.eks.amazonaws.com`
- **Actions:** `sts:AssumeRole`, `sts:TagSession`
- **Gán quyền chi tiết:**
  - `fabric-aws-lb-controller-role`: Gán policy khách hàng quản trị `AWSLoadBalancerControllerIAMPolicy`.
  - `fabric-ebs-csi-driver-role`: Gán AWS Managed Policy `AmazonEBSCSIDriverPolicy`.

### 4.2 Cấu Hình Kỹ Thuật Managed Add-ons

| Tên Add-on | Configuration Values (JSON) | Mục Đích Thiết Kế |
| :--- | :--- | :--- |
| **`vpc-cni`** | `{"enableNetworkPolicy": "true"}` | Bật tính năng Native NetworkPolicy của Amazon VPC CNI mà không cần cài Calico/Cilium ngoài. |
| **`eks-pod-identity-agent`** | `{}` (Mặc định) | Chạy DaemonSet cung cấp local token service cho Pods giao tiếp STS. |
| **`coredns`** | `{}` (Mặc định) | Phân giải DNS nội bộ cụm và chuyển tiếp DNS VPC. |
| **`kube-proxy`** | `{}` (Mặc định) | Quản lý iptables định tuyến Service ClusterIP. |
| **`aws-ebs-csi-driver`** | `{}` (Mặc định) | Hỗ trợ cấp phát Persistent Volumes cho các workloads stateful. |

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `03.02` (EKS Cluster `ACTIVE`) và `03.03` (Worker Nodes `Ready`).
- Phụ thuộc vào `02.06` (`eks-auth` Interface VPC Endpoint phải hoạt động trên cả hai VPC để Pod Identity Agent kết nối API EKS).
- Là điều kiện tiên quyết bắt buộc trước `03.05` (K8s NetworkPolicy Baseline).

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng thái 5 Add-ons** | `aws eks list-addons --cluster-name <Cluster>` | Tất cả add-on hiển thị trạng thái `ACTIVE`. |
| **NetworkPolicy Flag** | `aws eks describe-addon --cluster-name <Cluster> --addon-name vpc-cni` | Thuộc tính `configurationValues` chứa `"enableNetworkPolicy": "true"`. |
| **Pod Identity Associations** | `aws eks list-pod-identity-associations --cluster-name <Cluster>` | Hiển thị đủ các liên kết ServiceAccount và IAM Role tương ứng. |
| **DaemonSet Pods** | `kubectl get pods -n kube-system -l app.kubernetes.io/name=eks-pod-identity-agent` | Tất cả pods chạy ở trạng thái `Running` (1 pod per node). |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo tính tương thích:** Khi nâng cấp `vpc-cni`, luôn giữ nguyên cấu hình `enableNetworkPolicy: true`. Nếu mất cờ này, toàn bộ NetworkPolicy của cụm tại `03.05` sẽ bị vô hiệu hóa ngầm mà không có cảnh báo lỗi.
- **Quy trình Rollback:**
  ```bash
  # Xóa Pod Identity Associations
  aws eks delete-pod-identity-association --region ap-southeast-1 --cluster-name fabric-edge-eks --association-id a-pzqcm9dikmbnkjczp
  aws eks delete-pod-identity-association --region ap-southeast-1 --cluster-name fabric-edge-eks --association-id a-jemn2vtszgyyw9nlc
  aws eks delete-pod-identity-association --region ap-southeast-1 --cluster-name fabric-core-eks --association-id a-rqgv9gfbniu2xc4td

  # Xóa IAM Roles
  aws iam delete-role --role-name fabric-aws-lb-controller-role
  aws iam delete-role --role-name fabric-ebs-csi-driver-role
  ```
