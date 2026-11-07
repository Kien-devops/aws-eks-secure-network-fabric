# 07.03 — Triển Khai Internet-facing ALB Ingress Tích Hợp ACM TLS & WAF

> **Mã bài lab:** `07.03`  
> **Trạng thái:** `COMPLETED`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** ~$0.0225 USD / giờ cho Application Load Balancer tại Singapore  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — VPC: `fabric-edge-vpc`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bài lab [07.01](01-acm-public-tls-certificate.md):
  - Domain công khai: **`app3.devopsss.site`** (Hosted Zone: `devopsss.site`).
  - ACM Certificate ARN: `arn:aws:acm:ap-southeast-1:123456789012:certificate/0907f419-dd72-4b90-89af-e2bf7ce67391` (Status: `ISSUED`).
- Đã hoàn thành bài lab [07.02](02-aws-wafv2-web-acl-setup.md):
  - WAFv2 Web ACL ARN: `arn:aws:wafv2:ap-southeast-1:123456789012:regional/webacl/fabric-edge-web-acl/a010b9c0-edfa-4ba4-bfb0-8691ae8ecf56`.
- Cụm `fabric-edge-eks` đang hoạt động với các pods `frontend` đang chạy trong namespace `fabric-apps`.
- Hai Public Subnets `fabric-edge-public-1a` (`subnet-04dfffbdc3e5e0c93`) và `fabric-edge-public-1b` (`subnet-0a9017b8109df0c48`) đã sẵn sàng kết nối qua Internet Gateway `fabric-edge-igw`.
- Đang mở phiên AWS Management Console tại Singapore `ap-southeast-1`.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

AWS Load Balancer Controller sử dụng EKS Pod Identity để quản lý Application Load Balancers và liên kết WAF:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:CreateLoadBalancer",
        "elasticloadbalancing:CreateTargetGroup",
        "elasticloadbalancing:CreateListener",
        "elasticloadbalancing:RegisterTargets",
        "elasticloadbalancing:Describe*",
        "elasticloadbalancing:DeleteLoadBalancer",
        "wafv2:AssociateWebACL",
        "wafv2:DisassociateWebACL",
        "wafv2:GetWebACL",
        "wafv2:GetWebACLForResource"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Application Load Balancer tính phí ~$0.0225 USD/giờ cộng với phí LCU xử lý lưu lượng.
- **Cảnh báo Subnet Placement (Nguy cơ rò rỉ hoặc nghẽn mạng):** ALB công khai **BẮT BUỘC PHẢI NẰM TRONG 2 PUBLIC SUBNETS** (`fabric-edge-public-1a` và `fabric-edge-public-1b`). Tuyệt đối không đặt ALB vào Node Subnets hoặc TGW Subnets.
- **Cảnh báo HTTP-to-HTTPS Redirection:** Để đảm bảo chuẩn an ninh thanh toán PCI-DSS và Zero Trust, mọi yêu cầu gửi tới HTTP port 80 bắt buộc phải được tự động chuyển hướng (HTTP 301 Redirect) sang cổng HTTPS 443 có mã hóa TLS.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console & Kubectl (Console Walkthrough)

### Bước 1: Gắn Thẻ Subnets Cho AWS Load Balancer Controller Khám Phá
AWS Load Balancer Controller tự động quét các Subnets dựa trên thẻ nhãn để đặt ALB:
1. Mở **VPC Console** tại Singapore `ap-southeast-1` -> Chọn **Subnets**.
2. Tìm và chọn `fabric-edge-public-1a` -> Chọn tab **Tags** -> Nhấp **Manage tags**:
   - Thêm thẻ: Key: `kubernetes.io/role/elb` | Value: `1` (Báo hiệu đây là Public Subnet dành cho Public ALBs).
   - Thêm thẻ: Key: `kubernetes.io/cluster/fabric-edge-eks` | Value: `shared`.
   - Nhấp **Save**.
3. Lặp lại bước trên cho subnet `fabric-edge-public-1b`.

---

### Bước 2: Cài Đặt AWS Load Balancer Controller Trên Cụm Edge EKS
1. Mở terminal, chuyển context sang cụm Edge:
   ```bash
   aws eks update-kubeconfig --region ap-southeast-1 --name fabric-edge-eks --alias fabric-edge
   ```
