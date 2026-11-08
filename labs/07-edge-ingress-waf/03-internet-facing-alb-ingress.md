# 07.03 — Đặc Tả Triển Khai Internet-facing ALB Ingress Tích Hợp ACM TLS & WAF

> **Mã bài lab:** `07.03`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore) — VPC: `fabric-edge-vpc`
> **File bằng chứng:** `evidence/07-waf/03-alb-ingress-active.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả tài nguyên Application Load Balancer công khai (Internet-facing ALB) tại Edge VPC do AWS Load Balancer Controller tự động quản trị thông qua Kubernetes Ingress, tích hợp chấm dứt TLS bằng chứng chỉ ACM, chuyển hướng HTTP-sang-HTTPS tự động và liên kết trực tiếp với AWS WAFv2 Web ACL.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Vị Trí / Subnet / AZ | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `edge-frontend-ingress` | `networking.k8s.io/v1::Ingress` | `fabric-edge-eks` (`fabric-apps`) | Class: `alb`, Host: `app3.devopsss.site` |
| `fabric-edge-public-alb` | `AWS::ElasticLoadBalancingV2::LoadBalancer` | `fabric-edge-public-1a`, `1b` | `arn:aws:elasticloadbalancing:ap-southeast-1:123456789012:loadbalancer/app/fabric-edge-public-alb/61108d1397d1c55c`<br>DNS: `fabric-edge-public-alb-524689972.ap-southeast-1.elb.amazonaws.com` |
| Target Group (Edge ALB) | `AWS::ElasticLoadBalancingV2::TargetGroup` | `target-type: ip` | Protocol: HTTP, Port: 8080 (`10.40.9.110`, `10.40.15.20`) |
| Listener HTTP:80 | `AWS::ElasticLoadBalancingV2::Listener` | `fabric-edge-public-alb` | Action: Redirect HTTP 301 sang HTTPS:443 |
| Listener HTTPS:443 | `AWS::ElasticLoadBalancingV2::Listener` | `fabric-edge-public-alb` | Certificate: ACM `0907f419-...`<br>WAF: `fabric-edge-web-acl` |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-edge-public-alb` | Load Balancer và Target Group |
| `Project` | `aws-eks-secure-network-fabric` | Ingress, ALB, Target Groups, Listeners |
| `Environment` | `prod` | Ingress, ALB, Target Groups, Listeners |
| `ManagedBy` | `manual` | Quản trị bộ cân bằng tải công khai thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Cấu Hình Kubernetes Ingress Annotations

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: edge-frontend-ingress
  namespace: fabric-apps
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/load-balancer-name: fabric-edge-public-alb
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:ap-southeast-1:123456789012:certificate/0907f419-dd72-4b90-89af-e2bf7ce67391
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:ap-southeast-1:123456789012:regional/webacl/fabric-edge-web-acl/a010b9c0-edfa-4ba4-bfb0-8691ae8ecf56
    alb.ingress.kubernetes.io/healthcheck-path: /healthz
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: "15"
    alb.ingress.kubernetes.io/healthcheck-timeout-seconds: "5"
    alb.ingress.kubernetes.io/healthy-threshold-count: "2"
    alb.ingress.kubernetes.io/unhealthy-threshold-count: "2"
spec:
  ingressClassName: alb
  rules:
  - host: app3.devopsss.site
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: edge-frontend
            port:
              number: 8080
```

### 4.2 Đặc Tính Mạng & Bảo Mật

- **Subnet Placement:** Bắt buộc đặt trong `fabric-edge-public-1a` (`subnet-04dfffbdc3e5e0c93`) và `fabric-edge-public-1b` (`subnet-0a9017b8109df0c48`).
- **TLS Termination:** Chấm dứt TLS tại ALB bằng chứng chỉ ACM RSA-2048; truyền tải HTTP 8080 nội bộ an toàn tới pods thông qua VPC CNI IP-target.
- **WAFv2 Protection:** Gắn kết cứng với Web ACL ID `a010b9c0-edfa-4ba4-bfb0-8691ae8ecf56`.

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `07.01`: Chứng chỉ ACM ở trạng thái `ISSUED`.
- Phụ thuộc vào `07.02`: Web ACL `fabric-edge-web-acl` sẵn sàng.
- Phụ thuộc vào `03.04`: EKS Pod Identity Association cho AWS Load Balancer Controller trên cụm `fabric-edge-eks`.
- Phụ thuộc vào `04.04`: Pods `edge-frontend` ở trạng thái `Running` để Target Group đạt `healthy`.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng thái K8s Ingress** | `kubectl get ingress edge-frontend-ingress -n fabric-apps` | Cột `ADDRESS` hiển thị DNS Name của AWS ALB. |
| **Gắn kết WAF Web ACL** | `aws wafv2 get-web-acl-for-resource --resource-arn <AlbArn>` | Trả về thông tin Web ACL `fabric-edge-web-acl` (ID: `a010b9c0-...`). |
| **HTTP-to-HTTPS Redirection** | `curl -I http://app3.devopsss.site` | Trả về `HTTP/1.1 301 Moved Permanently` (Location: `https://app3.devopsss.site:443/`). |
| **HTTPS Endpoint Response** | `curl -Iv https://app3.devopsss.site/healthz` | Trả về `HTTP/1.1 200 OK` (JSON: `"service":"edge-frontend","status":"UP"`). |
| **Target Health** | `aws elbv2 describe-target-health --target-group-arn <TGArn>` | Cả 2 Pod IPs (`10.40.9.110`, `10.40.15.20`) ở trạng thái `healthy`. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo rò rỉ mạng:** Không đặt ALB Ingress vào Private Node Subnets vì Internet Gateway không thể định tuyến trực tiếp vào dải private, gây lỗi `Route unreachable`.
- **Quy trình Rollback:**
  ```bash
  # Xóa Ingress manifest (Controller sẽ tự động gỡ bỏ ALB và Target Group)
  kubectl delete ingress edge-frontend-ingress -n fabric-apps --context fabric-edge
  ```
