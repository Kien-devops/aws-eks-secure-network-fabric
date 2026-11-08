# 03.05 — Đặc Tả Ma Trận Kubernetes NetworkPolicy Hoàn Chỉnh (Zero Trust)

> **Mã bài lab:** `03.05`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/03-eks/05-network-policy-verification.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả ma trận chính sách kiểm soát lưu lượng nội bộ Kubernetes NetworkPolicy theo mô hình Zero Trust (Default-Deny) áp dụng trên hai cụm EKS bằng cơ chế eBPF native của AWS VPC CNI, phân định rõ ràng quyền truy cập mạng của `edge-frontend` và `core-service`.

---

## 2. Tài Nguyên (Resources)

| Tên Tài Nguyên | Loại Resource | Namespace / Cụm Áp Dụng | Mô Tả Kỹ Thuật |
| :--- | :--- | :--- | :--- |
| `fabric-apps` | `k8s::Namespace` | `fabric-edge-eks`, `fabric-core-eks` | Namespace cô lập ứng dụng |
| `default-deny-all` | `networking.k8s.io/v1::NetworkPolicy` | `fabric-apps` (Cả 2 cụm) | Chặn toàn bộ Ingress và Egress mặc định |
| `allow-coredns-egress` | `networking.k8s.io/v1::NetworkPolicy` | `fabric-apps` (Cả 2 cụm) | Cho phép Egress tới CoreDNS (UDP/TCP 53) trong `kube-system` |
| `allow-pod-identity` | `networking.k8s.io/v1::NetworkPolicy` | `fabric-apps` (Cả 2 cụm) | Cho phép Pods gọi local link `169.254.170.23:80` lấy STS token |
| `edge-frontend-policy` | `networking.k8s.io/v1::NetworkPolicy` | `fabric-apps` (`fabric-edge-eks`) | Inbound TCP 8080 từ ALB, Outbound TCP 443/8082 tới Core NLB |
| `core-service-policy` | `networking.k8s.io/v1::NetworkPolicy` | `fabric-apps` (`fabric-core-eks`) | Inbound TCP 8082 từ Edge qua NLB, Outbound tới Aurora (5432), Redis (6379), SQS (443) |

---

## 3. Thẻ Định Danh & Metadata (Kubernetes Labels/Annotations)

*Lưu ý: Đối với tài nguyên thuần Kubernetes (NetworkPolicy, Namespace), bảng dưới đây định nghĩa Kubernetes Metadata `labels`/`annotations`, không phải thẻ gán trực tiếp trên hạ tầng AWS (AWS Resource Tags).*

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `default-deny-all` / `*-policy` | Kubernetes Metadata Labels & Annotations |
| `Project` | `aws-eks-secure-network-fabric` | Kubernetes Metadata Labels & Annotations |
| `Environment` | `prod` | Kubernetes Metadata Labels & Annotations |
| `ManagedBy` | `manual` | Quản trị Kubernetes Manifests thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Quy Tắc Default-Deny & CoreDNS Baseline

Áp dụng đồng bộ cho cả hai cụm `fabric-edge-eks` và `fabric-core-eks`:
- **`default-deny-all`:** `podSelector: {}`, `policyTypes: [Ingress, Egress]`. Không có ingress/egress rules, kích hoạt cô lập tuyệt đối.
- **`allow-coredns-egress`:** Cho phép `egress` tới namespace `kube-system` (pod có label `k8s-app: kube-dns`) qua cổng UDP 53 và TCP 53.
- **`allow-pod-identity`:** Áp dụng cho pods có nhãn `aws-credentials: pod-identity`, cho phép egress `ipBlock: 169.254.170.23/32` trên cổng TCP 80.

### 4.2 Ma Trận Luồng Cho Edge Workloads (`fabric-edge-eks`)

- **`edge-frontend-policy` (Pod Selector: `app: edge-frontend`):**
  - **Ingress:** Cho phép TCP 8080 từ Public Subnet CIDR (`10.40.0.0/23` - nơi ALB Ingress chuyển tiếp traffic).
  - **Egress:**
    - Cho phép TCP 443 và TCP 8082 tới Core VPC CIDR (`10.50.0.0/16`) thông qua TGW để kết nối tới Internal NLB của Core.

### 4.3 Ma Trận Luồng Cho Core Workloads (`fabric-core-eks`)

- **`core-service-policy` (Pod Selector: `app: core-service`):**
  - **Ingress:** Cho phép TCP 8082 từ Core Node Subnet CIDR (`10.50.8.0/21` - lưu lượng từ Internal NLB chuyển tới Pod).
  - **Egress:**
    - Cho phép TCP 5432 tới Data Subnets (`10.50.20.0/23` - Aurora PostgreSQL).
    - Cho phép TCP 6379 tới Data Subnets (`10.50.20.0/23` - ElastiCache Redis).
    - Cho phép TCP 443 tới VPCE Subnets (`10.50.30.0/23` - AWS SQS VPC Endpoint).

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `03.04`: Add-on `vpc-cni` phải kích hoạt `enableNetworkPolicy: "true"` và daemonset `aws-eks-nodeagent` phải ở trạng thái `Running`.
- Phụ thuộc vào `02.01`: Subnet CIDR của ALB (`10.40.0.0/23`), Core Nodes (`10.50.8.0/21`), Data (`10.50.20.0/23`), VPCE (`10.50.30.0/23`).
- Là rào chắn bảo mật tầng pod cho việc triển khai microservices tại [Module 04](../04-phan-bo-workloads/README.md).

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Xác thực Controller eBPF** | `kubectl get daemonset aws-node -n kube-system` | Container `aws-eks-nodeagent` chạy ổn định, nạp eBPF probe thành công. |
| **Danh sách NetworkPolicies Edge** | `kubectl get netpol -n fabric-apps --context fabric-edge` | Hiển thị: `default-deny-all`, `allow-coredns-egress`, `allow-pod-identity`, `edge-frontend-policy`. |
| **Danh sách NetworkPolicies Core** | `kubectl get netpol -n fabric-apps --context fabric-core` | Hiển thị: `default-deny-all`, `allow-coredns-egress`, `allow-pod-identity`, `core-service-policy`. |
| **Kiểm tra Finalizer eBPF** | `kubectl get netpol -n fabric-apps -o yaml` | Xuất hiện `finalizers: [networking.k8s.aws/resources]` trên tất cả policy. |
| **Kiểm thử cách ly (Deny check)** | Chạy pod kiểm thử không nhãn kết nối tới cổng không cho phép | Kết nối bị timeout hoàn toàn bởi eBPF kernel filter. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo gián đoạn dịch vụ:** Áp dụng NetworkPolicy sai pod selector hoặc thiếu cổng DNS 53 sẽ làm rớt toàn bộ traffic của ứng dụng. Luôn kiểm tra kỹ namespace và labels trước khi apply.
- **Quy trình Rollback:**
  ```bash
  # Lưu trạng thái trước khi sửa
  kubectl get networkpolicy -n fabric-apps --context fabric-edge -o yaml > edge-netpols-backup.yaml
  kubectl get networkpolicy -n fabric-apps --context fabric-core -o yaml > core-netpols-backup.yaml

  # Gỡ bỏ các NetworkPolicy bị lỗi
  kubectl delete networkpolicy edge-frontend-policy -n fabric-apps --context fabric-edge
  kubectl delete networkpolicy core-service-policy -n fabric-apps --context fabric-core
  ```
