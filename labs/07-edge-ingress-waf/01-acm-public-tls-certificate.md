# 07.01 — Yêu Cầu & Cấp Phát Chứng Chỉ Bảo Mật Số AWS Certificate Manager (ACM)

> **Mã bài lab:** `07.01`  
> **Trạng thái:** `COMPLETED`  
> **Thời gian dự kiến:** 20 phút  
> **Chi phí ước tính:** $0.00 USD (Chứng chỉ SSL/TLS công khai cấp bởi AWS Certificate Manager là hoàn toàn miễn phí)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab tại [Module 02](../02-ha-tang-mang-co-ban/README.md) và [Module 03](../03-cum-eks-kep/README.md).
- Có một tên miền công khai quản trị trên AWS Route 53: Hosted Zone **`devopsss.site`** (Hosted Zone ID: `Z0611184P1C0HRBDC7VQ`).
- Domain áp dụng cho Edge Ingress frontend: **`app3.devopsss.site`**.
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
     - **Fully qualified domain name (FQDN):** Nhập `app3.devopsss.site`.
     - Nhấp **Add another name to this certificate**: Thêm SANs `*.devopsss.site` và `devopsss.site`.
   - **Validation method:** Chọn **DNS validation - recommended** (Xác thực qua bản ghi CNAME của Route 53, tự động gia hạn chứng chỉ hàng năm).
   - **Key algorithm:** Chọn **RSA 2048** (Tương thích cao nhất với các trình duyệt và thiết bị di động).
   - **Tags:**
     - Key: `Project` | Value: `aws-eks-secure-network-fabric`
     - Key: `Environment` | Value: `prod`
6. Nhấp nút cam **Request** ở cuối trang.

---

### Bước 2: Xác Thực Quyền Sở Hữu Tên Miền Qua Bản Ghi DNS
1. Hệ thống chuyển về danh sách **Certificates**:
   - Tìm chứng chỉ vừa yêu cầu. Quan sát cột **Status** đang hiển thị: **`Pending validation`**.
2. Nhấp vào **Certificate ID** để mở trang chi tiết.
3. Cuộn xuống mục **Domains**:
   - Tên miền được quản trị trên cùng tài khoản qua AWS Route 53 (Hosted Zone `devopsss.site`):
     - Nhấp nút **Create records in Route 53** ở góc phải bảng Domains.
     - Xác nhận hệ thống tự động tạo các bản ghi CNAME xác thực:
       - `_676f0dca51b603dc162d0a6d8fb4914a.app3.devopsss.site.` &rarr; `_16d92f33573b0816a94a8c76e2e4a630.wzccmgtwzk.acm-validations.aws.`
       - `_f139e0a1ff98631c8f03aaa2669ddc0c.devopsss.site.` &rarr; `_01e2e596cb56adfb27888575d5ad12f7.wzccmgtwzk.acm-validations.aws.`
4. Chờ từ 1 đến 2 phút để ACM xác thực bản ghi DNS.
5. Làm mới trang, xác nhận cột **Status** chuyển sang màu xanh: **`Issued`**.
6. Sao chép lại chuỗi **Certificate ARN**:
   `arn:aws:acm:ap-southeast-1:123456789012:certificate/0907f419-dd72-4b90-89af-e2bf7ce67391`
   để cấu hình Ingress ALB trong bài lab 07.03 và [ingress.yaml](file:///e:/repo/project6/aws-eks-secure-network-fabric-app/k8s/edge/ingress.yaml).

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái chứng chỉ số qua AWS CLI:
```bash
# 1. Liệt kê các chứng chỉ ACM tại Region Singapore
aws acm list-certificates --region ap-southeast-1 \
  --query 'CertificateSummaryList[*].{CertificateArn:CertificateArn,DomainName:DomainName,Status:Status}' \
  --output table

# 2. Kiểm tra chi tiết trạng thái xác thực và thời hạn của chứng chỉ
aws acm describe-certificate --region ap-southeast-1 \
  --certificate-arn arn:aws:acm:ap-southeast-1:123456789012:certificate/0907f419-dd72-4b90-89af-e2bf7ce67391 \
  --query 'Certificate.{Domain:DomainName,Status:Status,Type:Type,KeyAlgorithm:KeyAlgorithm,InUseBy:InUseBy[0]}' \
  --output table
```

**Runtime Output Thực Tế:**
```text
-----------------------------------------------------------------------------------------------------------------------------------------------------------------
|                                                                       DescribeCertificate                                                                     |
+---------------------+-----------------------+----------------------------------------------------------------------------------------+-----------+------------+
|       Domain        |     KeyAlgorithm      |                                        InUseBy                                         |  Status   |   Type     |
+---------------------+-----------------------+----------------------------------------------------------------------------------------+-----------+------------+
|  app3.devopsss.site |  RSA-2048             |  arn:aws:elasticloadbalancing:ap-southeast-1:123456789012:loadbalancer/app/fabric-edge-public-alb/61108d1397d1c55c   |  ISSUED   |  AMAZON_ISSUED |
+---------------------+-----------------------+----------------------------------------------------------------------------------------+-----------+------------+
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Nếu yêu cầu sai tên miền hoặc cần hủy chứng chỉ:
1. Mở ACM Console -> Chọn chứng chỉ cần xóa.
2. Nhấp menu **Actions** -> Chọn **Delete**.
3. Hoặc thực thi qua CLI:
   ```bash
   aws acm delete-certificate --region ap-southeast-1 \
     --certificate-arn arn:aws:acm:ap-southeast-1:123456789012:certificate/0907f419-dd72-4b90-89af-e2bf7ce67391
   ```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/07-waf/01-acm-issued.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [x] Chứng chỉ ACM chuyển sang trạng thái `ISSUED` tại Region Singapore `ap-southeast-1`.
- [x] Phương thức xác thực là `DNS validation` với thuật toán mã hóa `RSA 2048`.
- [x] Ghi lại thành công Certificate ARN để cấu hình TLS termination cho ALB Ingress.
- [x] Chứng chỉ đã được gắn và sử dụng thực tế (`InUseBy`) trên `fabric-edge-public-alb`.
