# 08.04 — Đặc Tả Khóa Mã Băm Bất Biến (Immutable Digest) & Tự Động Hóa PR GitOps

> **Mã bài lab:** `08.04`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/08-devsecops/04-gitops-promotion.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả cơ chế tự động hóa thăng hạng GitOps bằng cách thay thế toàn bộ tag nổi bằng mã băm bất biến SHA256 (`@sha256:...`) trong manifests Kubernetes, kèm theo kiến trúc phòng thủ 4 lớp ngăn chặn vòng lặp vô tận (Loop Guard) trong GitHub Actions.

---

## 2. Tài Nguyên (Resources)

| Tên Tài Nguyên | Loại Resource | Phạm Vi Áp Dụng | Runtime ID / URI |
| :--- | :--- | :--- | :--- |
| `k8s/edge/deployment.yaml` | `Manifest::K8s` | Repo `fabric-app` | Khóa digest: `sha256:aa90588851dca4af1ca6a3c0af72525ab9a3c5ad091f391ec7d4672e63020c07` |
| `k8s/core/deployment.yaml` | `Manifest::K8s` | Repo `fabric-app` | Khóa digest: `sha256:fa38d8073ebbe9f17f21f2b0089dd5dc7e8ee88c541860d255031ed5301c7e60` |
| GitHub Actions PR Bot | `CI::Automation` | GitHub Repo | PR #2 (`core-service`), PR #3 (`edge-frontend`) đã merged |
| `04-gitops-promotion.json` | `Artifact::Evidence` | `evidence/08-devsecops/` | Bằng chứng runtime digest của pods |

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-*-gitops` | Tài nguyên quản trị triển khai |
| `Project` | `aws-eks-secure-network-fabric` | Manifest metadata, Git Commit tags |
| `Environment` | `prod` | Manifest metadata, Git Commit tags |
| `ManagedBy` | `manual` | Quản trị quy trình thăng hạng thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Cơ Chế Phòng Thủ Chống Vòng Lặp 4 Lớp (Loop Guard Architecture)

1. **Lớp 1 (Path Filtering):** Chỉ kích hoạt khi thay đổi mã nguồn trong `services/**`, tự động bỏ qua các thay đổi trong `k8s/**` và `docs/**`.
2. **Lớp 2 (Job Condition Guard):** Kiểm tra điều kiện `github.actor != 'github-actions[bot]'` và commit message không chứa `[skip ci]`.
3. **Lớp 3 (Commit Flag):** Tự động gắn thẻ `[skip ci]` vào toàn bộ commit thăng hạng do bot thực hiện.
4. **Lớp 4 (Concurrency Group):** Giới hạn chỉ một tiến trình build/promote duy nhất được chạy đồng thời.

### 4.2 Cấu Hình Kỹ Thuật Manifests Kubernetes

- Loại bỏ hoàn toàn các tag động `:latest`, `:dev`, `:v1.0.0`.
- Ép buộc định danh container theo cú pháp:
  `<account_id>.dkr.ecr.ap-southeast-1.amazonaws.com/<repo_name>@sha256:<sha256_hash>`

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `08.02`: Container image phải đạt tiêu chuẩn an ninh Trivy trước khi trích xuất digest.
- Phụ thuộc vào `04.04`: Argo CD đã liên kết với repository ứng dụng để nhận diện và đồng bộ manifest mới.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Runtime Image ID Edge** | `kubectl get pod -l app=frontend -n fabric-apps --context fabric-edge -o jsonpath='{.items[0].status.containerStatuses[0].imageID}'` | Chứa chính xác chuỗi `sha256:aa90588851...` |
| **Runtime Image ID Core** | `kubectl get pod -l app=order-service -n fabric-apps --context fabric-core -o jsonpath='{.items[0].status.containerStatuses[0].imageID}'` | Chứa chính xác chuỗi `sha256:fa38d8073e...` |
| **Trạng thái PR GitOps** | `gh pr list --repo Kien-devops/aws-eks-secure-network-fabric-app --state all` | Cả PR #2 và PR #3 đều ở trạng thái `MERGED`. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo lỗi scheduler:** Nếu một digest bị xóa trên ECR, Kubernetes sẽ không thể kéo image và pod rơi vào trạng thái `ImagePullBackOff`. Không xóa các image digest đang chạy.
- **Quy trình Rollback:**
  ```bash
  # Hoàn tác PR thăng hạng trên repository app
  git revert HEAD -m 1
  git commit -m "chore(gitops): rollback to previous immutable digest [skip ci]"
  git push origin main
  ```
