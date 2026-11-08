# 08.03 — Đặc Tả Tạo Hóa Đơn Phần Mềm (SBOM) & Ký Số Ảnh Container Bằng Cosign

> **Mã bài lab:** `08.03`
> **Trạng thái tài liệu:** `READY_TO_RUN`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/08-devsecops/03-cosign-verification.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả quy trình sinh hóa đơn thành phần phần mềm (SBOM CycloneDX) và ký số mật mã học cho các container images bất biến bằng Cosign kết hợp khóa bất đối xứng AWS KMS nhằm bảo vệ chuỗi cung ứng phần mềm trước khi triển khai vào cụm EKS.

---

## 2. Tài Nguyên (Resources)

| Tên Tài Nguyên | Loại Resource | Vị Trí / Khu Vực | Runtime ID / ARN |
| :--- | :--- | :--- | :--- |
| `alias/fabric-cosign-signing-key` | `AWS::KMS::Key` (Asymmetric) | Regional (`ap-southeast-1`) | Key Spec: `ECC_NIST_P256`, Usage: `SIGN_VERIFY` |
| `fabric-core-service` | `AWS::ECR::Repository` | Regional (`ap-southeast-1`) | `123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-core-service` |
| `fabric-edge-frontend` | `AWS::ECR::Repository` | Regional (`ap-southeast-1`) | `123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-edge-frontend` |
| SBOM Artifacts | `Artifact::CycloneDX` | ECR / Evidence | `sbom-core-service.json`, `sbom-edge-frontend.json` |

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-cosign-signing-key` | Khóa ký số AWS KMS |
| `Project` | `aws-eks-secure-network-fabric` | Khóa KMS, ECR Repositories |
| `Environment` | `prod` | Khóa KMS, ECR Repositories |
| `ManagedBy` | `manual` | Quản trị chữ ký và SBOM thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Cấu Hình Khóa Ký Số Bất Đối Xứng AWS KMS

- **Key Type:** `Asymmetric` (Khóa bất đối xứng).
- **Key Usage:** `SIGN_VERIFY` (Ký và xác thực chữ ký).
- **Key Spec:** `ECC_NIST_P256` (Elliptic Curve Cryptography chuẩn NIST P-256).
- **Key Policy:** Cấp quyền `kms:Sign` cho CI/CD pipeline và `kms:GetPublicKey`, `kms:Verify` cho các bên xác thực.

### 4.2 Cấu Hình Ký Số & Đính Kèm SBOM

- **Sinh SBOM:** Sử dụng Trivy/Syft xuất định dạng `cyclonedx-json` từ chính xác Image Digest đã đẩy lên ECR.
- **Ký Số Cosign:** `cosign sign --key awskms:///$KMS_KEY_ARN $IMAGE_URI`
- **Đính kèm Attestation:** `cosign attest --predicate sbom-*.json --type cyclonedx --key awskms:///$KMS_KEY_ARN $IMAGE_URI`
- **Chính sách ECR Immutability:** Kích hoạt thuộc tính `imageTagMutability: IMMUTABLE` trên cả hai kho chứa ECR để ngăn chặn ghi đè tag.

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `08.02`: Container images phải vượt qua bài kiểm tra lỗ hổng của Trivy (0 Critical, 0 High).
- Phụ thuộc vào ECR Repositories của `fabric-core-service` và `fabric-edge-frontend`.
- Là điều kiện tiên quyết bắt buộc trước khi tạo PR cập nhật digest bất biến vào kho GitOps tại `08.04`.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng thái Khóa KMS** | `aws kms describe-key --key-id alias/fabric-cosign-signing-key` | `KeyState: Enabled`, `KeySpec: ECC_NIST_P256`. |
| **Xác thực Chữ Ký Cosign** | `cosign verify --key awskms:///$KMS_KEY_ARN $IMAGE_URI` | Trả về `Verification for <URI> -- OK!` |
| **Xác thực SBOM Attestation** | `cosign verify-attestation --type cyclonedx --key awskms:///$KMS_KEY_ARN $IMAGE_URI` | Trả về bản ghi attestation hợp lệ khớp với digest của image. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo tính toàn vẹn:** Không xóa khóa KMS đang dùng để ký các release đang chạy trên production. Nếu xóa khóa, hệ thống sẽ mất khả năng xác thực nguồn gốc artifact.
- **Quy trình Rollback:**
  ```bash
  # Lên lịch xóa khóa KMS nếu khởi tạo sai thuật toán
  aws kms schedule-key-deletion --region ap-southeast-1 --key-id <KeyId> --pending-window-in-days 7
  ```