2. Cài đặt Controller bằng Helm (tận dụng Pod Identity đã tạo ở 03.04):
   ```bash
   helm repo add eks https://aws.github.io/eks-charts
   helm repo update
   
   EDGE_VPC_ID=$(aws ec2 describe-vpcs --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-edge-vpc" --query 'Vpcs[0].VpcId' --output text)
   
   helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
     -n kube-system \
     --set clusterName=fabric-edge-eks \
     --set serviceAccount.create=true \
     --set serviceAccount.name=aws-load-balancer-controller \
     --set region=ap-southeast-1 \
     --set vpcId=$EDGE_VPC_ID
   ```
3. Xác nhận Deployment chuyển sang `Running`:
   ```bash
   kubectl rollout status deployment aws-load-balancer-controller -n kube-system
   ```

---

### Bước 3: Triển Khai Kubernetes Ingress Manifest Tích Hợp ACM & WAF
1. File manifest hoàn chỉnh tại repository ứng dụng: [ingress.yaml](file:///e:/repo/project6/aws-eks-secure-network-fabric-app/k8s/edge/ingress.yaml):
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: edge-frontend-ingress
     namespace: fabric-apps
     labels:
       app: frontend
       Project: aws-eks-secure-network-fabric
     annotations:
       # Điều phối AWS Load Balancer Controller
       alb.ingress.kubernetes.io/scheme: internet-facing
       alb.ingress.kubernetes.io/target-type: ip
       alb.ingress.kubernetes.io/load-balancer-name: fabric-edge-public-alb
       
       # Cấu hình giao thức HTTPS và Chứng chỉ ACM TLS
       alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
       alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:ap-southeast-1:123456789012:certificate/0907f419-dd72-4b90-89af-e2bf7ce67391
       alb.ingress.kubernetes.io/ssl-redirect: '443'
       
       # Tích hợp trực tiếp AWS WAF v2 Web ACL
       alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:ap-southeast-1:123456789012:regional/webacl/fabric-edge-web-acl/a010b9c0-edfa-4ba4-bfb0-8691ae8ecf56
       
       # Health check và nhãn tài nguyên
       alb.ingress.kubernetes.io/healthcheck-path: /healthz
       alb.ingress.kubernetes.io/healthcheck-interval-seconds: "15"
       alb.ingress.kubernetes.io/healthcheck-timeout-seconds: "5"
       alb.ingress.kubernetes.io/healthy-threshold-count: "2"
       alb.ingress.kubernetes.io/unhealthy-threshold-count: "2"
       alb.ingress.kubernetes.io/tags: Project=aws-eks-secure-network-fabric,Environment=prod,elbv2.k8s.aws/cluster=fabric-edge-eks
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
               name: frontend
               port:
                 number: 8080
   ```
2. Áp dụng manifest lên cụm Edge EKS:
   ```bash
   kubectl apply -f k8s/edge/ingress.yaml --context fabric-edge
   ```

---

### Bước 4: Quan Sát Trạng Thái Khởi Tạo Trên AWS Console
1. Mở **EC2 Console** tại Region Singapore `ap-southeast-1` -> Menu bên trái chọn **Load Balancers**.
2. Tìm Load Balancer `fabric-edge-public-alb`:
   - **Scheme:** Xác nhận là **`internet-facing`**.
   - **VPC:** Xác nhận là **`fabric-edge-vpc`**.
   - **State:** Đạt trạng thái màu xanh: **`Active`**.
3. Chọn tab **Listeners and rules**:
   - Listener `HTTP:80`: Hiển thị hành động `Redirect to HTTPS:443`.
   - Listener `HTTPS:443`: Hiển thị hành động `Forward to Target Group` kèm Certificate ACM hợp lệ (`app3.devopsss.site`).
4. Chọn tab **Integrations** (hoặc cuộn xuống mục **AWS WAF**):
   - Xác nhận mục AWS WAF hiển thị Web ACL: **`fabric-edge-web-acl`** (Tích hợp thành công).
5. Tại menu bên trái, chọn **Target Groups**:
   - Nhấp vào Target Group `k8s-fabricap-frontend-...` -> Tab **Targets**:
   - Xác nhận cả 2 Pod IPs của dịch vụ `frontend` (`10.40.9.110` và `10.40.15.20`) ở trạng thái **`healthy`**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái Ingress và xác minh liên kết WAF qua CLI:
```bash
# 1. Kiểm tra Kubernetes Ingress và lấy Public DNS Name
kubectl get ingress edge-frontend-ingress -n fabric-apps --context fabric-edge -o wide

# 2. Kiểm tra ALB gắn đúng Web ACL
aws wafv2 get-web-acl-for-resource --region ap-southeast-1 \
  --resource-arn arn:aws:elasticloadbalancing:ap-southeast-1:123456789012:loadbalancer/app/fabric-edge-public-alb/61108d1397d1c55c \
  --query 'WebACL.{Name:Name,Id:Id,Capacity:Capacity}' \
  --output table

# 3. Kiểm thử chuyển hướng HTTP sang HTTPS
curl -I http://app3.devopsss.site

# 4. Kiểm thử kết nối HTTPS tới Frontend
curl -Iv https://app3.devopsss.site/healthz

# 5. Kiểm tra trạng thái Target Health của Pods phía sau ALB
aws elbv2 describe-target-health --region ap-southeast-1 \
  --target-group-arn $(aws elbv2 describe-target-groups --region ap-southeast-1 --load-balancer-arn arn:aws:elasticloadbalancing:ap-southeast-1:123456789012:loadbalancer/app/fabric-edge-public-alb/61108d1397d1c55c --query 'TargetGroups[0].TargetGroupArn' --output text) \
  --query 'TargetHealthDescriptions[*].{IP:Target.Id,Port:Target.Port,AZ:Target.AvailabilityZone,State:TargetHealth.State}' \
  --output table
```

**Runtime Output Thực Tế:**
```text
NAME                    CLASS   HOSTS                ADDRESS                                                             PORTS   AGE
edge-frontend-ingress   alb     app3.devopsss.site   fabric-edge-public-alb-524689972.ap-southeast-1.elb.amazonaws.com   80      75m

------------------------------------------------------------------------------------------
|                                  GetWebACLForResource                                  |
+----------+---------------------------------------+-------------------------------------+
| Capacity |                  Id                   |                Name                 |
+----------+---------------------------------------+-------------------------------------+
|  927     |  a010b9c0-edfa-4ba4-bfb0-8691ae8ecf56 |  fabric-edge-web-acl                |
+----------+---------------------------------------+-------------------------------------+

HTTP/1.1 301 Moved Permanently
Server: awselb/2.0
Location: https://app3.devopsss.site:443/

HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 141
{"service":"edge-frontend","status":"UP","timestamp":"...","data":{"cluster":"fabric-edge-eks","environment":"production"}}

-------------------------------------------------------
|                DescribeTargetHealth                 |
+-----------------+---------------+-------+-----------+
|       AZ        |      IP       | Port  |   State   |
+-----------------+---------------+-------+-----------+
|  ap-southeast-1a|  10.40.9.110  |  8080 |  healthy  |
|  ap-southeast-1b|  10.40.15.20  |  8080 |  healthy  |
+-----------------+---------------+-------+-----------+
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Để gỡ bỏ Public ALB Ingress:
```bash
kubectl delete -f k8s/edge/ingress.yaml --context fabric-edge
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/07-waf/03-alb-ingress-active.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [x] ALB công khai được tạo thành công trên 2 Public Subnets của Edge VPC (`fabric-edge-public-1a/b`).
- [x] Listener HTTP 80 tự động chuyển hướng HTTP 301 sang HTTPS 443.
- [x] Listener HTTPS 443 giải mã TLS với chứng chỉ ACM hợp lệ và chuyển tiếp tới Frontend Pods.
- [x] Web ACL `fabric-edge-web-acl` được gắn kết thành công và bảo vệ trực tiếp trên ALB.
- [x] Cả 2 Pods backend trong Target Group hiển thị trạng thái `healthy`.
