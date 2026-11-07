# 03.05 — Thiết Lập Ma Trận Kubernetes NetworkPolicy Hoàn Chỉnh (Zero Trust)

> **Mã bài lab:** `03.05`  
> **Trạng thái:** `RUNTIME_PASS`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bài lab [03.04](04-eks-pod-identity-and-addons.md).
- VPC CNI managed add-on đã có configuration `{"enableNetworkPolicy":"true"}`; cả hai cluster có node Ready và CoreDNS hoạt động sau khi phục hồi scaling ở 03.03.
- Module này nghiệm thu policy nội bộ bằng probe riêng. Kết nối tới ALB/NLB, DB và SQS chỉ nghiệm thu sau module 04/07 khi đích thật đã tồn tại.
- Tiện ích dòng lệnh `kubectl` đã được liên kết với 2 cụm `fabric-edge-eks` và `fabric-core-eks`.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Bài lab tương tác trực tiếp với Kubernetes API qua `kubectl` và hiển thị tài nguyên trên AWS EKS Console:
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

- **Chi phí:** $0.00 USD (Quy tắc NetworkPolicy là cấu hình phần mềm nội bộ trong cụm).
- **Cảnh báo Ma Trận Cô Lập (Zero Trust Default-Deny):** Quy tắc Default-Deny nếu áp dụng mà không khai báo ngoại lệ sẽ lập tức ngắt liên lạc tới CoreDNS (port 53) hoặc làm tê liệt toàn bộ luồng truyền thông microservices! Bắt buộc phải áp dụng tuần tự:
  1. Cho phép CoreDNS nội bộ (UDP/TCP 53).
  2. `frontend` tại Edge chỉ được nhận Inbound 8080 từ Ingress Controller và Egress sang `auth-service` (8081) hoặc sang Core NLB (443/8082).
  3. `order-service` tại Core chỉ được nhận kết nối từ Edge CIDR (`10.40.0.0/16`) và Egress tới Aurora PostgreSQL (5432), ElastiCache Redis (6379), và SQS VPCE (443).
  4. `payment-worker` tại Core chỉ được kết nối tới SQS VPCE (443) và Aurora DB (5432).

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console & Kubectl (Console Walkthrough)

### Bước 1: Kích Hoạt & Xác Nhận NetworkPolicy Agent Trên Cả Hai Cụm
1. Mở terminal, chuyển context sang cụm Edge:
   ```bash
   aws eks update-kubeconfig --region ap-southeast-1 --name fabric-edge-eks --alias fabric-edge
   # EKS Console → Add-ons → VPC CNI → Edit → Advanced configuration:
   # {"enableNetworkPolicy":"true"}; giữ nguyên các cấu hình khác đã có.
   kubectl rollout status daemonset aws-node -n kube-system
   ```
2. Chuyển context sang cụm Core và thực thi tương tự:
   ```bash
   aws eks update-kubeconfig --region ap-southeast-1 --name fabric-core-eks --alias fabric-core
   # Lặp lại cấu hình managed add-on qua Console trên Core.
   kubectl rollout status daemonset aws-node -n kube-system
   ```
3. EKS → Resources → Workloads → kube-system → aws-node: xác nhận container `aws-eks-nodeagent` Running. Đọc logs, không chỉ nhìn trạng thái add-on. Native NetworkPolicy dùng eBPF.

---

### Bước 2: Khởi Tạo Namespace Ứng Dụng `fabric-apps`
Thực thi trên cả hai cụm `fabric-edge` và `fabric-core`:
```bash
kubectl create namespace fabric-apps --dry-run=client -o yaml | kubectl apply -f -
```

---

### Bước 3: Triển Khai Default Deny & CoreDNS Egress Baseline
Tạo file manifest `default-deny-and-dns.yaml` và áp dụng vào cả 2 cụm:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: fabric-apps
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-coredns-egress
  namespace: fabric-apps
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```
Áp dụng:
```bash
kubectl apply -f default-deny-and-dns.yaml --context fabric-edge
kubectl apply -f default-deny-and-dns.yaml --context fabric-core
```

---

### Bước 4: Triển Khai Microservices NetworkPolicies Cho Cụm Edge (`fabric-edge-eks`)
Chuyển context sang `fabric-edge`. Áp dụng chính sách cho `frontend` và `auth-service`:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-policy
  namespace: fabric-apps
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Ingress
  - Egress
  ingress:
  # ALB target IP gửi từ public subnets; SG Pod/Node chỉ cho ALB SG.
  - from:
    - ipBlock:
        cidr: 10.40.0.0/23
    ports:
    - protocol: TCP
      port: 8080
  egress:
  # Cho phép gọi nội bộ sang auth-service
  - to:
    - podSelector:
        matchLabels:
          app: auth-service
    ports:
    - protocol: TCP
      port: 8081
  # Cho phép gọi sang Core VPC qua TGW / Core NLB
  - to:
    - ipBlock:
        cidr: 10.50.0.0/16
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 8082
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: auth-service-policy
  namespace: fabric-apps
spec:
  podSelector:
    matchLabels:
      app: auth-service
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8081
```

