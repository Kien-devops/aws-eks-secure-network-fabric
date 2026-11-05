# 07.03 — Triển Khai Internet-facing ALB Ingress Tích Hợp ACM TLS & WAF

> **Mã bài lab:** `07.03`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** ~$0.0225 USD / giờ cho Application Load Balancer tại Singapore  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — VPC: `fabric-edge-vpc`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bài lab [07.01](01-acm-public-tls-certificate.md) (lấy được ACM Certificate ARN) và [07.02](02-aws-wafv2-web-acl-setup.md) (lấy được Web ACL ARN).
- Cụm `fabric-edge-eks` đang hoạt động với các pods `frontend` đang chạy trong namespace `fabric-apps`.
- Hai Public Subnets `fabric-edge-public-1a` và `fabric-edge-public-1b` đã sẵn sàng kết nối qua Internet Gateway `fabric-edge-igw`.
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
1. Lấy ARN của ACM Certificate và WAF Web ACL:
   ```bash
   ACM_ARN=$(aws acm list-certificates --region ap-southeast-1 --query 'CertificateSummaryList[0].CertificateArn' --output text)
   WAF_ARN=$(aws wafv2 list-web-acls --scope REGIONAL --region ap-southeast-1 --query 'WebACLs[?Name==`fabric-edge-web-acl`].ARN | [0]' --output text)
   echo "ACM Certificate ARN: $ACM_ARN"
   echo "WAF Web ACL ARN: $WAF_ARN"
   ```
2. Tạo file manifest `fabric-edge-ingress.yaml`:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: fabric-edge-ingress
     namespace: fabric-apps
     annotations:
       # Điều phối AWS Load Balancer Controller
       alb.ingress.kubernetes.io/scheme: internet-facing
       alb.ingress.kubernetes.io/target-type: ip
       alb.ingress.kubernetes.io/subnets: fabric-edge-public-1a, fabric-edge-public-1b
       
       # Cấu hình giao thức HTTPS và Chứng chỉ ACM TLS
       alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
       alb.ingress.kubernetes.io/certificate-arn: REPLACE_WITH_ACM_ARN
       alb.ingress.kubernetes.io/ssl-redirect: '443'
       
       # Tích hợp trực tiếp AWS WAF v2 Web ACL
       alb.ingress.kubernetes.io/wafv2-acl-arn: REPLACE_WITH_WAF_ARN
       
       # Nhãn tài nguyên
       alb.ingress.kubernetes.io/tags: Project=aws-eks-secure-network-fabric,Environment=prod
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
                 number: 8080
   ```
3. Thay thế các placeholder bằng giá trị ARN thực tế và áp dụng:
   ```bash
   sed -i "s|REPLACE_WITH_ACM_ARN|$ACM_ARN|g" fabric-edge-ingress.yaml
   sed -i "s|REPLACE_WITH_WAF_ARN|$WAF_ARN|g" fabric-edge-ingress.yaml
   kubectl apply -f fabric-edge-ingress.yaml
   ```

---

### Bước 4: Quan Sát Trạng Thái Khởi Tạo Trên AWS Console
1. Mở **EC2 Console** tại Region Singapore `ap-southeast-1` -> Menu bên trái chọn **Load Balancers**.
2. Tìm Load Balancer kiểu Application có tiền tố `k8s-fabricap-fabriced-...`:
   - **Scheme:** Xác nhận là **`internet-facing`**.
   - **VPC:** Xác nhận là **`fabric-edge-vpc`**.
   - **State:** Đợi chuyển sang màu xanh: **`Active`**.
3. Chọn tab **Listeners and rules**:
   - Listener `HTTP:80`: Hiển thị hành động `Redirect to HTTPS:443`.
   - Listener `HTTPS:443`: Hiển thị hành động `Forward to fabric-edge-tg` kèm Certificate ACM hợp lệ.
4. Chọn tab **Integrations** (hoặc cuộn xuống mục **AWS WAF**):
   - Xác nhận mục AWS WAF hiển thị Web ACL: **`fabric-edge-web-acl`** (Tích hợp thành công).
5. Tại menu bên trái, chọn **Target Groups**:
   - Nhấp vào Target Group tương ứng của ALB -> Tab **Targets**:
   - Xác nhận các Pod IPs của dịch vụ `frontend` (dải `10.40.10.x` hoặc `10.40.14.x`) ở trạng thái **`healthy`**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái Ingress và xác minh liên kết WAF qua CLI:
```bash
# 1. Kiểm tra Kubernetes Ingress và lấy Public DNS Name
kubectl get ingress fabric-edge-ingress -n fabric-apps -o wide

ALB_DNS=$(kubectl get ingress fabric-edge-ingress -n fabric-apps -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "Public ALB DNS: $ALB_DNS"

# 2. Kiểm tra ALB gắn đúng Web ACL
ALB_ARN=$(aws elbv2 describe-load-balancers --region ap-southeast-1 --query 'LoadBalancers[?DNSName==`'$ALB_DNS'`].LoadBalancerArn | [0]' --output text)
aws wafv2 get-web-acl-for-resource --region ap-southeast-1 --resource-arn $ALB_ARN --output table

# 3. Kiểm thử chuyển hướng HTTP sang HTTPS
curl -I http://$ALB_DNS

# 4. Kiểm thử kết nối HTTPS tới Frontend
curl -Ik https://$ALB_DNS
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Để gỡ bỏ Public ALB Ingress:
```bash
kubectl delete -f fabric-edge-ingress.yaml
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/07-waf/03-alb-ingress-active.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] ALB công khai được tạo thành công trên 2 Public Subnets của Edge VPC (`fabric-edge-public-1a/b`).
- [ ] Listener HTTP 80 tự động chuyển hướng HTTP 301 sang HTTPS 443.
- [ ] Listener HTTPS 443 giải mã TLS với chứng chỉ ACM hợp lệ và chuyển tiếp tới Frontend Pods.
- [ ] Web ACL `fabric-edge-web-acl` được gắn kết thành công và bảo vệ trực tiếp trên ALB.
