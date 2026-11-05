# 07.01 — Yêu Cầu & Cấp Phát Chứng Chỉ Bảo Mật Số AWS Certificate Manager (ACM)

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Thiết lập chứng chỉ số TLS cho Application Load Balancer tiếp nhận kết nối công khai từ Internet tại Singapore.

---

## 1. Mục Tiêu Kỹ Thuật

- Yêu cầu cấp phát chứng chỉ số công khai **AWS Certificate Manager (ACM)** tại Region Singapore (`ap-southeast-1`).
- Cấu hình phương thức xác thực quyền sở hữu tên miền qua DNS (DNS Validation).
- Chuẩn bị sẵn sàng ARN của chứng chỉ để gắn vào Application Load Balancer Ingress.

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Yêu Cầu Chứng Chỉ Công Khai
1. Mở dịch vụ **AWS Certificate Manager (ACM)** tại Region Singapore (`ap-southeast-1`).
2. Nhấp nút cam **Request a certificate** -> Chọn **Request a public certificate** -> Nhấp **Next**.
3. **Domain names:**
   - **Fully qualified domain name:** Nhập tên miền của bạn (ví dụ: `fabric.yourdomain.com` hoặc `*.fabric.yourdomain.com`).
4. **Validation method:** Chọn **DNS validation - recommended**.
5. **Key algorithm:** Chọn `RSA 2048`.
6. **Tags:** `Project` = `aws-eks-secure-network-fabric`, `Environment` = `dev`.
7. Nhấp nút cam **Request**.

---

### Bước 2: Xác Thực Quyền Sở Hữu Qua DNS
1. Tại danh sách **Certificates**, nhấp vào Certificate ID vừa yêu cầu (trạng thái đang là `Pending validation`).
2. Tại mục **Domains**, quan sát bảng chứa:
   - **CNAME name:** Chuỗi định danh ngẫu nhiên (ví dụ: `_a1b2c3...`).
   - **CNAME value:** Chuỗi đích đến (ví dụ: `_x1y2z3...acm-validations.aws.`).
3. Nếu bạn quản lý DNS trên Route 53:
   - Nhấp trực tiếp vào nút **Create records in Route 53** -> Nhấp **Create records**.
4. Chờ từ 1 - 3 phút để ACM kiểm tra bản ghi CNAME và chuyển trạng thái sang **Issued**.

---

## 3. Xác Minh (Verification)

Kiểm tra trạng thái chứng chỉ qua AWS CLI:
```bash
aws acm list-certificates \
  --region ap-southeast-1 \
  --query 'CertificateSummaryList[?DomainName==`fabric.yourdomain.com`].{Arn:CertificateArn,Status:Status}' \
  --output table
```
> Kết quả: `Status = ISSUED`.

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Chứng chỉ ACM chuyển sang trạng thái `ISSUED` tại Region `ap-southeast-1`.
- [ ] Ghi lại ARN của chứng chỉ để cấu hình cho Ingress ALB ở bài sau.

