# 08.03 — Tạo Hóa Đơn Phần Mềm (SBOM) & Ký Số Ảnh Container Bằng Cosign

> **Mã bài lab:** `08.03`  
> **Trạng thái:** `DRAFT`  
> **Thời gian dự kiến:** 40 phút  
> **Chi phí ước tính:** ~$1.00 USD / tháng cho AWS KMS Asymmetric Key  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bài lab [08.02](02-trivy-container-vulnerability-scan.md). Ảnh container đã vượt qua kiểm tra không có lỗ hổng HIGH/CRITICAL.
- Đã cài đặt công cụ **Cosign** (Sigstore CLI) và **Syft** (hoặc Trivy) trên máy trạm.
- Đang mở phiên AWS Management Console tại Singapore `ap-southeast-1`.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để tạo khóa ký KMS và đẩy chữ ký số lên ECR:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kms:CreateKey",
        "kms:CreateAlias",
        "kms:DescribeKey",
        "kms:Sign",
        "kms:Verify",
        "kms:GetPublicKey",
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Khóa KMS Asymmetric Key tính phí $1.00 USD/tháng. Phí ký số Cosign theo số lượng request KMS (~$0.03/10,000 requests).
- **Giới hạn supply chain:** Chữ ký và SBOM không đủ đạt SLSA Level 3; cần provenance và build isolation được đánh giá riêng. Kyverno/Gatekeeper admission chưa được triển khai: chữ ký hiện là gate xác minh trước promotion, chưa phải bằng chứng cluster tự chặn unsigned images.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console & Terminal (Console Walkthrough)

### Bước 1: Khởi Tạo Khóa Ký Số Bất Đối Xứng AWS KMS (Asymmetric Key)
1. Đăng nhập vào **AWS Management Console**, chọn Region Singapore `ap-southeast-1`.
2. Trên thanh tìm kiếm, nhập `KMS` và chọn **AWS Key Management Service**.
3. Tại menu điều hướng bên trái, chọn **Customer managed keys** -> Nhấp nút cam **Create key**.
4. **Step 1 — Configure key:**
   - Key type: Chọn **Asymmetric**.
   - Key usage: Chọn **Sign and verify**.
   - Key spec: chọn **ECC_NIST_P256**, usage SIGN_VERIFY; ghim Cosign version hỗ trợ AWS KMS.
   - Regionality: Chọn **Single-Region key**.
   - Nhấp **Next**.
5. **Step 2 — Add labels:**
   - **Alias:** Nhập `alias/fabric-cosign-signing-key`.
   - **Description:** Nhập `Asymmetric KMS key for Cosign container image signing in Singapore`.
   - **Tags:** Key: `Project` | Value: `aws-eks-secure-network-fabric`.
   - Nhấp **Next**.
6. **Step 3 & 4 — Administrators & Users:**
   - Chọn IAM User/Role của bạn để có quyền gọi API `kms:Sign` và `kms:GetPublicKey`.
   - Nhấp **Next** -> Nhấp **Finish**.
