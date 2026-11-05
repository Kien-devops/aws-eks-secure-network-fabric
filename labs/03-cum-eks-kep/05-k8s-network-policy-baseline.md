# 03.05 — Thiết Lập Chính Sách Bảo Mật Kubernetes NetworkPolicy Baseline

> **Trạng thái:** Hướng dẫn thực hành chi tiết cấu hình an ninh nội bộ Kubernetes.  
> **Áp dụng cho:** Thực thi mô hình Zero-Trust trong cụm Kubernetes bằng cơ chế Default Deny và chỉ mở luồng có khai báo tường minh.

---

## 1. Mục Tiêu Kỹ Thuật

- Kích hoạt tính năng hỗ trợ **Kubernetes NetworkPolicy** trên AWS VPC CNI (hoặc sử dụng Calico / Cilium CNI add-on).
- Triển khai chính sách bảo mật **Default Deny All** cho cả 2 chiều Ingress và Egress trên namespace chạy ứng dụng.
- Cấu hình các chính sách NetworkPolicy ngoại lệ cho phép:
  - Cho phép truy cập DNS nội bộ qua CoreDNS (Cổng UDP 53).
  - Cho phép Ingress từ ALB Ingress hoặc Core NLB.
  - Cho phép liên lạc giữa các microservices được chỉ định.

---

## 2. Kích Hoạt NetworkPolicy Trên AWS VPC CNI

Kể từ VPC CNI v1.14+, AWS hỗ trợ native NetworkPolicy. Bật cờ qua cấu hình DaemonSet:
```bash
aws eks update-addon \
  --cluster-name fabric-edge-eks \
  --addon-name vpc-cni \
  --configuration-values '{"enableNetworkPolicy": "true"}' \
  --region ap-southeast-1
```
*(Thực hiện tương tự trên cụm `fabric-core-eks`)*.

---

## 3. Các File Manifest NetworkPolicy Chuẩn

### 1. Chính Sách Mặc Định Chặn Toàn Bộ (`00-default-deny.yaml`)
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

### 2. Cho Phép Truy Vấn DNS Nội Bộ (`01-allow-dns.yaml`)
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-coredns
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Egress
  - Ingress
  egress:
  - to:
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

### 3. Cho Phép Frontend Nhận Traffic Từ ALB (`02-allow-frontend-ingress.yaml`)
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-ingress
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - ipBlock:
        cidr: 10.40.0.0/24 # Public Subnet AZ-a
    - ipBlock:
        cidr: 10.40.1.0/24 # Public Subnet AZ-b
    ports:
    - protocol: TCP
      port: 80
```

---

## 4. Xác Minh (Verification)

Kiểm tra danh sách NetworkPolicy đã được áp dụng:
```bash
kubectl get networkpolicies -n default
```
Chạy thử Pod kiểm tra: Pod lạ trong cụm không thể ping hoặc curl tới Pod khác khi chưa có NetworkPolicy cho phép.

---

## 5. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Tính năng NetworkPolicy được kích hoạt trên AWS VPC CNI.
- [ ] Chính sách Default Deny có hiệu lực: Các Pod chưa cấp phép không thể kết nối qua lại.
- [ ] CoreDNS phân giải tên miền bình thường nhờ chính sách allow-dns.

