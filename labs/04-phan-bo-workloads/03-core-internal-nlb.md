# 03.03 — Đặc Tả Core Internal NLB Sử Dụng AWS Load Balancer Controller (IP-target)

> **Mã bài lab:** `04.03`
> **Trạng thái tài liệu:** `READY_TO_RUN`
> **Vùng triển khai:** `ap-southeast-1` (Singapore) — VPC: `fabric-core-vpc`
> **File bằng chứng:** `evidence/04-workloads/03-core-nlb-status.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả Network Load Balancer nội bộ (Internal NLB) tại Core VPC do AWS Load Balancer Controller tự động quản trị với target-type IP, tiếp nhận lưu lượng HTTPS mã hóa (TCP 443 -> TCP 8082) từ Transit Gateway và phân phối trực tiếp tới các Pods của `core-service`.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Vị Trí / Subnet / AZ | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `aws-load-balancer-controller` | `k8s::Deployment` | `fabric-core-eks` (`kube-system`) | Chạy qua EKS Pod Identity |
| `core-internal-nlb` | `k8s::Service` (LoadBalancer) | `fabric-core-eks` (`fabric-apps`) | Service selector `app: core-service` |
| `fabric-core-internal-nlb` | `AWS::ElasticLoadBalancingV2::LoadBalancer` | `fabric-core-vpc` (Internal) | Scheme: `internal`, Network |
| Target Group (Core NLB) | `AWS::ElasticLoadBalancingV2::TargetGroup` | Core VPC (`target-type: ip`) | Protocol: TCP, Port: 8082 |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-core-internal-nlb` | NLB và Target Group |
| `Project` | `aws-eks-secure-network-fabric` | K8s Service annotations, NLB và Target Group |
| `Environment` | `prod` | K8s Service annotations, NLB và Target Group |
| `ManagedBy` | `manual` | Quản trị bộ cân bằng tải nội bộ thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Cấu Hình K8s Service Annotations Cho Internal NLB

```yaml
apiVersion: v1
kind: Service
metadata:
  name: core-internal-nlb
  namespace: fabric-apps
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "external"
    service.beta.kubernetes.io/aws-load-balancer-name: "fabric-core-internal-nlb"
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internal"
    service.beta.kubernetes.io/aws-load-balancer-subnets: "fabric-core-nodes-1a, fabric-core-nodes-1b"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
    service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: "preserve_client_ip.enabled=false"
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-protocol: "TCP"
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-port: "traffic-port"
    service.beta.kubernetes.io/aws-load-balancer-additional-resource-tags: "Project=aws-eks-secure-network-fabric,Environment=prod"
spec:
  type: LoadBalancer
  selector:
    app: core-service
  ports:
  - name: https-core
    port: 443
    targetPort: 8082
    protocol: TCP
```

### 4.2 Thuộc Tính Mạng & Bảo Mật

- **Scheme:** `internal` (Bắt buộc riêng tư, không cấp Public IP).
- **Target Type:** `ip` (Định tuyến trực tiếp tới địa chỉ IP của Pod `core-service`, loại bỏ rủi ro lệch routing và overhead của NodePort).
- **Listener:** `TCP 443` -> Chuyển tiếp tới Target Group port `TCP 8082`.
- **Health Check:** TCP 8082 (`traffic-port`), interval 10 giây, healthy/unhealthy threshold: 3.

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `03.04`: EKS Pod Identity Association cho AWS Load Balancer Controller trên cụm `fabric-core-eks`.
- Phụ thuộc vào `02.01`: Subnets `fabric-core-nodes-1a/b` để cấp IP cho các ENIs của NLB.
- Phụ thuộc vào `04.04`: Pods của `core-service` phải sẵn sàng để Target Group đạt trạng thái `healthy`.
- Cung cấp DNS Name cho bản ghi `core.fabric.internal` tại `04.02`.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng thái Controller Deployment** | `kubectl get deployment aws-load-balancer-controller -n kube-system` | Pods hiển thị trạng thái `Running` (1/1 hoặc 2/2). |
| **Trạng thái K8s Service** | `kubectl get svc core-internal-nlb -n fabric-apps` | Cột `EXTERNAL-IP` hiển thị DNS nội bộ của AWS NLB. |
| **Scheme của Load Balancer** | `aws elbv2 describe-load-balancers --names fabric-core-internal-nlb` | `Scheme: internal`, `State.Code: active`. |
| **Target Health** | `aws elbv2 describe-target-health --target-group-arn <TGArn>` | Các Pod IPs của `core-service` ở trạng thái `healthy`. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo tính tương thích Pod IP:** Tuyệt đối không gắn thủ công IP của Pod vào Target Group qua CLI/Console vì Pods có thể thay đổi IP khi tái khởi động. Toàn bộ đăng ký target phải do Controller thực hiện.
- **Quy trình Rollback:**
  ```bash
  # Xóa K8s Service (AWS Load Balancer Controller sẽ tự động thu hồi NLB và Target Group)
  kubectl delete svc core-internal-nlb -n fabric-apps --context fabric-core
  ```