7. Sao chép lại chuỗi **Key ARN** (dạng `arn:aws:kms:ap-southeast-1:123456789012:key/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).

---

### Bước 2: Sinh Hóa Đơn Phần Mềm (SBOM) Theo Chuẩn CycloneDX
Mở terminal, chạy lệnh phân tích thành phần phần mềm của container image:
```bash
# Sử dụng Syft hoặc Trivy để sinh file SBOM chuẩn CycloneDX JSON
trivy image \
  --format cyclonedx \
  --output sbom-order-service.json \
  fabric-order-service:local
```
Kiểm tra cấu trúc file: Xác nhận chứa đầy đủ thông tin về các gói OS (Alpine/AmazonLinux), thư viện npm/python, và các checksum SHA256.

---

### Bước 3: Đăng Nhập & Đẩy Ảnh Lên Amazon ECR Bằng Digest
Trước login: ECR → Private repositories → Create repository → `fabric-order-service` → tag immutability **Immutable** → encryption AES-256 hoặc CMK được phép → Create. Lặp cho 5 services. Tag release phải duy nhất (ưu tiên commit SHA); ví dụ `v1.0.0` chỉ dùng lần đầu, không ghi đè artifact đã scan.
1. Đăng nhập Docker CLI vào ECR Singapore (thay `123456789012` bằng Account ID thực tế):
   ```bash
   aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.ap-southeast-1.amazonaws.com
   ```
2. Gắn tag và đẩy image lên repository ECR:
   ```bash
   ECR_REPO="123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-order-service"
   docker tag fabric-order-service:local $ECR_REPO:v1.0.0
   docker push $ECR_REPO:v1.0.0
   ```
3. Lấy mã băm bất biến (Immutable SHA256 Digest) của image vừa push:
   ```bash
   IMAGE_DIGEST=$(aws ecr describe-images --region ap-southeast-1 --repository-name fabric-order-service --image-ids imageTag=v1.0.0 --query 'imageDetails[0].imageDigest' --output text)
   IMAGE_URI="$ECR_REPO@$IMAGE_DIGEST"
   echo "Target Image URI: $IMAGE_URI"
   ```

---

### Bước 4: Ký Số Mật Mã Học Bằng Cosign & AWS KMS Key
1. Sử dụng Cosign ký số trực tiếp lên image digest thông qua AWS KMS:
   ```bash
   KMS_KEY_ARN=$(aws kms describe-key --region ap-southeast-1 --key-id alias/fabric-cosign-signing-key --query 'KeyMetadata.Arn' --output text)
   
   cosign sign --key awskms:///$KMS_KEY_ARN $IMAGE_URI
   ```
2. Sinh lại SBOM từ **đúng digest đã push**, đối chiếu scan cùng digest: `trivy image --format cyclonedx --output sbom-order-service.json "$IMAGE_URI"`. Sau đó đính kèm SBOM Attestation vào ECR:
   ```bash
   cosign attest --predicate sbom-order-service.json --type cyclonedx --key awskms:///$KMS_KEY_ARN $IMAGE_URI
   ```

Trước attest, sinh SBOM từ **đúng digest đã push**: `trivy image --format cyclonedx --output sbom-order-service.json "$IMAGE_URI"`; đối chiếu report scan cùng digest. Cosign artifacts/referrers hiển thị tùy version, không bắt buộc tag `.sig/.att`; kết quả verify là nguồn xác nhận.

---

### Bước 5: Kiểm Tra Kết Quả Chữ Ký Trên Amazon ECR Console
1. Mở **Amazon ECR Console** tại Singapore `ap-southeast-1`.
2. Nhấp vào repository **`fabric-order-service`**.
3. Quan sát danh sách Artifacts trong repository:
   - Dòng 1: Tag `v1.0.0` (Image container chính).
   - Dòng 2: Tag dạng `sha256-xxxxxx.sig` (Artifact chứa chữ ký số của Cosign).
   - Dòng 3: Tag dạng `sha256-xxxxxx.att` (Artifact chứa SBOM attestation).
   - Xác nhận cả 3 thành phần đều được lưu trữ an toàn trên ECR.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Xác minh tính hợp lệ của chữ ký số bằng Cosign:
```bash
# Xác thực chữ ký số bằng Public Key từ AWS KMS
cosign verify --key awskms:///$KMS_KEY_ARN $IMAGE_URI
cosign verify-attestation --type cyclonedx --key awskms:///$KMS_KEY_ARN $IMAGE_URI
```
**Kết quả kỳ vọng:**
`Verification for 123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-order-service@sha256:... -- OK!`
`[{"critical":{"identity":{"docker-reference":"..."},"image":{"docker-manifest-digest":"sha256:..."},"type":"cosign container image signature"}}]`

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Nếu ký/attest sai digest: dừng promotion, kiểm tra lại digest, scan/SBOM rồi ký lại artifact đúng. Git revert về digest đã verify khi cần rollback triển khai. Không xóa khóa để “hoàn tác chữ ký”: có thể làm mất khả năng verify các releases cũ.

Nếu key spec sai và khóa chỉ mới tạo riêng cho phiên lab, tạo khóa đúng, giữ khóa cũ cho các artifacts còn cần kiểm tra. Chỉ lên lịch xóa trong cleanup được phép sau khi kiểm kê toàn bộ consumers; KMS → Customer managed keys → chọn đúng key ID → Key actions → Schedule key deletion → chọn recovery window, ghi ngày/owner. Khóa dùng chung hoặc đang ký releases không được xóa.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/08-devsecops/03-cosign-verification.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Khóa KMS Asymmetric Key `alias/fabric-cosign-signing-key` ở trạng thái `Enabled` với chức năng `Sign and verify`.
- [ ] File SBOM chuẩn CycloneDX được sinh ra thành công không có lỗi cú pháp.
- [ ] Chữ ký số Cosign và SBOM Attestation được đẩy thành công lên Amazon ECR.
- [ ] Lệnh `cosign verify` trả về kết quả xác thực thành công `OK`.
