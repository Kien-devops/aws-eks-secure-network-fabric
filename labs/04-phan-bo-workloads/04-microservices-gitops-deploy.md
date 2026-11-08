# 04.04 — Đặc Tả Triển Khai Microservices & Đồng Bộ GitOps (Argo CD)

> **Mã bài lab:** `04.04`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/04-workloads/04-gitops-pods-status.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả tài nguyên và cấu hình phân phối 2 microservices (`edge-frontend` trên cụm Edge và `core-service` trên cụm Core) theo quy trình GitOps tự động hóa thông qua Argo CD, tích hợp xác thực IAM không mật khẩu bằng EKS Pod Identity và mã hóa TLS toàn trình qua Transit Gateway.

---

## 2. Tài Nguyên (Resources)

| Tên Tài Nguyên | Loại Resource | Vị Trí / Cụm Áp Dụng | Runtime ID / URI |
| :--- | :--- | :--- | :--- |
| `argocd` | `k8s::Namespace` | `fabric-edge-eks`, `fabric-core-eks` | Quản trị triển khai GitOps |
| `fabric-edge-apps` | `argoproj.io/v1alpha1::Application` | `fabric-edge-eks` | Đồng bộ thư mục `k8s/edge` |
| `fabric-core-apps` | `argoproj.io/v1alpha1::Application` | `fabric-core-eks` | Đồng bộ thư mục `k8s/core` |
| `edge-frontend` | `k8s::Deployment` | `fabric-edge-eks` (`fabric-apps`) | Image: `123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-edge-frontend:latest` |
| `core-service` | `k8s::Deployment` | `fabric-core-eks` (`fabric-apps`) | Image: `123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-core-service:latest` |
| `fabric-core-service-role` | `AWS::IAM::Role` | Global (IAM) | Role cho Pod Identity (`core-service`) |

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-*-app` / `fabric-core-service-role` | Toàn bộ tài nguyên quản trị và IAM |
| `Project` | `aws-eks-secure-network-fabric` | Bắt buộc trên toàn bộ tài nguyên |
| `Environment` | `prod` | Phân vùng môi trường chính thức |
| `ManagedBy` | `manual` | Quản lý quy trình triển khai thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Cấu Hình Microservices Baseline (2 Dịch Vụ)

| Dịch Vụ | Cụm Triển Khai | Replicas | Port / Giao Thức | Health Check | Quyền Truy Cập IAM / Mạng |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **`edge-frontend`** | `fabric-edge-eks` | 2 | `TCP 8080` (HTTP) | `/healthz` | Nhận traffic từ ALB Ingress, gọi Egress tới `https://core.fabric.internal:443`. |
| **`core-service`** | `fabric-core-eks` | 2 | `TCP 8082` (HTTPS) | `/healthz` | Nhận HTTPS từ NLB, tích hợp consumer SQS, gọi DB PostgreSQL 5432, Redis 6379, SQS 443. |

### 4.2 Cấu Hình Tự Động Hóa Argo CD Application

- **Edge Application (`fabric-edge-apps`):**
  - Source Repo: `aws-eks-secure-network-fabric-app.git` (Path: `k8s/edge`)
  - Target: `https://kubernetes.default.svc` (Namespace: `fabric-apps`)
  - Sync Policy: `Automated` (`Prune: true`, `SelfHeal: true`).
- **Core Application (`fabric-core-apps`):**
  - Source Repo: `aws-eks-secure-network-fabric-app.git` (Path: `k8s/core`)
  - Target: `https://kubernetes.default.svc` (Namespace: `fabric-apps`)
  - Sync Policy: `Automated` (`Prune: true`, `SelfHeal: true`).

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `03.02`, `03.03`: Cả hai cụm EKS có các worker nodes sẵn sàng.
- Phụ thuộc vào `03.04`, `03.05`: Pod Identity Agent và ma trận NetworkPolicy đã kích hoạt.
- Phụ thuộc vào `04.01`: Cụm Aurora PostgreSQL, ElastiCache Redis và queue SQS sẵn sàng.
- Phụ thuộc vào `04.02`, `04.03`: Route 53 PHZ `fabric.internal` và Internal NLB đã hoạt động.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng thái Pods Edge** | `kubectl get pods -n fabric-apps --context fabric-edge` | `edge-frontend` đạt trạng thái `2/2 Running`. |
| **Trạng thái Pods Core** | `kubectl get pods -n fabric-apps --context fabric-core` | `core-service` đạt trạng thái `2/2 Running`. |
| **Secret Retrieval Log** | `kubectl logs -n fabric-apps -l app=core-service --context fabric-core` | Không chứa lỗi xác thực; nạp DB creds và Redis token từ Secrets Manager thành công. |
| **Kết nối East-West liên cụm** | `kubectl exec -n fabric-apps <edge-pod> -- curl -s https://core.fabric.internal:443/healthz` | Trả về mã HTTP `200 OK`. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo tính bất biến (Self-Healing):** Khi Argo CD bật `selfHeal: true`, mọi can thiệp thủ công `kubectl edit` hay `kubectl rollout undo` sẽ bị ghi đè tự động.
- **Quy trình Rollback:**
  ```bash
  # Hoàn tác trên repository ứng dụng bằng git revert
  cd aws-eks-secure-network-fabric-app
  git revert HEAD --no-edit
  git push origin main
  # Argo CD sẽ tự động đồng bộ về commit trước đó
  ```
