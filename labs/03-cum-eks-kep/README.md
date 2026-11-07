# Module 03: Cụm Kubernetes EKS Kép (Dual EKS Clusters 1.37)

Module này hướng dẫn triển khai 2 cụm Amazon EKS riêng tư (Private Clusters) trên phiên bản Kubernetes **1.37** mới nhất, mã hóa bằng AWS KMS Secrets, kết nối thông qua EKS Pod Identity và kiểm soát Zero Trust bằng AWS VPC CNI NetworkPolicy.

## Danh Sách Bài Lab

| Mã Lab | Tên Bài Lab & Nội Dung Trọng Tâm | Trạng Thái | File Hướng Dẫn |
|---|---|:---:|---|
| **03.01** | **Tạo Khóa KMS CMK:** Mã hóa Kubernetes Secrets độc lập cho Edge và Core. | `RUNTIME_PASS` | [01-kms-encryption-keys.md](01-kms-encryption-keys.md) |
| **03.02** | **Khởi Tạo Cụm EKS Kép 1.37:** Cụm riêng tư `fabric-edge-eks` và `fabric-core-eks`. | `RUNTIME_PASS` | [02-dual-eks-clusters.md](02-dual-eks-clusters.md) |
| **03.03** | **Managed Node Groups:** Worker nodes AL2023 phân bố đa AZ, cấu hình SSM. | `RUNTIME_PASS` | [03-managed-node-groups.md](03-managed-node-groups.md) |
| **03.04** | **EKS Pod Identity & Add-ons:** Pod Identity Agent, VPC CNI, EBS CSI Driver. | `RUNTIME_PASS` | [04-eks-pod-identity-and-addons.md](04-eks-pod-identity-and-addons.md) |
| **03.05** | **K8s NetworkPolicy Baseline:** Ma trận Zero Trust pod-to-pod, default deny. | `DRAFT` | [05-k8s-network-policy-baseline.md](05-k8s-network-policy-baseline.md) |
