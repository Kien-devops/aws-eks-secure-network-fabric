# 03.05 — Thiết Lập Ma Trận Kubernetes NetworkPolicy Hoàn Chỉnh (Zero Trust)

> **Mã bài lab:** `03.05`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bài lab [03.04](04-eks-pod-identity-and-addons.md).
- VPC CNI NetworkPolicy controller đã được kích hoạt trên cả 2 cụm EKS bằng cấu hình Add-on hoặc lệnh:
  ```bash
  kubectl set env daemonset aws-node -n kube-system ENABLE_NETWORK_POLICY=true
  ```
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
   kubectl set env daemonset aws-node -n kube-system ENABLE_NETWORK_POLICY=true
   kubectl rollout status daemonset aws-node -n kube-system
   ```
2. Chuyển context sang cụm Core và thực thi tương tự:
   ```bash
   aws eks update-kubeconfig --region ap-southeast-1 --name fabric-core-eks --alias fabric-core
   kubectl set env daemonset aws-node -n kube-system ENABLE_NETWORK_POLICY=true
   kubectl rollout status daemonset aws-node -n kube-system
   ```
3. Kiểm tra pod logs của `aws-node` xác nhận container `aws-eks-nodeagent` đã khởi chạy thành công bộ điều khiển eBPF / iptables NetworkPolicy.

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
  # Cho phép lưu lượng Ingress từ ingress controller / ALB
  - from:
    - namespaceSelector: {}
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
  # Chỉ nhận kết nối từ Edge VPC CIDR qua NLB
  - from:
    - ipBlock:
        cidr: 10.40.0.0/16
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

# 2. Thử nghiệm vi phạm chính sách: Tạo pod lạ cố gắng kết nối trái phép tới Database
kubectl run unauthorized-probe --rm -it --image=curlimages/curl --restart=Never -n fabric-apps --context fabric-core -- \
  curl -m 3 http://10.50.20.15:5432 || echo "PASSED: Unauthorized connection dropped by NetworkPolicy!"
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Trong trường hợp cần gỡ bỏ NetworkPolicy để khắc phục sự cố:
```bash
kubectl delete networkpolicies --all -n fabric-apps --context fabric-edge
kubectl delete networkpolicies --all -n fabric-apps --context fabric-core
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/03-eks/05-network-policy-verification.log`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Tính năng native NetworkPolicy hoạt động ổn định trên AWS VPC CNI.
- [ ] Quy tắc default-deny ngăn chặn thành công 100% các kết nối trái phép giữa các pods.
- [ ] Pods hợp lệ kết nối thành công tới đúng các cổng nghiệp vụ (53, 443, 5432, 6379, 8080, 8081, 8082, 8083).
- [ ] EKS Console hiển thị đầy đủ danh sách NetworkPolicy trong tab Resources.
