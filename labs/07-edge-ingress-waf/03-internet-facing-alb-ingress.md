# 07.03 — Triển Khai Internet-facing ALB Ingress Tích Hợp ACM TLS & WAF

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console và Kubernetes Manifests.  
> **Áp dụng cho:** Xuất bản dịch vụ Frontend của Edge EKS ra Internet qua Application Load Balancer công khai gắn kèm WAF.

---

## 1. Mục Tiêu Kỹ Thuật

- Triển khai **AWS Load Balancer Controller** trên cụm `fabric-edge-eks`.
- Khởi tạo tài nguyên Kubernetes Ingress điều phối tạo **Public Application Load Balancer** trong các Public Subnets của Edge VPC:
  - Subnet: `fabric-edge-public-1a` và `fabric-edge-public-1b`.
  - Gắn chứng chỉ số ACM TLS cổng **HTTPS `443`**.
  - Tự động gắn kết với **AWS WAF v2 Web ACL** (`fabric-edge-web-acl`).
  - Định tuyến lưu lượng vào Pods `frontend`.

---

## 2. Các Bước Triển Khai Chi Tiết

### Bước 1: Gắn Thẻ Subnets Cho AWS Load Balancer Controller Tự Khám Phá
Đảm bảo 2 Public Subnets của Edge VPC có thẻ tag định danh:
- `kubernetes.io/role/elb` = `1`
- `kubernetes.io/cluster/fabric-edge-eks` = `shared`

---

### Bước 2: Triển Khai Manifest Kubernetes Ingress
Tạo file manifest `edge-alb-ingress.yaml`:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fabric-edge-ingress
  namespace: default
  annotations:
    # Điều phối AWS Load Balancer Controller
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/subnets: fabric-edge-public-1a, fabric-edge-public-1b
    
    # Cấu hình giao thức HTTPS và Chứng chỉ ACM
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: <ACM-CERTIFICATE-ARN>
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    
    # Tích hợp trực tiếp AWS WAF v2
    alb.ingress.kubernetes.io/wafv2-acl-arn: <WAF-WEB-ACL-ARN>
    
    # Bật Access Logs đẩy về S3
    alb.ingress.kubernetes.io/load-balancer-attributes: access_logs.s3.enabled=true,access_logs.s3.bucket=fabric-alb-logs-bucket
spec:
  ingressClassName: alb
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 80
```

Áp dụng manifest vào cụm:
```bash
kubectl apply -f edge-alb-ingress.yaml
```

---

## 3. Xác Minh (Verification)

Kiểm tra địa chỉ Address (DNS Name) của Ingress:
```bash
kubectl get ingress fabric-edge-ingress
```
Kiểm tra trên AWS Console hoặc CLI:
```bash
aws elbv2 describe-load-balancers \
  --region ap-southeast-1 \
  --query 'LoadBalancers[?Scheme==`internet-facing`].{Name:LoadBalancerName,DNS:DNSName,State:State.Code}' \
  --output table
```
> Kết quả: ALB được khởi tạo và chuyển sang trạng thái `active`.

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] ALB công khai được tạo thành công trên 2 Public Subnets của Edge VPC.
- [ ] Listener HTTPS 443 tiếp nhận traffic và chuyển tiếp vào Frontend Pods.
- [ ] Web ACL `fabric-edge-web-acl` hiển thị trong tab Integrations của ALB trên Console.