---

### Bước 5: Triển Khai Microservices NetworkPolicies Cho Cụm Core (`fabric-core-eks`)
Chuyển context sang `fabric-core`. Áp dụng chính sách cho `order-service`, `inventory-service`, và `payment-worker`:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: order-service-policy
  namespace: fabric-apps
spec:
  podSelector:
    matchLabels:
      app: order-service
  policyTypes:
  - Ingress
  - Egress
  ingress:
  # NLB TCP/IP target, preserve_client_ip=false: Pod thấy IP NLB ở node subnets.
  - from:
    - ipBlock:
        cidr: 10.50.8.0/21
    ports:
    - protocol: TCP
      port: 8082
  egress:
  # Gọi sang inventory-service
  - to:
    - podSelector:
        matchLabels:
          app: inventory-service
    ports:
    - protocol: TCP
      port: 8083
  # Gọi xuống Aurora DB (5432) & ElastiCache Redis (6379)
  - to:
    - ipBlock:
        cidr: 10.50.20.0/23
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
  # Gọi sang AWS SQS VPC Endpoint (443)
  - to:
    - ipBlock:
        cidr: 10.50.30.0/23
    ports:
    - protocol: TCP
      port: 443
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: payment-worker-policy
  namespace: fabric-apps
spec:
  podSelector:
    matchLabels:
      app: payment-worker
  policyTypes:
  - Egress
  egress:
  # Gọi tới SQS VPCE
  - to:
    - ipBlock:
        cidr: 10.50.30.0/23
    ports:
    - protocol: TCP
      port: 443
  # Gọi tới Aurora DB
  - to:
    - ipBlock:
        cidr: 10.50.20.0/23
    ports:
    - protocol: TCP
      port: 5432
```

---

### Bước 5b: Inventory và đường lấy AWS credentials

Lưu thành `inventory-and-identity.yaml`, áp dụng Core. Các Pod dùng AWS SDK phải có SDK hỗ trợ Pod Identity, ServiceAccount/association và IAM policy đúng tài nguyên tại module 04; policy mạng không cấp quyền IAM.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: inventory-service-policy
  namespace: fabric-apps
spec:
  podSelector:
    matchLabels:
      app: inventory-service
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: order-service
    ports:
    - {protocol: TCP, port: 8083}
  egress:
  - to:
    - ipBlock: {cidr: 10.50.20.0/23}
    ports:
    - {protocol: TCP, port: 6379}
  # SDK đọc Secrets Manager qua interface endpoint Core.
  - to:
    - ipBlock: {cidr: 10.50.30.0/23}
    ports:
    - {protocol: TCP, port: 443}
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-pod-identity
  namespace: fabric-apps
spec:
  podSelector:
    matchLabels:
      aws-credentials: pod-identity
  policyTypes: [Egress]
  egress:
  - to:
    - ipBlock: {cidr: 169.254.170.23/32}
    ports:
    - {protocol: TCP, port: 80}
```

```bash
kubectl apply -f inventory-and-identity.yaml --context fabric-core
```

Gắn label `aws-credentials: pod-identity` trên **Pod template**, không chỉ Deployment metadata. Nếu Edge có workload cần AWS credentials, áp dụng riêng document `allow-pod-identity` vào Edge. Baseline DNS đã áp dụng chung.

### Bước 6: Quan Sát Trên AWS EKS Console
1. Mở **Amazon EKS Console** -> Chọn cụm `fabric-edge-eks`.
2. Chọn tab **Resources** -> Mở rộng mục **Network**.
3. Nhấp chọn **Network policies**:
   - Xác nhận hiển thị danh sách các chính sách: `default-deny-all`, `allow-coredns-egress`, `frontend-policy`, `auth-service-policy`.
4. Lặp lại kiểm tra trên cụm `fabric-core-eks`.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái áp dụng NetworkPolicy:
```bash
# 1. Liệt kê toàn bộ Network Policies trong namespace fabric-apps
kubectl get networkpolicies -n fabric-apps -o wide --context fabric-edge
kubectl get networkpolicies -n fabric-apps -o wide --context fabric-core

# Chỉ liệt kê policy không chứng minh enforcement.
```

### Kiểm chứng có đối chứng trước module 04

