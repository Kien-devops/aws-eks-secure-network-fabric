# Module 08: Tự Động Hóa CI/CD & Bảo Mật Chuỗi Cung Ứng (DevSecOps)

## 1. Mục Tiêu Kỹ Thuật
- **Mục tiêu:**
  - Thiết lập quy trình kiểm thử tự động (CI) cho hạ tầng Terraform và mã nguồn container.
  - Quét an ninh cấu hình IaC bằng **Checkov** và `terraform validate` để ngăn ngừa lỗi cấu hình (misconfigurations) trước khi deploy.
  - Quét lỗ hổng bảo mật trong hình ảnh container bằng **Trivy** (chặn các lỗ hổng CRITICAL và HIGH có sẵn bản vá).
  - Tự động tạo hóa đơn phần mềm **SBOM (Software Bill of Materials)** theo định dạng CycloneDX / SPDX.
  - Ký số ảnh container bằng **Cosign** (Sigstore).
  - Đảm bảo 100% workloads triển khai trên Kubernetes sử dụng **Immutable Digest (`@sha256:...`)**, cấm tuyệt đối dùng tag nổi (`:latest`).
  - Thiết lập quy trình cập nhật GitOps tự động qua Pull Request (PR) an toàn.

---

## 2. Quy Trình Pipeline CI/CD Chuẩn Doanh Nghiệp

```text
[Mã nguồn / Terraform]
        |
        v
[1. Kiểm tra Cú pháp & Format] --> terraform fmt -check & terraform validate
        |
        v
[2. Quét An ninh IaC]           --> Checkov (Kiểm tra SG 0.0.0.0/0, mã hóa KMS)
        |
        v
[3. Build Container Image]      --> docker build -t service:tag
        |
        v
[4. Quét Lỗ hổng Container]     --> Trivy Scan (--severity HIGH,CRITICAL --exit-code 1)
        |
        v
[5. Xuất SBOM]                  --> syft packages docker:service:tag -o cyclonedx-json
        |
        v
[6. Push & Ký Số Ảnh]           --> docker push ECR & cosign sign <image-digest>
        |
        v
[7. GitOps PR Handoff]          --> Tự động tạo PR cập nhật digest bất biến vào repo GitOps
```

---

## 3. Các Bước Thực Hiện Chi Tiết

### Bước 1: Quét An Ninh Hạ Tầng Terraform với Checkov
Chạy kiểm tra trong repo hạ tầng:
```bash
checkov -d terraform/ --framework terraform --check CKV_AWS_*
```
*Đảm bảo các quy tắc an ninh mạng (như không mở port 22/3389 ra 0.0.0.0/0, bật VPC Flow Logs) đều đạt chuẩn PASS.*

### Bước 2: Quét Ảnh Container & Chặn Lỗ Hổng Nguy Hiểm với Trivy
```bash
trivy image --severity HIGH,CRITICAL --exit-code 1 <image-uri-ghim-digest>
```

### Bước 3: Tạo SBOM & Ký Số Ảnh với Cosign
1. Tạo SBOM:
   ```bash
   trivy image --format cyclonedx --output sbom.json <image-uri>
   ```
2. Ký số ảnh trên AWS ECR:
   ```bash
   cosign sign --key <kms-arn> <ecr-repo-uri>@sha256:<digest>
   ```

### Bước 4: Ghim Digest Bất Biến Vào Manifest K8s
Manifest triển khai trong `gitops/` bắt buộc phải có dạng:
```yaml
spec:
  containers:
  - name: order-service
    image: 123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-order-service@sha256:a1b2c3d4e5f6...
```

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Pipeline CI hoàn tất kiểm tra cú pháp Terraform và vượt qua kiểm định an ninh Checkov.
- [ ] Không có lỗ hổng mức CRITICAL/HIGH chưa vá tồn tại trong ảnh container triển khai.
- [ ] File SBOM và chữ ký Cosign được lưu trữ kèm theo ảnh trên ECR.
- [ ] Toàn bộ Deployment manifests trong GitOps sử dụng immutable digest `@sha256:...`.

