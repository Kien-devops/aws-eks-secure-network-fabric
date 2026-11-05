# Module 07: Cổng Vào Biên & Tường Lửa Ứng Dụng (Edge Ingress & AWS WAF)

## 1. Mục Tiêu Kỹ Thuật
- **Mục tiêu:**
  - Thiết lập cổng vào công khai an toàn (Edge Ingress) thông qua **Internet-facing Application Load Balancer (ALB)** đặt tại Public Subnets của `fabric-edge-vpc`.
  - Cấu hình chứng chỉ bảo mật số TLS công khai thông qua **AWS Certificate Manager (ACM)**.
  - Tích hợp **AWS WAF v2** Web ACL gắn trực tiếp vào ALB Ingress:
    - Kích hoạt nhóm quy tắc quản lý của AWS: `AWSManagedRulesCommonRuleSet` (OWASP Top 10), `AWSManagedRulesKnownBadInputsRuleSet`, `AWSManagedRulesAmazonIpReputationList`.
    - Thiết lập quy tắc giới hạn tần suất (Rate Limiting: 500 requests / 5 phút trên mỗi client IP).
  - Triển khai chiến lược chuyển đổi an toàn: **Count-to-Block** (Ban đầu chỉ đếm và log cảnh báo, sau khi xác minh không có false-positive sẽ chuyển sang chặn thực tế).
  - Thu thập toàn bộ WAF Access Logs và đẩy về CloudWatch / S3.

---

## 2. Kiến Trúc Luồng Ingress L7

```text
[Người Dùng Internet]
        | (HTTPS / Cổng 443)
        v
[Route 53 Public DNS / ACM TLS]
        |
        v
[AWS WAF v2 Web ACL]
  - Kiểm tra SQL Injection, XSS, Path Traversal
  - Kiểm tra danh tiếng IP độc hại (AWS IP Reputation)
  - Kiểm tra giới hạn tần suất (Rate Limit)
        | (Gói tin hợp lệ)
        v
[Public Application Load Balancer (ALB)]
        | (Chuyển tiếp qua Private Subnets)
        v
[Edge EKS: frontend Pods (Cổng 3000 / 8080)]
```

---

## 3. Các Bước Thực Hiện Chi Tiết

### Bước 1: Yêu Cầu Chứng Chỉ ACM TLS
Yêu cầu chứng chỉ cho tên miền public (hoặc dùng self-signed/internal cho bài lab testing):
```bash
aws acm request-certificate \
  --domain-name fabric.example.com \
  --validation-method DNS \
  --region ap-southeast-1
```

### Bước 2: Tạo AWS WAF v2 Web ACL (Chế độ Count)
1. Tạo Web ACL với phạm vi `REGIONAL` tại `ap-southeast-1`.
2. Gắn các Rule Sets mặc định với hành vi ban đầu là `Count`.
3. Tạo Rule Rate Limiting: Chặn nếu quá 500 requests / 5 phút.

### Bước 3: Triển khai AWS Load Balancer Controller trên Edge EKS
1. Gán quyền IAM Role via EKS Pod Identity cho AWS Load Balancer Controller.
2. Triển khai Ingress resource:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: edge-ingress
  namespace: default
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/wafv2-acl-arn: <WAF-ACL-ARN>
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

### Bước 4: Chuyển Đổi Sang Chế Độ Block (Count-to-Block)
Sau khi test lưu lượng bình thường không bị false-positive, cập nhật hành động của các Rule trong Web ACL từ `Count` sang `Block`.

---

## 4. Xác Minh (Verification)
1. Thử nghiệm payload độc hại mô phỏng SQL Injection:
   ```bash
   curl -Iv "https://<alb-dns-name>/?id=1'%20OR%20'1'='1"
   ```
   > Kết quả mong đợi: `HTTP 403 Forbidden` (Chặn bởi AWS WAF).
2. Kiểm tra log trên CloudWatch Logs để xác thực `action: BLOCK`.

---

## 5. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] ALB tiếp nhận traffic HTTPS cổng 443 và phân phối tới các Pod `frontend`.
- [ ] AWS WAF v2 chặn thành công payload tấn công mẫu (HTTP 403).
- [ ] Toàn bộ request độc hại có bản ghi chi tiết trong CloudWatch WAF Access Logs.

