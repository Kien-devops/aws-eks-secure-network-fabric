# 08.03 — Tạo Hóa Đơn Phần Mềm (SBOM) & Ký Số Ảnh Container Bằng Cosign

> **Trạng thái:** Hướng dẫn thực hành an ninh chuỗi cung ứng phần mềm (Software Supply Chain Security).  
> **Áp dụng cho:** Đảm bảo tính minh bạch xuất xứ (Provenance) và bảo toàn tính toàn vẹn của container images trên AWS ECR.

---

## 1. Mục Tiêu Kỹ Thuật

- Tự động tạo hóa đơn phần mềm **SBOM (Software Bill of Materials)** theo chuẩn công nghiệp **CycloneDX** hoặc **SPDX**.
- Ký số mật mã học cho hình ảnh container trên **AWS Elastic Container Registry (ECR)** bằng công cụ **Cosign** (Sigstore) kết hợp với AWS KMS.
- Lưu trữ chữ ký số và tài liệu SBOM trực tiếp cùng repository trên ECR.

---

## 2. Các Bước Thực Hiện Chi Tiết

### Bước 1: Tạo Hóa Đơn Phần Mềm (SBOM)
Sử dụng công cụ `trivy` hoặc `syft` để phân tích các thành phần phần mềm có trong ảnh:
```bash
trivy image \
  --format cyclonedx \
  --output sbom-order-service.json \
  fabric-order-service:local
```

---

### Bước 2: Đẩy Ảnh & SBOM Lên AWS ECR
1. Đăng nhập vào AWS ECR tại Region Singapore:
   ```bash
   aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.ap-southeast-1.amazonaws.com
   ```
2. Tag ảnh bằng SHA digest và push:
   ```bash
   docker tag fabric-order-service:local 123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-order-service:v1.0.0
   docker push 123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-order-service:v1.0.0
   ```
3. Đính kèm SBOM vào ảnh trên ECR bằng Cosign:
   ```bash
   cosign attest --predicate sbom-order-service.json --type cyclonedx --key awskms:///arn:aws:kms:ap-southeast-1:123456789012:key/fabric-signing-key 123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-order-service:v1.0.0
   ```

---

### Bước 3: Ký Số Ảnh Container Bằng Cosign & AWS KMS
Thực hiện ký số bảo vệ tính toàn vẹn:
```bash
cosign sign --key awskms:///arn:aws:kms:ap-southeast-1:123456789012:key/fabric-signing-key 123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-order-service:v1.0.0
```

---

## 3. Xác Minh (Verification)

Kiểm tra xác thực chữ ký số bằng Cosign:
```bash
cosign verify --key awskms:///arn:aws:kms:ap-southeast-1:123456789012:key/fabric-signing-key 123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-order-service:v1.0.0
```
> Kết quả: `Verification for 123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-order-service:v1.0.0 -- OK!`.

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] File SBOM chuẩn CycloneDX được sinh ra thành công.
- [ ] Chữ ký số Cosign được lưu trữ hợp lệ trên AWS ECR và xác thực thành công.

