# 07.01 — Đặc Tả Yêu Cầu & Cấp Phát Chứng Chỉ Bảo Mật Số AWS Certificate Manager (ACM)

> **Mã bài lab:** `07.01`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/07-waf/01-acm-issued.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả chứng chỉ số công khai SSL/TLS do AWS Certificate Manager (ACM) cấp phát tại Region Singapore thông qua cơ chế xác thực DNS Route 53 tự động nhằm kích hoạt mã hóa HTTPS và chấm dứt TLS an toàn trên Application Load Balancer Ingress.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Vị Trí / Khu Vực | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-ingress-acm-cert` (`app3.devopsss.site`) | `AWS::CertificateManager::Certificate` | Regional (`ap-southeast-1`) | `arn:aws:acm:ap-southeast-1:123456789012:certificate/0907f419-dd72-4b90-89af-e2bf7ce67391` |
| `devopsss.site` (Hosted Zone) | `AWS::Route53::HostedZone` (Public) | Global | Zone ID: `Z0611184P1C0HRBDC7VQ` |
| Bản ghi DNS CNAME Validation | `AWS::Route53::RecordSet` | Route 53 Public Zone | Bản ghi CNAME xác thực ACM tự sinh |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-ingress-acm-cert` | ACM Certificate |
| `Project` | `aws-eks-secure-network-fabric` | ACM Certificate |
| `Environment` | `prod` | ACM Certificate |
| `ManagedBy` | `manual` | Quản trị chứng chỉ số thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Thuộc Tính Chứng Chỉ ACM

- **Primary Domain Name (FQDN):** `app3.devopsss.site`
- **Subject Alternative Names (SANs):** `*.devopsss.site`, `devopsss.site`
- **Validation Method:** `DNS` (Tạo bản ghi CNAME trên Route 53 để ACM tự động gia hạn hàng năm).
- **Key Algorithm:** `RSA_2048` (Bảo đảm tương thích 100% với các HTTP client và TLS handshakes).
- **Region:** Bắt buộc tại `ap-southeast-1` (Singapore) để gắn trực tiếp vào Regional ALB.

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào Route 53 Public Hosted Zone `devopsss.site` đã kích hoạt và sẵn sàng ghi nhận DNS records.
- Là điều kiện tiên quyết cho việc gắn listener HTTPS 443 trên Internet-facing ALB tại `07.03`.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng thái Chứng chỉ** | `aws acm describe-certificate --certificate-arn <CertArn>` | `Status: ISSUED`, `Type: AMAZON_ISSUED`. |
| **Thuật toán Khóa** | Kiểm tra trường `KeyAlgorithm` | Giá trị là `RSA-2048`. |
| **Sử dụng Thực tế** | Kiểm tra trường `InUseBy` | Chứa ARN của `fabric-edge-public-alb`. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo tính tương thích Vùng:** Chứng chỉ tạo ở `us-east-1` không thể gắn vào ALB ở `ap-southeast-1`. Chứng chỉ phải được tạo tại cùng Region với Application Load Balancer.
- **Quy trình Rollback:**
  ```bash
  # Xóa chứng chỉ số ACM (Sau khi gỡ khỏi ALB listener)
  aws acm delete-certificate --region ap-southeast-1 \
    --certificate-arn arn:aws:acm:ap-southeast-1:123456789012:certificate/0907f419-dd72-4b90-89af-e2bf7ce67391
  ```
