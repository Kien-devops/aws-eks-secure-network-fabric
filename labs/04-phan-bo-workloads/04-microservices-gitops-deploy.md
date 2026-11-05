# 04.04 — Triển Khai Microservices (app3) Lên 2 Cụm EKS Qua GitOps (Argo CD)

> **Trạng thái:** Hướng dẫn triển khai ứng dụng bằng phương pháp GitOps chuẩn doanh nghiệp.  
> **Áp dụng cho:** Phân bổ các workloads từ repo `aws-eks-secure-network-fabric-app` lên cụm Edge EKS và Core EKS.

---

## 1. Mục Tiêu Kỹ Thuật

- Triển khai 5 microservices từ kho ứng dụng `app3` lên 2 cụm Kubernetes:
  - **Edge EKS (`fabric-edge-eks`):** `frontend`, `auth-service`.
  - **Core EKS (`fabric-core-eks`):** `order-service`, `inventory-service`, `payment-worker`.
- Sử dụng mã băm hình ảnh bất biến (**Immutable SHA Digest `@sha256:...`**) cho toàn bộ Deployments.
- Cấu hình Environment Variables kết nối tới Route 53 DNS nội bộ (`order.internal.fabric`), Aurora DB, Redis và SQS.
- Kiểm tra tính đúng đắn của chu trình xử lý đơn hàng (Atomic transaction + Idempotent consumer).

---

## 2. Bố Trí Thư Mục GitOps Trong Repo Ứng Dụng

Cấu trúc trong repository `aws-eks-secure-network-fabric-app`:
```text
gitops/
├── edge/
│   ├── 00-namespace.yaml
│   ├── 01-frontend-deployment.yaml
│   ├── 02-frontend-service.yaml
│   ├── 03-auth-deployment.yaml
│   ├── 04-auth-service.yaml
│   └── kustomization.yaml
└── core/
    ├── 00-namespace.yaml
    ├── 01-order-deployment.yaml
    ├── 02-order-service.yaml
    ├── 03-inventory-deployment.yaml
    ├── 04-payment-worker-deployment.yaml
    └── kustomization.yaml
```

---

## 3. Các Bước Triển Khai Chi Tiết

### Bước 1: Khởi Tạo Argo CD Application Cho Edge Cluster
Tạo tệp Application trỏ tới thư mục `gitops/edge`:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: fabric-edge-workloads
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/Kien-devops/aws-eks-secure-network-fabric-app.git
    targetRevision: main
    path: gitops/edge
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

---

### Bước 2: Khởi Tạo Argo CD Application Cho Core Cluster
Tạo tệp Application trỏ tới thư mục `gitops/core`:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: fabric-core-workloads
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/Kien-devops/aws-eks-secure-network-fabric-app.git
    targetRevision: main
    path: gitops/core
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

---

### Bước 3: Cấu Hình Biến Môi Trường (ConfigMap & Secrets)
- **Trong `frontend-deployment.yaml`:**
  - `BACKEND_URL`: `https://order.internal.fabric`
  - `AUTH_SERVICE_URL`: `http://auth-service.default.svc.cluster.local:8080`
- **Trong `order-deployment.yaml`:**
  - `DB_HOST`: Địa chỉ Endpoint của Aurora Serverless v2.
  - `REDIS_HOST`: Địa chỉ Primary Endpoint của ElastiCache Redis.
  - `SQS_QUEUE_URL`: URL của `fabric-order-events.fifo`.

---

## 4. Xác Minh (Verification)

Kiểm tra trạng thái Pods trên cả 2 cluster:
```bash
# Trên Edge Cluster
kubectl get pods -l app=frontend
kubectl get pods -l app=auth-service

# Trên Core Cluster
kubectl get pods -l app=order-service
kubectl get pods -l app=inventory-service
kubectl get pods -l app=payment-worker
```
> Kết quả: Toàn bộ Pods đều ở trạng thái `Running` (`1/1 Ready`).

---

## 5. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Argo CD đồng bộ thành công cả 2 ứng dụng Edge và Core (`Status: Synced`, `Health: Healthy`).
- [ ] 100% hình ảnh container được ghim bằng SHA digest `@sha256:...`.
- [ ] Microservice `frontend` kết nối được tới `order.internal.fabric` qua cổng 443.

