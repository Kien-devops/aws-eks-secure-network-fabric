# 07.01 — Yêu Cầu & Cấp Phát Chứng Chỉ Bảo Mật Số AWS Certificate Manager (ACM)

> **Mã bài lab:** `07.01`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 20 phút  
> **Chi phí ước tính:** $0.00 USD (Chứng chỉ SSL/TLS công khai cấp bởi AWS Certificate Manager là hoàn toàn miễn phí)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab tại [Module 02](../02-ha-tang-mang-co-ban/README.md) và [Module 03](../03-cum-eks-kep/README.md).
- Có một tên miền công khai quản trị trên AWS Route 53 hoặc nhà cung cấp DNS bên ngoài (Ví dụ: `fabric.yourdomain.com`). Nếu không có custom domain, có thể sử dụng Private CA hoặc self-signed certificate cho mục đích lab nội bộ.
- Đang mở phiên AWS Management Console tại Singapore `ap-southeast-1`.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để thực thi bài lab này:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "acm:RequestCertificate",
        "acm:DescribeCertificate",
        "acm:ListCertificates",
        "acm:AddTagsToCertificate",
        "acm:DeleteCertificate",
        "route53:ChangeResourceRecordSets",
        "route53:GetChange"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD. AWS Certificate Manager không tính phí cho các chứng chỉ số công khai được gắn vào các tài nguyên AWS như Application Load Balancer hay CloudFront.
- **Cảnh báo tính Zonal/Regional:** Chứng chỉ ACM phải được tạo tại đúng **Region Singapore (`ap-southeast-1`)** để gắn vào Application Load Balancer của Edge VPC. Chứng chỉ tạo tại `us-east-1` chỉ dùng được cho CloudFront, không thể gắn vào Regional ALB.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Yêu Cầu Cấp Phát Chứng Chỉ Công Khai Trên ACM Console
1. Đăng nhập **AWS Management Console**, chọn Region Singapore `ap-southeast-1`.
2. Trên thanh tìm kiếm, nhập `ACM` hoặc `Certificate Manager` và chọn **AWS Certificate Manager**.
3. Tại menu điều hướng bên trái, chọn **Certificates** -> Nhấp nút cam **Request a certificate**.
4. **Step 1 — Certificate type:**
   - Chọn **Request a public certificate**.
   - Nhấp **Next**.
5. **Step 2 — Configure certificate:**
   - **Domain names:**
     - **Fully qualified domain name (FQDN):** Nhập tên miền Ingress của bạn (ví dụ: `fabric.example.com` hoặc `*.fabric.example.com`).
     - Nhấp **Add another name to this certificate** nếu muốn thêm SANs (Subject Alternative Names).
   - **Validation method:** Chọn **DNS validation - recommended** (Xác thực qua bản ghi CNAME của Route 53, tự động gia hạn chứng chỉ hàng năm).
   - **Key algorithm:** Chọn **RSA 2048** (Tương thích cao nhất với các trình duyệt và thiết bị di động).
   - **Tags:**
     - Key: `Project` | Value: `aws-eks-secure-network-fabric`
     - Key: `Environment` | Value: `prod`
6. Nhấp nút cam **Request** ở cuối trang.

---

### Bước 2: Xác Thực Quyền Sở Hữu Tên Miền Qua Bản Ghi DNS
1. Hệ thống chuyển về danh sách **Certificates**:
   - Tìm chứng chỉ vừa yêu cầu. Quan sát cột **Status** đang hiển thị màu vàng: **`Pending validation`**.
2. Nhấp vào **Certificate ID** để mở trang chi tiết.
3. Cuộn xuống mục **Domains**:
   - Nếu tên miền được quản trị trên cùng tài khoản qua AWS Route 53:
     - Nhấp nút **Create records in Route 53** ở góc phải bảng Domains.
     - Kiểm tra các bản ghi CNAME được liệt kê -> Nhấp **Create records**.
   - Nếu tên miền được quản lý ở DNS bên ngoài (Cloudflare, GoDaddy...):
     - Sao chép giá trị **CNAME name** (ví dụ: `_a1b2c3d4...`) và **CNAME value** (ví dụ: `_x1y2z3...acm-validations.aws.`).
     - Tạo bản ghi CNAME tương ứng trên DNS Provider bên ngoài.
4. Chờ từ 1 đến 3 phút để ACM xác thực bản ghi DNS.
5. Làm mới trang, xác nhận cột **Status** chuyển sang màu xanh: **`Issued`**.
6. Sao chép lại chuỗi **Certificate ARN** (dạng `arn:aws:acm:ap-southeast-1:123456789012:certificate/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`) để cấu hình Ingress ALB trong bài lab 07.03.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái chứng chỉ số qua AWS CLI:
```bash
# 1. Liệt kê các chứng chỉ ACM tại Region Singapore
aws acm list-certificates --region ap-southeast-1 \
  --query 'CertificateSummaryList[*].{CertificateArn:CertificateArn,DomainName:DomainName}' \
  --output table

# 2. Kiểm tra chi tiết trạng thái xác thực và thời hạn của chứng chỉ
CERT_ARN=$(aws acm list-certificates --region ap-southeast-1 --query 'CertificateSummaryList[0].CertificateArn' --output text)
aws acm describe-certificate --region ap-southeast-1 --certificate-arn $CERT_ARN \
  --query 'Certificate.{Domain:DomainName,Status:Status,Type:Type,KeyAlgorithm:KeyAlgorithm,InUseBy:length(InUseBy)}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Nếu yêu cầu sai tên miền hoặc cần hủy chứng chỉ:
1. Mở ACM Console -> Chọn chứng chỉ cần xóa.
2. Nhấp menu **Actions** -> Chọn **Delete**.
3. Hoặc thực thi qua CLI:
   ```bash
   aws acm delete-certificate --region ap-southeast-1 --certificate-arn $CERT_ARN
   ```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/07-waf/01-acm-issued.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Chứng chỉ ACM chuyển sang trạng thái `ISSUED` tại Region Singapore `ap-southeast-1`.
- [ ] Phương thức xác thực là `DNS validation` với thuật toán mã hóa `RSA 2048`.
- [ ] Ghi lại thành công Certificate ARN để cấu hình TLS termination cho ALB Ingress.
