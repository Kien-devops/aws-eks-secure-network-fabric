# Module 07: Cổng Vào Biên & Tường Lửa Ứng Dụng (Edge Ingress & AWS WAF)

Module này cung cấp các đặc tả tài nguyên triển khai cổng vào công khai an toàn (Edge Ingress) thông qua Application Load Balancer đặt tại Public Subnets của Edge VPC, kết hợp mã hóa TLS bằng chứng chỉ ACM, quản lý Ingress tự động bằng AWS Load Balancer Controller và bảo vệ tầng L7 bằng AWS WAFv2 Web ACL theo quy trình chuyển đổi an toàn Count-to-Block.

---

## 1. Sơ Đồ Kiến Trúc Luồng Ingress L7

```text
[Người Dùng Internet]
        │ (HTTPS / Cổng 443)
        ▼
[Route 53 Public DNS: app3.devopsss.site]
        │
        ▼
[AWS Certificate Manager: ACM TLS RSA-2048]
        │
        ▼
[AWS WAF v2 Regional Web ACL: fabric-edge-web-acl]
  ├── Priority 0: Rate Limit Rule (500 req/5m -> Block 429)
  ├── Priority 1: AWSManagedRulesCommonRuleSet (OWASP Top 10 -> Block 403)
  ├── Priority 2: AWSManagedRulesKnownBadInputsRuleSet (Log4j, Traversal -> Block 403)
  └── Priority 3: AWSManagedRulesAmazonIpReputationList (Threat Intel -> Block 403)
        │ (Traffic Hợp Lệ)
        ▼
[Public ALB: fabric-edge-public-alb] (Public Subnets A/B)
  ├── Listener HTTP:80 -> Redirect HTTP 301 sang HTTPS:443
  └── Listener HTTPS:443 -> Forward sang Target Group (target-type: ip)
        │
        ▼
[Edge EKS: edge-frontend Pods (TCP 8080)] (Private Node Subnets A/B)
```

---

## 2. Thứ Tự Phụ Thuộc (Dependency Tree)

```text
07.01 (Yêu cầu & cấp phát chứng chỉ ACM TLS: app3.devopsss.site)
  │
  ├──> 07.02 (Khởi tạo AWS WAFv2 Web ACL: fabric-edge-web-acl ở chế độ Count)
  │      │
  │      └──> 07.03 (Triển khai Internet-facing ALB Ingress tích hợp ACM & WAF)
  │             │
  └─────────────┴──> 07.04 (Quy trình chuyển đổi Count-to-Block & Kiểm thử tấn công L7)
```

---

## 3. Danh Mục Tài Nguyên (Resource Catalog)

| Tài Nguyên | Loại Resource | Số Lượng | Ghi Chú Kỹ Thuật |
| :--- | :--- | :---: | :--- |
| **ACM Certificate** | `AWS::CertificateManager::Certificate` | 1 | `app3.devopsss.site` (RSA 2048, DNS validated, Status: ISSUED) |
| **Route 53 Public Zone** | `AWS::Route53::HostedZone` | 1 | `devopsss.site` (`Z0611184P1C0HRBDC7VQ`) |
| **WAF Web ACL** | `AWS::WAFv2::WebACL` | 1 | `fabric-edge-web-acl` (ID: `a010b9c0-edfa-4ba4-bfb0-8691ae8ecf56`) |
| **WAF Rules** | `AWS::WAFv2::Rule` / `ManagedRuleGroup` | 4 | Rate limit (429) + 3 AWS Managed Rule Sets (403) |
| **Public ALB** | `AWS::ElasticLoadBalancingV2::LoadBalancer` | 1 | `fabric-edge-public-alb` (Scheme: internet-facing, Dual-AZ) |
| **ALB Listeners** | `AWS::ElasticLoadBalancingV2::Listener` | 2 | Port 80 (HTTP 301 redirect) và Port 443 (HTTPS forward) |
| **Target Group** | `AWS::ElasticLoadBalancingV2::TargetGroup` | 1 | Target type IP, Port 8080 (Pods `edge-frontend`) |
| **CloudWatch Log Group** | `AWS::Logs::LogGroup` | 1 | `aws-waf-logs-fabric-edge-waf` (L7 WAF inspection logs) |

---

## 4. Danh Sách 4 Bài Lab Đặc Tả Chi Tiết

| Mã Lab | Tên Đặc Tả & Nội Dung Trọng Tâm | Trạng Thái | File Đặc Tả |
|---|---|:---:|---|
| **07.01** | **Yêu Cầu & Cấp Phát Chứng Chỉ ACM:** Chứng chỉ số công khai cho `app3.devopsss.site`. | `RUNTIME_PASS` | [01-acm-public-tls-certificate.md](01-acm-public-tls-certificate.md) |
| **07.02** | **AWS WAF v2 Web ACL Setup:** Khởi tạo Web ACL với 4 nhóm rules ở chế độ Count an toàn. | `RUNTIME_PASS` | [02-aws-wafv2-web-acl-setup.md](02-aws-wafv2-web-acl-setup.md) |
| **07.03** | **Internet-facing ALB Ingress:** AWS LB Controller cấp phát ALB tích hợp ACM TLS và WAF. | `RUNTIME_PASS` | [03-internet-facing-alb-ingress.md](03-internet-facing-alb-ingress.md) |
| **07.04** | **Count-to-Block Transition & Attack Tests:** Cắt chuyển sang Block và xác minh chặn L7 (403/429). | `RUNTIME_PASS` | [04-waf-count-to-block-transition.md](04-waf-count-to-block-transition.md) |
