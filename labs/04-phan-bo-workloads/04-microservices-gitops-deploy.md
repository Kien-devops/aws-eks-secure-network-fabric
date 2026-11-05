# 04.04 — Triển Khai Microservices & Đồng Bộ GitOps (Argo CD)

> **Mã bài lab:** `04.04`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab từ [04.01](01-database-and-cache-setup.md) đến [04.03](03-core-internal-nlb.md).
- Hai cụm EKS `fabric-edge-eks` và `fabric-core-eks` có các node `Ready` và đầy đủ add-ons.
- Repository ứng dụng [`aws-eks-secure-network-fabric-app`](https://github.com/Kien-devops/aws-eks-secure-network-fabric-app) đã có sẵn Kustomize manifests cho 5 microservices (`frontend`, `auth`, `order`, `inventory`, `payment`).

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
        "eks:AccessKubernetesApi"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD. Không phát sinh chi phí AWS ngoài các node EC2 đã chạy.
- **Cảnh báo phân tách ranh giới tin cậy (Workload Placement):**
  - Cụm **Edge EKS** CHỈ CHỨA: `frontend` và `auth-service`.
  - Cụm **Core EKS** CHỈ CHỨA: `order-service`, `inventory-service`, `payment-worker`.
  - Tuyệt đối không deploy dịch vụ xử lý dữ liệu sang cụm Edge để đảm bảo ranh giới an ninh DMZ.
- **Cảnh báo tính bất biến (Immutable Digests):** Mọi image deploy bắt buộc phải dùng tag digest dạng `@sha256:...`, không dùng tag nổi `:latest` để tránh lỗ hổng chuỗi cung ứng.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console & GitOps (Console Walkthrough)

### Bước 1: Cài Đặt Argo CD Trên Cụm Quản Trị
1. Chuyển context sang cụm `fabric-edge-eks` (hoặc cụm quản trị):
   ```bash
   aws eks update-kubeconfig --region ap-southeast-1 --name fabric-edge-eks --alias fabric-edge
   kubectl create namespace argocd
   kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
   kubectl rollout status deployment argocd-server -n argocd
   ```
2. Mở cổng truy cập giao diện Web của Argo CD Console:
   ```bash
   kubectl port-forward svc/argocd-server -n argocd 8080:443
   ```
3. Lấy mật khẩu đăng nhập tài khoản `admin`:
   ```bash
   kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | [System.Convert]::FromBase64String($_) # hoặc base64 -d
   ```
4. Mở trình duyệt web, truy cập `https://localhost:8080`. Đăng nhập với Username: `admin` và mật khẩu vừa lấy.

---

### Bước 2: Khởi Tạo Ứng Dụng GitOps Trên Giao Diện Argo CD Web UI
1. **Tạo Application cho Edge Workloads (`fabric-edge-apps`):**
   - Tại giao diện Argo CD Console, nhấp nút **+ NEW APP** ở góc trên bên trái.
   - **General:**
     - Application Name: `fabric-edge-apps`
     - Project: `default`
     - Sync Policy: Chọn **Automatic** (Kèm theo `Prune Resources` và `Self Heal`).
   - **Source:**
     - Repository URL: `https://github.com/Kien-devops/aws-eks-secure-network-fabric-app.git`
     - Revision: `main` (hoặc branch chỉ định)
     - Path: `gitops/overlays/edge-prod`
   - **Destination:**
     - Cluster URL: `https://kubernetes.default.svc`
     - Namespace: `fabric-apps`
   - Nhấp nút **CREATE** ở đầu trang.
   - Nhấp vào card `fabric-edge-apps` -> Nhấp **SYNC** -> Nhấp **SYNCHRONIZE** để kích hoạt triển khai `frontend` và `auth-service`.

2. **Tạo Application cho Core Workloads (`fabric-core-apps`):**
   - Chuyển context sang `fabric-core` và tạo tương tự, hoặc sử dụng Kustomize deploy trực tiếp:
     ```bash
     kubectl apply -k https://github.com/Kien-devops/aws-eks-secure-network-fabric-app.git/gitops/overlays/core-prod --context fabric-core
     ```

---

### Bước 3: Quan Sát Trạng Thái Triển Khai Trên AWS EKS Console
1. Mở **Amazon EKS Console** tại Region Singapore `ap-southeast-1`.
2. Chọn cụm `fabric-edge-eks` -> Chọn tab **Workloads**:
   - Xác nhận trong namespace `fabric-apps` có 2 Deployments:
     - `frontend` (Trạng thái: Active, Pods: 2/2 Ready).
     - `auth-service` (Trạng thái: Active, Pods: 2/2 Ready).
3. Chọn cụm `fabric-core-eks` -> Tab **Workloads**:
   - Xác nhận có 3 Deployments:
     - `order-service` (Active, Pods: 2/2 Ready).
     - `inventory-service` (Active, Pods: 2/2 Ready).
     - `payment-worker` (Active, Pods: 2/2 Ready).
4. Nhấp vào Pod bất kỳ -> Kiểm tra tab **Details**:
   - Xác nhận **IP address** của Pod được cấp phát trực tiếp từ dải mạng Private Node Subnet của VPC CNI.
   - Xác nhận **Image URI** sử dụng mã băm bất biến `@sha256:...`.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra danh sách Pods và kiểm thử kết nối nội bộ giữa Edge và Core:
```bash
# 1. Liệt kê pods trên cụm Edge
kubectl get pods -n fabric-apps -o wide --context fabric-edge

# 2. Liệt kê pods trên cụm Core
kubectl get pods -n fabric-apps -o wide --context fabric-core

# 3. Kiểm thử kết nối HTTP từ frontend pod sang order-service qua Route 53 và Core Internal NLB
FRONTEND_POD=$(kubectl get pods -n fabric-apps -l app=frontend -o jsonpath='{.items[0].metadata.name}' --context fabric-edge)
kubectl exec -it $FRONTEND_POD -n fabric-apps --context fabric-edge -- \
  curl -s -o /dev/null -w "%{http_code}\n" https://core.fabric.internal/api/v1/orders/health -k
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Hoàn tác deployment nếu ứng dụng phát sinh lỗi:
```bash
kubectl rollout undo deployment/frontend -n fabric-apps --context fabric-edge
kubectl rollout undo deployment/order-service -n fabric-apps --context fabric-core
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/04-workloads/04-gitops-pods-status.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Toàn bộ 5 microservices đạt trạng thái `Running` (1/1 hoặc 2/2) trên đúng cụm EKS quy định.
- [ ] Không có hiện tượng Pod rơi vào trạng thái `CrashLoopBackOff` hay `ImagePullBackOff`.
- [ ] Frontend gọi sang Order Service thành công qua tên miền `core.fabric.internal` (HTTP 200).
- [ ] Giao diện Argo CD Console hiển thị trạng thái xanh `Synced` và `Healthy`.
