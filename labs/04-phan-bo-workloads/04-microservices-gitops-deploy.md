# 04.04 — Triển Khai Microservices & Đồng Bộ GitOps (Argo CD)

> **Mã bài lab:** `04.04`  
> **Trạng thái:** `COMPLETED`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab từ [04.01](01-database-and-cache-setup.md) đến [04.03](03-core-internal-nlb.md).
- Hai cụm EKS `fabric-edge-eks` và `fabric-core-eks` có các node `Ready` và đầy đủ add-ons mạng (VPC CNI, CoreDNS, kube-proxy, EKS Pod Identity Agent).
- **Trạng thái Repo Application (`aws-eks-secure-network-fabric-app`):**
  - Đã có đầy đủ mã nguồn Go, Unit Tests, Dockerfiles đa tầng (multi-stage build), CI/CD GitHub Actions (`ci-edge-frontend.yml`, `ci-core-service.yml`).
  - Đã build và push immutable images lên Amazon ECR:
    - `fabric-edge-frontend` (`123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-edge-frontend:latest`)
    - `fabric-core-service` (`123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-core-service:latest`)
  - Kustomize manifests sẵn sàng tại `k8s/edge` và `k8s/core`.
- **Contract & Port Allocation:**
  - `edge-frontend`: HTTP port `8080`, Health check path `/healthz`.
  - `core-service`: HTTPS port `8082`, Health check path `/healthz` (tích hợp internal TLS cert SAN `core.fabric.internal`).
  - Giao tiếp liên cụm: `edge-frontend` kết nối tới `https://core.fabric.internal:443` thông qua Core Internal NLB qua Transit Gateway.
- **Bảo mật & Phân quyền IAM (Zero Plaintext Secrets):**
  - Pod Identity Role `fabric-core-order-service-role` liên kết với ServiceAccount `order-service` tại namespace `fabric-apps` trên `fabric-core-eks`.
  - Không lưu credentials trong K8s Secret plaintext; Pod tự động truy vấn AWS Secrets Manager (`rds!cluster-*`, `fabric-core-redis-auth`) và SQS qua Interface VPC Endpoints.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Bài lab tương tác với cụm EKS thông qua Argo CD và `kubectl`, đồng thời quan sát tài nguyên trên AWS EKS Console:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster",
        "eks:AccessKubernetesApi",
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD. Không phát sinh chi phí AWS ngoài các node EC2 và cụm EKS đã chạy.
- **Cảnh báo phân tách ranh giới tin cậy (Workload Placement):**
  - Cụm **Edge EKS (`fabric-edge-eks`)**: CHỈ CHỨA lớp giao diện và gateway (`edge-frontend`).
  - Cụm **Core EKS (`fabric-core-eks`)**: CHỈ CHỨA lớp backend nghiệp vụ và dữ liệu (`core-service` với order logic, payment SQS worker, kết nối Aurora PostgreSQL và ElastiCache Redis).
  - Tuyệt đối không deploy dịch vụ dữ liệu/backend vào cụm Edge nhằm bảo vệ ranh giới bảo mật DMZ.
- **Cảnh báo tính bất biến (Immutable Digests / Tags):** Trong môi trường production, mọi image deploy qua GitOps nên ghim theo immutable tag hoặc image digest `@sha256:...` để bảo vệ chuỗi cung ứng phần mềm.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console & GitOps (Console Walkthrough)

### Bước 1: Cài Đặt Argo CD Trên Cụm Quản Trị
Chọn **Argo CD riêng biệt trên từng cluster** cho mô hình độc lập (mỗi Application trỏ về `https://kubernetes.default.svc` của chính cluster đó):

1. **Cài đặt Argo CD trên Edge EKS:**
   ```bash
   aws eks update-kubeconfig --region ap-southeast-1 --name fabric-edge-eks --alias fabric-edge
   kubectl create namespace argocd --context fabric-edge
   kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.10.4/manifests/install.yaml --context fabric-edge
   kubectl rollout status deployment argocd-server -n argocd --context fabric-edge
   ```
2. **Mở cổng và đăng nhập Argo CD Edge:**
   ```bash
   kubectl port-forward svc/argocd-server -n argocd 8080:443 --context fabric-edge
   # Lấy mật khẩu ban đầu
   kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' --context fabric-edge | base64 -d
   ```
3. **Cài đặt Argo CD trên Core EKS:**
   ```bash
   aws eks update-kubeconfig --region ap-southeast-1 --name fabric-core-eks --alias fabric-core
   kubectl create namespace argocd --context fabric-core
   kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.10.4/manifests/install.yaml --context fabric-core
   kubectl rollout status deployment argocd-server -n argocd --context fabric-core
   ```
4. **Mở cổng và đăng nhập Argo CD Core:**
   ```bash
   kubectl port-forward svc/argocd-server -n argocd 8081:443 --context fabric-core
   kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' --context fabric-core | base64 -d
   ```

---

### Bước 2: Khởi Tạo Ứng Dụng GitOps Trên Giao Diện Argo CD Web UI

1. **Tạo Application cho Edge Workloads (`fabric-edge-apps`):**
   - Mở giao diện Web Argo CD Edge (`https://localhost:8080`).
   - Nhấp **+ NEW APP**:
     - **Application Name:** `fabric-edge-apps`
     - **Project:** `default`
     - **Sync Policy:** `Automatic` (chọn `Prune Resources` và `Self Heal`).
     - **Source:**
       - Repository URL: `https://github.com/Kien-devops/aws-eks-secure-network-fabric-app.git`
       - Revision: `main` (hoặc commit SHA ổn định)
       - Path: `k8s/edge`
     - **Destination:**
       - Cluster URL: `https://kubernetes.default.svc`
       - Namespace: `fabric-apps`
   - Nhấp **CREATE** -> Chọn **SYNC** để đồng bộ `edge-frontend`.

