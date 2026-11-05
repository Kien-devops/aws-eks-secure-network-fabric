# 04.03 — Triển Khai Core Internal NLB Sử Dụng AWS Load Balancer Controller (IP-target)

> **Mã bài lab:** `04.03`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** ~$0.0225 USD / giờ cho Network Load Balancer tại Singapore  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — VPC: `fabric-core-vpc`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bài lab [03.04](../03-cum-eks-kep/04-eks-pod-identity-and-addons.md) với EKS Pod Identity Association đã được cấu hình cho ServiceAccount `aws-load-balancer-controller`.
- Private Hosted Zone `fabric.internal` đã được khởi tạo và liên kết cả 2 VPCs tại bài lab [04.02](02-route53-private-hosted-zone.md).
- Kết nối `kubectl` tới cụm `fabric-core-eks` đang hoạt động.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

AWS Load Balancer Controller sử dụng EKS Pod Identity để gọi các API quản lý NLB:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:CreateLoadBalancer",
        "elasticloadbalancing:CreateTargetGroup",
        "elasticloadbalancing:RegisterTargets",
        "elasticloadbalancing:DeregisterTargets",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeTargetHealth",
        "elasticloadbalancing:ModifyLoadBalancerAttributes",
        "elasticloadbalancing:ModifyTargetGroupAttributes",
        "elasticloadbalancing:DeleteLoadBalancer",
        "elasticloadbalancing:DeleteTargetGroup",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeVpcs"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Network Load Balancer tính phí ~$0.0225 USD/giờ cộng với phí NLCU truyền dữ liệu.
- **Cảnh báo Kiến Trúc IP-Target (Không dùng IP thủ công):** Tuyệt đối **KHÔNG ĐƯỢC ĐĂNG KÝ POD IP BẰNG TAY** vào Target Group của NLB. Trong môi trường Kubernetes, Pod IP thay đổi liên tục khi Pod restart/reschedule. Bắt buộc phải để AWS Load Balancer Controller tự động quản lý vòng đời target thông qua Service manifest với annotation `nlb-ip`.
- **Cảnh báo Scheme:** **BẮT BUỘC CHỌN SCHEME LÀ INTERNAL**. NLB này chỉ phục vụ Ingress nội bộ cho cụm Core EKS từ Transit Gateway, tuyệt đối không được để lộ địa chỉ Public IP.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console & Kubectl (Console Walkthrough)

### Bước 1: Cài Đặt AWS Load Balancer Controller Bằng Helm Trên Cụm Core
1. Mở terminal, chuyển context sang cụm Core EKS:
   ```bash
   aws eks update-kubeconfig --region ap-southeast-1 --name fabric-core-eks --alias fabric-core
   ```
2. Thêm và cập nhật Helm repository:
   ```bash
   helm repo add eks https://aws.github.io/eks-charts
   helm repo update
   ```
3. Cài đặt AWS Load Balancer Controller (sử dụng EKS Pod Identity, không cần annotation role-arn trên SA):
   ```bash
   helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
     -n kube-system \
     --set clusterName=fabric-core-eks \
     --set serviceAccount.create=true \
     --set serviceAccount.name=aws-load-balancer-controller \
     --set region=ap-southeast-1 \
     --set vpcId=$(aws ec2 describe-vpcs --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-core-vpc" --query 'Vpcs[0].VpcId' --output text)
   ```
4. Xác nhận Deployment của Controller chuyển sang trạng thái sẵn sàng:
   ```bash
   kubectl rollout status deployment aws-load-balancer-controller -n kube-system
   ```

---

### Bước 2: Triển Khai Kubernetes Service Với Annotation IP-Target
Tạo file manifest `core-internal-nlb.yaml`:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: core-internal-nlb
  namespace: fabric-apps
  annotations:
    # Yêu cầu AWS Load Balancer Controller quản trị
    service.beta.kubernetes.io/aws-load-balancer-type: "external"
    # Target-type IP: Định tuyến trực tiếp tới IP của Pod (Không qua NodePort SNAT)
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
    # Scheme nội bộ: Chỉ cấp phát Private IP trong Core VPC
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internal"
    # Đặt NLB trên 2 Subnet Private Node của Core VPC
    service.beta.kubernetes.io/aws-load-balancer-subnets: "fabric-core-nodes-1a, fabric-core-nodes-1b"
    # Bật cân bằng tải chéo AZ
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
    # Tag phân loại
    service.beta.kubernetes.io/aws-load-balancer-additional-resource-tags: "Project=aws-eks-secure-network-fabric,Environment=prod"