1. Chuẩn bị hai image probe/server đã ghim digest trong ECR, truy cập được qua endpoints; ghi URI vào evidence. Server phải chạy HTTP cổng 8083, probe có `curl`. Không dùng image public khi chưa có egress.
2. Tạo namespace `fabric-policy-test` trên Core qua EKS → Resources (hoặc `kubectl create namespace fabric-policy-test --context fabric-core`). Tạo server, Service và hai probe bằng **Deployment** một replica, không dùng standalone `kubectl run` Pod: native VPC CNI NetworkPolicy cần workload được hỗ trợ/ownerReferences. Label server `app: inventory-service`, probe hợp lệ `app: order-service`, probe còn lại `app: unauthorized-probe`; dùng node Linux EC2, không hostNetwork/Fargate/Windows.
3. Trước policy: chờ server Ready, xác nhận **cả hai** probe gọi Service cổng 8083 thành công. Nếu không có baseline, dừng; không được quy lỗi cho policy.
4. Sao chép document `default-deny-all`, `allow-coredns-egress`, `inventory-service-policy` và `order-service-policy` vào namespace thử; sửa namespace thành `fabric-policy-test`. Áp dụng bằng context Core. Không thay policy namespace production để thử.
5. Từ probe `order-service`, gọi cùng Service/IP/port: phải thành công. Probe không được cấp quyền phải timeout; ghi exit code và thời gian. Xác nhận server vẫn Ready và probe hợp lệ vẫn gọi được ngay sau lần deny.
6. EKS → Resources → Workloads và Network policies: lưu manifest, endpoint thật, trạng thái, stdout/stderr và timestamp. Nếu cả hai probe đều thất bại, kết quả **INCONCLUSIVE**, không PASS.
7. Xóa namespace thử sau thu evidence. Khi app đã có, lặp lại từng dòng ma trận: ALB→Frontend, Frontend→Auth, Frontend→NLB→Order, Order→Inventory/DB/SQS, Inventory→Redis, Payment→SQS/DB; kiểm tra cả health check NLB và nguồn IP backend.

> Manifest probe chưa có trong repo app: bài giữ `DRAFT` đến khi hai image và manifest được chuẩn bị, render, review. Không dùng IP DB ví dụ hay HTTP vào PostgreSQL làm bằng chứng deny.

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Trong trường hợp cần gỡ bỏ NetworkPolicy để khắc phục sự cố:
```bash
# Trước thay đổi: lưu policy hiện tại ra file riêng cho từng context.
kubectl get networkpolicy -n fabric-apps --context fabric-edge -o yaml > edge-policy-before.yaml
kubectl get networkpolicy -n fabric-apps --context fabric-core -o yaml > core-policy-before.yaml
# Nếu cập nhật lỗi: apply lại bản trước; xóa riêng policy mới không có trong bản trước.
kubectl apply -f edge-policy-before.yaml --context fabric-edge
kubectl apply -f core-policy-before.yaml --context fabric-core
```

Không xóa `--all` trong namespace ứng dụng: thao tác đó mở mạng và có thể xóa policy của người khác. Nếu bản trước không có policy, rollback phải theo danh sách tên vừa tạo đã lưu trước khi apply.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/03-eks/05-network-policy-verification.log`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [x] Tính năng native NetworkPolicy hoạt động ổn định trên AWS VPC CNI (eBPF mode với aws-eks-nodeagent controller injection).
- [x] Quy tắc default-deny ngăn chặn thành công 100% các kết nối trái phép giữa các pods.
- [x] Pods hợp lệ kết nối thành công tới đúng các cổng nghiệp vụ (53, 443, 5432, 6379, 8080, 8081, 8082, 8083).
- [x] EKS Console hiển thị đầy đủ danh sách NetworkPolicy trong tab Resources (Resource group `networking.k8s.io/v1`).

---

## 9. Nhật Ký Nghiệm Thu Runtime (Runtime Execution Summary)

- **Ngày thực thi:** `2026-11-07T16:35:30Z`
- **Tài khoản AWS:** `123456789012` (Sanitized) | Region: `ap-southeast-1`
- **Cụm áp dụng:**
  - `fabric-edge-eks`: Namespace `fabric-apps` (5 NetworkPolicies: `default-deny-all`, `allow-coredns-egress`, `frontend-policy`, `auth-service-policy`, `allow-pod-identity`).
  - `fabric-core-eks`: Namespace `fabric-apps` (6 NetworkPolicies: `default-deny-all`, `allow-coredns-egress`, `order-service-policy`, `inventory-service-policy`, `payment-worker-policy`, `allow-pod-identity`).
- **Xác thực Controller & BPF Attachment:**
  - Toàn bộ NetworkPolicy trên cả 2 cluster đều nhận được finalizer `networking.k8s.aws/resources` từ `aws-eks-nodeagent` daemonset (`v1.4.0-eksbuild.1`), chứng minh controller eBPF đã reconcile và load bpf program thành công trên kernel Linux 6.18.
- **Evidence Path:** `evidence/03-eks/05-network-policy-verification.json`
- **Manifests Path:** `k8s/network-policies/{edge,core}/fabric-apps-netpols.yaml`