2. **Tạo Application cho Core Workloads (`fabric-core-apps`):**
   - Mở giao diện Web Argo CD Core (`https://localhost:8081`).
   - Nhấp **+ NEW APP**:
     - **Application Name:** `fabric-core-apps`
     - **Project:** `default`
     - **Sync Policy:** `Automatic` (chọn `Prune Resources` và `Self Heal`).
     - **Source:**
       - Repository URL: `https://github.com/Kien-devops/aws-eks-secure-network-fabric-app.git`
       - Revision: `main`
       - Path: `k8s/core`
     - **Destination:**
       - Cluster URL: `https://kubernetes.default.svc`
       - Namespace: `fabric-apps`
   - Nhấp **CREATE** -> Chọn **SYNC** để đồng bộ `core-service`, `ServiceAccount`, `ConfigMap` và `core-internal-nlb`.

---

### Bước 3: Quan Sát Trạng Thái Triển Khai Trên AWS EKS Console

1. Mở **Amazon EKS Console** tại Region Singapore `ap-southeast-1`.
2. Chọn cụm `fabric-edge-eks` -> Chọn tab **Workloads**:
   - Xác nhận trong namespace `fabric-apps` có Deployment:
     - `edge-frontend` (Trạng thái: Active, Pods: 2/2 Ready).
3. Chọn cụm `fabric-core-eks` -> Chọn tab **Workloads**:
   - Xác nhận trong namespace `fabric-apps` có Deployment:
     - `core-service` (Trạng thái: Active, Pods: 2/2 Ready).
4. Kiểm tra tab **Details & Networking** của các Pods:
   - Xác nhận Pod IPs nằm chính xác trong dải Private Node Subnet của VPC CNI (`10.50.x.x`).
   - Pod `core-service` gắn nhãn `aws-credentials: pod-identity` và sử dụng `serviceAccountName: order-service`.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái triển khai và kiểm thử kết nối toàn trình xuyên Transit Gateway:

```bash
# 1. Liệt kê pods trên cụm Edge
kubectl get pods -n fabric-apps -o wide --context fabric-edge

# 2. Liệt kê pods trên cụm Core
kubectl get pods -n fabric-apps -o wide --context fabric-core

# 3. Kiểm tra log khởi động Core Service (xác nhận lấy secret từ AWS Secrets Manager qua Pod Identity)
kubectl logs -n fabric-apps -l app=order-service --tail=20 --context fabric-core

# 4. Kiểm tra Target Health của Core Internal NLB
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups --query "TargetGroups[?contains(TargetGroupName, 'coreinte')].TargetGroupArn" --output text --region ap-southeast-1) \
  --region ap-southeast-1

# 5. Kiểm thử kết nối HTTPS từ Pod Edge Frontend sang Core Backend qua NLB và Route 53 Private Hosted Zone
EDGE_POD=$(kubectl get pods -n fabric-apps -l app=frontend -o jsonpath='{.items[0].metadata.name}' --context fabric-edge)

# Gọi endpoint /healthz (Core Service HTTPS qua cổng 443 của NLB)
kubectl exec -it $EDGE_POD -n fabric-apps --context fabric-edge -- \
  curl -s -w "\nHTTP_STATUS: %{http_code}\n" https://core.fabric.internal:443/healthz

# Tạo đơn hàng mẫu từ Edge sang Core
kubectl exec -it $EDGE_POD -n fabric-apps --context fabric-edge -- \
  curl -s -X POST https://core.fabric.internal:443/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"cust-101","items":[{"sku":"SKU-A1","quantity":2,"unit_price":49.99}]}'
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Hoàn tác deployment nếu ứng dụng phát sinh lỗi:
```bash
# 1. Revert commit trên branch main của repository app:
cd aws-eks-secure-network-fabric-app
git revert HEAD --no-edit
git push origin main

# 2. Argo CD tự động phát hiện commit mới và sync về trạng thái ổn định trước đó.
# Lưu ý: Không chạy lệnh 'kubectl rollout undo' khi chế độ selfHeal đang bật, 
# vì Argo CD sẽ lập tức reconcile lại theo manifest trong Git.
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures) được lưu trữ tại:
`evidence/04-workloads/04-gitops-pods-status.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [x] Cả 2 microservices (`edge-frontend` và `core-service`) đạt trạng thái `2/2 Running` trên đúng cụm EKS quy định (`fabric-edge-eks` và `fabric-core-eks`).
- [x] Không có hiện tượng Pod rơi vào trạng thái `CrashLoopBackOff` hay `ImagePullBackOff`.
- [x] Pod `core-service` nạp thành công DB password và Redis auth token từ AWS Secrets Manager thông qua EKS Pod Identity mà không dùng plaintext Secret.
- [x] Target Health của Core Internal NLB báo trạng thái `healthy` trên cổng 8082.
- [x] `edge-frontend` kết nối thành công sang `https://core.fabric.internal:443` thông qua Route 53 và NLB qua Transit Gateway (HTTP 200).
- [x] Giao diện Argo CD Console hiển thị trạng thái `Synced` và `Healthy`.