spec:
  type: LoadBalancer
  selector:
    app: order-service
  ports:
  - name: https-order
    port: 443
    targetPort: 8082
    protocol: TCP
```
Áp dụng manifest vào cụm Core EKS:
```bash
kubectl apply -f core-internal-nlb.yaml
```

---

### Bước 3: Quan Sát & Kiểm Tra Trạng Thái NLB Trên AWS Console
1. Mở **EC2 Console** tại Region Singapore `ap-southeast-1`.
2. Tại menu điều hướng bên trái, cuộn xuống nhóm **Load Balancing** -> Chọn **Load Balancers**.
3. Tìm kiếm Load Balancer kiểu **Network** vừa được tạo:
   - **Name:** Có định dạng tự động `k8s-fabricap-coreinte-...`.
   - **Scheme:** Xác nhận là **`internal`**.
   - **Type:** Xác nhận là **`network`**.
   - **VPC:** Xác nhận là **`fabric-core-vpc`**.
   - **State:** Đợi chuyển sang màu xanh: **`Active`**.
4. Chọn tab **Listeners and rules**:
   - Xác nhận có Listener: `TCP:443` chuyển tiếp tới Target Group tương ứng.
5. Tại menu bên trái, chọn **Target Groups**:
   - Nhấp vào Target Group của NLB vừa tạo.
   - Chọn tab **Targets**:
     - Xác nhận **Target type** hiển thị: **`IP`**.
     - Quan sát danh sách Registered targets: Hiển thị các địa chỉ IP của Pod `order-service` (nằm trong dải `10.50.10.x` hoặc `10.50.14.x`).
     - Cột **Health status** hiển thị: **`healthy`**.

---

### Bước 4: Cập Nhật Bản Ghi DNS Trên Route 53 Private Hosted Zone
1. Lấy DNS Name nội bộ của NLB:
   ```bash
   NLB_DNS=$(kubectl get svc core-internal-nlb -n fabric-apps -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
   echo "Core Internal NLB DNS: $NLB_DNS"
   ```
2. Mở **Route 53 Console** -> **Hosted zones** -> Chọn `fabric.internal`.
3. Tìm bản ghi `core.fabric.internal` (đã tạo nháp ở lab 04.02):
   - Nhấp vào bản ghi -> Chọn **Edit record**.
   - **Record type:** Chọn `CNAME`.
   - **Value:** Dán chính xác chuỗi `$NLB_DNS` vừa lấy được.
   - **TTL:** `60`.
   - Nhấp **Save**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy các lệnh xác minh trạng thái Service và Target Health:
```bash
# 1. Kiểm tra trạng thái Kubernetes Service
kubectl get svc core-internal-nlb -n fabric-apps -o wide

# 2. Lấy Target Group ARN của NLB
TG_ARN=$(aws elbv2 describe-target-groups --region ap-southeast-1 \
  --names $(aws elbv2 describe-load-balancers --region ap-southeast-1 --query 'LoadBalancers[?Scheme==`internal` && VpcId==`'"$(aws ec2 describe-vpcs --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-core-vpc" --query 'Vpcs[0].VpcId' --output text)"'`].LoadBalancerName' --output text) \
  --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null)

# 3. Kiểm tra sức khỏe của các targets trong Target Group
aws elbv2 describe-target-health --region ap-southeast-1 \
  --target-group-arn $TG_ARN \
  --query 'TargetHealthDescriptions[*].{TargetId:Target.Id,Port:Target.Port,State:TargetHealth.State}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Để gỡ bỏ Internal NLB:
```bash
# Xóa Service, AWS Load Balancer Controller sẽ tự động thu hồi NLB và Target Group trên AWS
kubectl delete -f core-internal-nlb.yaml
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/04-workloads/03-core-nlb-status.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] AWS Load Balancer Controller chạy ổn định với 2 pods `Ready` trên namespace `kube-system`.
- [ ] Network Load Balancer được khởi tạo tự động ở chế độ `internal` trong `fabric-core-vpc`.
- [ ] Target Group sử dụng `target-type: ip` và các Pod endpoints đạt trạng thái `healthy`.
- [ ] Bản ghi Route 53 `core.fabric.internal` phân giải chính xác về các địa chỉ IP riêng của NLB.
