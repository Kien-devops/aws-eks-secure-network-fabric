# Module 08: Tự Động Hóa CI/CD & Bảo Mật Chuỗi Cung Ứng (DevSecOps)

Module này cung cấp các đặc tả kỹ thuật triển khai quy trình kiểm thử tự động (CI/CD) cho hạ tầng Terraform và mã nguồn container, quét tĩnh an ninh IaC bằng Checkov, quét lỗ hổng container bằng Trivy, ký số mật mã học bằng Cosign và khóa mã băm bất biến (@sha256:...) qua GitOps.

---

## 1. Sơ Đồ Quy Trình Pipeline CI/CD Chuẩn Doanh Nghiệp

```text
[Mã nguồn Go / Dockerfile]
        │
        ▼
[1. Kiểm Tra Cú Pháp & Unit Tests] ──> go test -v ./... (Pass 100%)
        │
        ▼
[2. Build Container Image Cục Bộ]  ──> Alpine 3.20.3 Minimal Base
        │
        ▼
[3. Quét Lỗ Hổng Bằng Trivy]        ──> 0 CRITICAL, 0 HIGH (Security Gate Pass)
        │
        ▼
[4. Đẩy Ảnh Lên Amazon ECR]        ──> Trích xuất SHA256 Immutable Digest
        │
        ▼
[5. Ký Số Cosign & Đính Kèm SBOM]  ──> AWS KMS ECC_NIST_P256 Asymmetric Key
        │
        ▼
[6. Thăng Hạng GitOps Tự Động]      ──> Bot tạo PR cập nhật K8s Manifest [skip ci]
        │
        ▼
[7. Đồng Bộ Cụm EKS Qua Argo CD]   ──> Pods chạy chính xác Digest đã ký
```

---

## 2. Thứ Tự Phụ Thuộc (Dependency Tree)

```text
08.01 (Kiểm thử Terraform & Quét An ninh IaC bằng Checkov)
  │
  └──> 08.02 (Quét Lỗ hổng Ảnh Container bằng Trivy: 0 Critical, 0 High)
         │
         └──> 08.03 (Tạo Hóa đơn Phần mềm SBOM CycloneDX & Ký số bằng Cosign)
                │
                └──> 08.04 (Khóa Mã băm Bất biến Immutable Digest & Tự động hóa PR GitOps)
```

---

## 3. Danh Mục Tài Nguyên (Resource Catalog)

| Tài Nguyên | Loại Resource | Số Lượng | Ghi Chú Kỹ Thuật |
| :--- | :--- | :---: | :--- |
| **Checkov Runner** | `Security::SAST` | 1 | Bộ quy tắc kiểm tra IaC Terraform (`CKV_AWS_*`) |
| **Trivy Scanner** | `Security::Container` | 1 | Aqua Security Trivy Action nhúng trong GitHub Workflows |
| **Khóa Ký Cosign** | `AWS::KMS::Key` | 1 | `alias/fabric-cosign-signing-key` (Asymmetric ECC_NIST_P256) |
| **Kho Ảnh ECR** | `AWS::ECR::Repository` | 2 | `fabric-core-service` và `fabric-edge-frontend` (Tag Immutability: true) |
| **CI Workflows** | `CI::Workflow` | 2 | `ci-core-service.yml` và `ci-edge-frontend.yml` (Loop Guard 4 lớp) |
| **GitOps PR Bot** | `CI::Automation` | 1 | `github-actions[bot]` tự động tạo và merge promotion PRs |

---

## 4. Danh Sách 4 Bài Lab Đặc Tả Chi Tiết

| Mã Lab | Tên Đặc Tả & Nội Dung Trọng Tâm | Trạng Thái | File Đặc Tả |
|---|---|:---:|---|
| **08.01** | **Kiểm Thử Terraform & Checkov:** Phân tích tĩnh an ninh mã nguồn hạ tầng IaC. | `READY_TO_RUN` | [01-terraform-validation-checkov.md](01-terraform-validation-checkov.md) |
| **08.02** | **Quét Lỗ Hổng Container Trivy:** Chặn đứng các lỗ hổng CRITICAL và HIGH trước khi push ECR. | `RUNTIME_PASS` | [02-trivy-container-vulnerability-scan.md](02-trivy-container-vulnerability-scan.md) |
| **08.03** | **SBOM & Ký Số Cosign:** Sinh SBOM CycloneDX và ký số mật mã học qua AWS KMS Asymmetric Key. | `READY_TO_RUN` | [03-sbom-and-cosign-signing.md](03-sbom-and-cosign-signing.md) |
| **08.04** | **Khóa Digest Bất Biến & PR GitOps:** Khóa digest `@sha256:...` và cơ chế chống loop 4 lớp. | `RUNTIME_PASS` | [04-gitops-immutable-digest-pr.md](04-gitops-immutable-digest-pr.md) |
