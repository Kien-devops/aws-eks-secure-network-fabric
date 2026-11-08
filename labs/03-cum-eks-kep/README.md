# Module 03: Cụm Kubernetes EKS Kép (Dual EKS Clusters)

Module này cung cấp các đặc tả tài nguyên triển khai 2 cụm Amazon EKS riêng tư (Private Clusters) trên phiên bản Kubernetes 1.37, mã hóa phong bì bằng AWS KMS Secrets, kết nối định danh thông qua EKS Pod Identity và kiểm soát Zero Trust bằng AWS VPC CNI NetworkPolicy.

---

## 1. Thứ Tự Phụ Thuộc (Dependency Tree)

```text
03.01 (AWS KMS CMK: Edge & Core Keys)
  │
  └──> 03.02 (Dual EKS Clusters: fabric-edge-eks & fabric-core-eks)
         │
         └──> 03.03 (Managed Node Groups: fabric-edge-ng-1 & fabric-core-ng-1)
                │
                └──> 03.04 (EKS Pod Identity & Managed Add-ons: VPC CNI, EBS CSI)
                       │
                       └──> 03.05 (K8s NetworkPolicy Baseline: Zero Trust eBPF)
```

---

## 2. Danh Mục Tài Nguyên (Resource Catalog)

| Tài Nguyên | Loại Resource | Số Lượng | Ghi Chú Kỹ Thuật |
| :--- | :--- | :---: | :--- |
| **KMS CMK** | `AWS::KMS::Key` | 2 | `alias/fabric-edge-eks-secrets`, `alias/fabric-core-eks-secrets` (Key rotation: true) |
| **IAM Cluster Role** | `AWS::IAM::Role` | 1 | `fabric-eks-cluster-role` (`AmazonEKSClusterPolicy`) |
| **EKS Clusters** | `AWS::EKS::Cluster` | 2 | `fabric-edge-eks`, `fabric-core-eks` (v1.37, Private + Allowlist Public API) |
| **IAM Node Role** | `AWS::IAM::Role` | 1 | `fabric-eks-node-role` (WorkerNode, CNI, ECRReadOnly, SSM) |
| **Node Groups** | `AWS::EKS::Nodegroup` | 2 | `fabric-edge-ng-1`, `fabric-core-ng-1` (t3.medium Spot, AL2023, 2 nodes per cluster) |
| **EKS Add-ons** | `AWS::EKS::Addon` | 10 | `vpc-cni`, `eks-pod-identity-agent`, `coredns`, `kube-proxy`, `aws-ebs-csi-driver` trên cả 2 cụm |
| **Pod Identity Assoc** | `AWS::EKS::PodIdentityAssociation` | 3 | Gắn role cho AWS LB Controller và EBS CSI Driver |
| **K8s NetworkPolicy** | `networking.k8s.io/v1::NetworkPolicy` | 6 | `default-deny-all`, `allow-coredns-egress`, `allow-pod-identity`, policies cho `edge-frontend` và `core-service` |

---

## 3. Danh Sách 5 Bài Lab Đặc Tả Chi Tiết

| Mã Lab | Tên Đặc Tả & Nội Dung Trọng Tâm | Trạng Thái | File Đặc Tả |
|---|---|:---:|---|
| **03.01** | **Tạo Khóa KMS CMK:** Mã hóa Kubernetes Secrets độc lập cho Edge và Core. | `RUNTIME_PASS` | [01-kms-encryption-keys.md](01-kms-encryption-keys.md) |
| **03.02** | **Khởi Tạo Cụm EKS Kép 1.37:** Cụm riêng tư `fabric-edge-eks` và `fabric-core-eks`. | `RUNTIME_PASS` | [02-dual-eks-clusters.md](02-dual-eks-clusters.md) |
| **03.03** | **Managed Node Groups:** Worker nodes AL2023 phân bố đa AZ, cấu hình SSM. | `RUNTIME_PASS` | [03-managed-node-groups.md](03-managed-node-groups.md) |
| **03.04** | **EKS Pod Identity & Add-ons:** Pod Identity Agent, VPC CNI, EBS CSI Driver. | `RUNTIME_PASS` | [04-eks-pod-identity-and-addons.md](04-eks-pod-identity-and-addons.md) |
| **03.05** | **K8s NetworkPolicy Baseline:** Ma trận Zero Trust pod-to-pod, default deny qua eBPF. | `RUNTIME_PASS` | [05-k8s-network-policy-baseline.md](05-k8s-network-policy-baseline.md) |
