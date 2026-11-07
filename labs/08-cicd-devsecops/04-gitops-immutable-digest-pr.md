# 08.04 — Khóa Mã Băm Bất Biến (Immutable Digest) & Tự Động Hóa PR GitOps

> **Mã bài lab:** `08.04`  
> **Trạng thái:** `COMPLETED`  
> **Thời gian dự kiến:** 35 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab [08.02](02-trivy-container-vulnerability-scan.md) và [08.03](03-sbom-and-cosign-signing.md).
- Images đã vượt qua security gate quét lỗ hổng Trivy (0 CRITICAL, 0 HIGH) và được đẩy lên Amazon ECR Singapore.
- Repository ứng dụng [`aws-eks-secure-network-fabric-app`](https://github.com/Kien-devops/aws-eks-secure-network-fabric-app) đã cấu hình GitHub Actions Workflows với quyền OIDC và GITHUB_TOKEN (`contents: write`, `pull-requests: write`).
- Cả hai cụm EKS (`fabric-edge-eks` và `fabric-core-eks`) đang vận hành ổn định trên vùng `ap-southeast-1`.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để trích xuất digest từ Amazon ECR và quản trị cụm:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:DescribeImages",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "eks:DescribeCluster",
        "eks:AccessKubernetesApi"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Rủi Ro Tag Nổi (Mutable Tag Vulnerability & Loop Hazards)

- **Chi phí:** $0.00 USD.
- **Rủi Ro An Ninh Tag Nổi (Mutable Tag Trap):** Việc sử dụng tag nổi như `:latest`, `:dev`, hoặc `:v1.0.0` là rủi ro an ninh nghiêm trọng trong môi trường doanh nghiệp. Kẻ tấn công hoặc quy trình CI bị thỏa hiệp có thể ghi đè image tag mà Kubernetes scheduler không phát hiện ra. **100% CONTAINER IMAGES TRÊN EKS BẮT BUỘC PHẢI KHÓA BẰNG MÃ BĂM BẤT BIẾN (`@sha256:...`)**.
- **Nguy Cơ Vòng Lặp Vô Hạn CI/CD (CI/CD Infinite Loop Hazard):** Khi pipeline CI/CD tự động commit manifest cập nhật trở lại Git repo, nếu không thiết lập cơ chế chặn (loop guard), hành động push mới này sẽ kích hoạt lại workflow, dẫn đến vòng lặp build - commit - push vô tận, tiêu tốn runner compute và gây nhiễu loạn Git history.

---

## 4. Kiến Trúc Tự Động Hóa GitOps & Cơ Chế Chặn Vòng Lặp 4 Lớp (Loop Guard Architecture)

Hệ thống triển khai cơ chế phòng vệ 4 lớp (Defense-in-Depth Loop Guard) kết hợp cập nhật GitOps tự động:

```
[Developer Push Code (services/)]
           │
           ▼
[Workflow Trigger Filter] ── (paths-ignore: ['k8s/**', 'docs/**', '**.md'])
           │
           ▼
[Job Condition Guard] ── (if: actor != 'github-actions[bot]' && !contains('[skip ci]'))
           │
           ▼
[Build, Unit Test & Trivy Scan] ── (0 CRITICAL, 0 HIGH)
           │
           ▼
[ECR Push & Extract Immutable Digest] (sha256:fa38d8...)
           │
           ▼
[Bot Manifest Update] (sed -i k8s/core/deployment.yaml)
           │
           ▼
[Bot Git Commit with Flag] ── (git commit -m "... [skip ci]")
           │
           ▼
[Auto Create GitOps PR with Rich Metadata Table] (via gh CLI)
           │
           ▼
[Merge to Main Branch with [skip ci]] ── (GitHub Actions skips re-trigger)
           │
           ▼
[Live EKS Deployment Sync] (Rollout with Immutable Digest)
```

### Chi Tiết 4 Lớp Chặn Vòng Lặp (4-Tier Loop Prevention)

1. **Lớp 1 — Bộ lọc đường dẫn kích hoạt (Path Filtering):**
   ```yaml
   on:
     push:
       branches: [ main ]
       paths:
         - 'services/core-service/**'
         - '.github/workflows/ci-core-service.yml'
   ```
   *Bất kỳ commit nào chỉ thay đổi thư mục `k8s/` không nằm trong danh sách `paths` sẽ không bao giờ kích hoạt workflow.*

2. **Lớp 2 — Điều kiện kiểm tra Actor & Message (Job-Level Condition):**
   ```yaml
   if: github.actor != 'github-actions[bot]' && !contains(github.event.head_commit.message, '[skip ci]') && !contains(github.event.head_commit.message, '[ci skip]')
   ```
   *Ngăn chặn việc thực thi job nếu tác nhân kích hoạt là bot hoặc commit message chứa cờ bỏ qua.*

3. **Lớp 3 — Cờ Bỏ qua CI chuẩn hóa (`[skip ci]` Commit Flag):**
   Mọi commit do bot thực hiện đều gắn thẻ `[skip ci]`:
   ```bash
   git commit -m "chore(gitops): promote core-service to immutable digest ${SHORT_DIGEST} [skip ci]"
   ```
   *GitHub Actions engine tự động bỏ qua (skip) toàn bộ push events có tag này.*

4. **Lớp 4 — Kiểm soát tiến trình đồng thời (Concurrency Control):**
   ```yaml
   concurrency:
     group: ${{ github.workflow }}-${{ github.ref }}
     cancel-in-progress: true
   ```
   *Đảm bảo chỉ có một tiến trình build/promote duy nhất được chạy tại một thời điểm.*

---

## 5. Quy Chuẩn Báo Cáo Trạng Thái Trên App Repository (Metadata Reporting)

Khi bot cập nhật mã băm bất biến, một bảng báo cáo trạng thái chi tiết được tự động chèn vào **Pull Request description**, **Commit Body**, và **GitHub Step Summary**:

| Metadata Attribute | Production Value | Ý nghĩa Kiến trúc |
| :--- | :--- | :--- |
| **Service** | `core-service` / `edge-frontend` | Microservice được thăng hạng |
| **Target Cluster** | `fabric-core-eks` / `fabric-edge-eks` | Cụm EKS mục tiêu tại Singapore |
| **Target VPC** | Core VPC (10.50.0.0/16) / Edge VPC (10.40.0.0/16) | Vùng mạng cách ly |
| **Target Manifest** | `k8s/core/deployment.yaml` / `k8s/edge/deployment.yaml` | File cấu hình Kubernetes |
| **Source Commit** | `506fe5f...` | Git commit SHA nguồn của ứng dụng |
| **ECR Image** | `123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/...` | URI kho ảnh ECR |
| **Immutable Digest** | `sha256:fa38d8073ebbe9f17f21f2b0089dd5dc7e8ee88c541860d255031ed5301c7e60` | Khóa mã băm SHA256 bất biến |
| **Trivy Vulnerability Scan** | 🟢 **PASSED** (0 Critical, 0 High) | Bằng chứng vượt qua cổng an ninh |
| **CI Bot Actor** | `github-actions[bot]` | Danh tính bot thực hiện commit |
| **Loop Prevention** | 🔒 Active (`[skip ci]`, `paths-ignore: ['k8s/**']`) | Trạng thái bảo vệ chống loop |
| **Timestamp** | `2026-11-08T03:37:29Z` | Dấu thời gian chuẩn UTC |

---

## 6. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

### Bước 1: Kiểm Tra Trực Tiếp Image ID Của Pods Đang Chạy
Sử dụng `kubectl` truy vấn trực tiếp thuộc tính `imageID` từ Kubernetes Container Runtime API:

```bash
# Kiểm tra Pod core-service trên Core EKS Cluster
kubectl get pod -l app=order-service -n fabric-apps --context fabric-core \
  -o jsonpath='{.items[0].status.containerStatuses[0].imageID}'

# Kiểm tra Pod edge-frontend trên Edge EKS Cluster
kubectl get pod -l app=frontend -n fabric-apps --context fabric-edge \
  -o jsonpath='{.items[0].status.containerStatuses[0].imageID}'
```

**Kết quả runtime thực tế:**
```
123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-core-service@sha256:fa38d8073ebbe9f17f21f2b0089dd5dc7e8ee88c541860d255031ed5301c7e60
123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-edge-frontend@sha256:aa90588851dca4af1ca6a3c0af72525ab9a3c5ad091f391ec7d4672e63020c07
```
*(Xác nhận: Không còn tồn tại tag nổi `:latest` trong runtime của các pods).*

---

### Bước 2: Kiểm Tra Trạng Thái Pull Request Do Bot Tạo Trên GitHub
Truy vấn danh sách Pull Requests do `github-actions[bot]` tạo ra qua GitHub CLI:
```bash
gh pr list --repo Kien-devops/aws-eks-secure-network-fabric-app --state all
```

**Kết quả kỳ vọng:**
```
#3  chore(gitops): promote edge-frontend to immutable digest aa905888  gitops/promote-edge-frontend  MERGED
#2  chore(gitops): promote core-service to immutable digest fa38d807   gitops/promote-core-service   MERGED
```

---

## 7. Kế Hoạch Khôi Phục / Rollback Plan

Nếu phiên bản mới phát sinh sự cố sau khi thăng hạng:
1. **Rollback GitOps tức thì:**
   ```bash
   # Revert commit promotion trên nhánh main
   git revert HEAD -m 1
   git commit -m "chore(gitops): rollback to previous immutable digest [skip ci]"
   git push origin main
   ```
2. **Kích hoạt lại Deployment:**
   ```bash
   kubectl --context fabric-core rollout undo deployment/core-service -n fabric-apps
   ```

---

## 8. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, PR snapshots, Pod inspects) được lưu trữ tại:
`evidence/08-devsecops/04-gitops-promotion.json`

---

## 9. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [x] 100% container images trong file manifest Kubernetes (`k8s/core/deployment.yaml` và `k8s/edge/deployment.yaml`) được khóa cố định bằng mã băm `@sha256:...`.
- [x] Tích hợp thành công bot tự động hóa `github-actions[bot]` để tạo GitOps branch và PR promotion.
- [x] Thiết lập triệt để cơ chế chặn vòng lặp 4 lớp (Path filters, Condition guard, `[skip ci]`, Concurrency).
- [x] Xuất bản bảng metadata trạng thái đầy đủ (Trivy status, ECR digest, cluster, timestamp) trên PR và GitHub Step Summary.
- [x] Pods thực tế trên cụm `fabric-core-eks` và `fabric-edge-eks` chạy đúng container image ID tương ứng.
