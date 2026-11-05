# 08.04 — Khóa Mã Băm Bất Biến (Immutable Digest) & Tự Động Hóa PR GitOps

> **Mã bài lab:** `08.04`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 35 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab [08.02](02-trivy-container-vulnerability-scan.md) và [08.03](03-sbom-and-cosign-signing.md). Image đã được ký số và có mặt trên Amazon ECR Singapore.
- Repository ứng dụng [`aws-eks-secure-network-fabric-app`](https://github.com/Kien-devops/aws-eks-secure-network-fabric-app) đã được clone cục bộ.
- Đang mở phiên AWS Management Console tại Singapore `ap-southeast-1`.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để đọc ECR image digest và kiểm tra deployment trên EKS:
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

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD.
- **Cảnh báo Lỗ Hổng Thay Thế Ảnh (Image Poisoning / Mutable Tag Trap):** Việc sử dụng tag nổi như `:latest`, `:dev`, hoặc `:v1.0.0` là rủi ro an ninh nghiêm trọng, vì kẻ tấn công có quyền ECR có thể ghi đè image cùng tên mà Kubernetes không phát hiện ra sự thay đổi. **100% CONTAINER IMAGES TRÊN EKS BẮT BUỘC PHẢI KHÓA BẰNG MÃ BĂM BẤT BIẾN (`@sha256:...`)**. Mọi thay đổi image phải thông qua Git Pull Request có đối soát chữ ký.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console & GitOps (Console Walkthrough)

### Bước 1: Trích Xuất Mã Băm Bất Biến (SHA256 Digest) Từ ECR
1. Mở **Amazon ECR Console** tại Region Singapore `ap-southeast-1`.
2. Chọn repository `fabric-order-service`.
3. Tìm image tag `v1.0.0`:
   - Quan sát cột **Image digest**: Sao chép chuỗi mã băm dạng `sha256:4f8d5e6a7b8c...`.
   - (Hoặc nhấp vào biểu tượng Copy URI: `123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-order-service@sha256:4f8d5e...`).
4. Lấy qua dòng lệnh CLI:
   ```bash
   IMAGE_DIGEST=$(aws ecr describe-images --region ap-southeast-1 \
     --repository-name fabric-order-service \
     --image-ids imageTag=v1.0.0 \
     --query 'imageDetails[0].imageDigest' \
     --output text)
   echo "Immutable Digest: $IMAGE_DIGEST"
   ```

---

### Bước 2: Cập Nhật Manifest Kubernetes Bằng Kustomize
1. Mở terminal tại thư mục repository `aws-eks-secure-network-fabric-app`:
   ```bash
   cd gitops/overlays/core-prod/
   ```
2. Sử dụng lệnh `kustomize` để ghim mã băm bất biến vào file `kustomization.yaml`:
   ```bash
   kustomize edit set image fabric-order-service=123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-order-service@${IMAGE_DIGEST}
   ```
3. Kiểm tra kết quả sau khi chỉnh sửa:
   ```yaml
   # kustomization.yaml
   images:
   - name: fabric-order-service
     newName: 123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-order-service
     digest: sha256:4f8d5e6a7b8c...
   ```

---

### Bước 3: Tạo Nhánh Git & Mở Pull Request Có Bằng Chứng Kiểm Thử
1. Tạo nhánh git mới đại diện cho lần thăng hạng phiên bản (promotion):
   ```bash
   SHORT_SHA=${IMAGE_DIGEST:7:8}
   git checkout -b promote/order-service-${SHORT_SHA}
   git add kustomization.yaml
   git commit -m "chore(gitops): promote order-service to immutable digest ${SHORT_SHA} [verified cosign]"
   git push origin promote/order-service-${SHORT_SHA}
   ```
2. Mở giao diện GitHub của repo `aws-eks-secure-network-fabric-app`:
   - Nhấp nút **Compare & pull request**.
   - **PR Description:** Đính kèm kết quả xác thực chữ ký Cosign và báo cáo Trivy từ lab 08.02 và 08.03:
     ```markdown
     ### Security & Compliance Verification
     - [x] Trivy Vulnerability Scan: PASSED (0 Critical, 0 High)
     - [x] Cosign Signature: VERIFIED via AWS KMS (alias/fabric-cosign-signing-key)
     - [x] Immutable Image Digest: `sha256:4f8d5e...`
     - [x] Target Cluster: `fabric-core-eks` (Core EKS VPC)
     ```
   - Nhấp **Create pull request**.
3. Sau khi Lead Architect phê duyệt (Review & Approve), thực hiện **Squash and merge** vào nhánh `main`.

---

### Bước 4: Đồng Bộ Tự Động Xuống Cụm EKS Qua Argo CD
1. Mở giao diện **Argo CD Web UI** (`https://localhost:8080`).
2. Nhấp vào application `fabric-core-apps`:
   - Argo CD sẽ tự động phát hiện commit mới trên nhánh `main` và kích hoạt đồng bộ (hoặc nhấp **SYNC** thủ công).
   - Quan sát quá trình Rolling Update của Deployment `order-service`.
   - Các Pod cũ được terminate an toàn và các Pod mới khởi chạy với mã băm SHA256 đã phê duyệt.

---

### Bước 5: Kiểm Tra Trạng Thái Pods Trên AWS EKS Console
1. Mở **Amazon EKS Console** tại Singapore `ap-southeast-1`.
2. Chọn cụm `fabric-core-eks` -> Chọn tab **Workloads** -> Nhấp vào Deployment `order-service`.
3. Chọn một Pod đang chạy -> Mở tab **Details**:
   - Xác nhận trường **Image** hiển thị đầy đủ chuỗi `@sha256:...`.
   - Xác nhận Pod ở trạng thái xanh `Running` (1/1 Ready).

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trực tiếp Container Image ID từ Kubernetes API:
```bash
# Kiểm tra imageID thực tế của Pod order-service trên Core EKS
kubectl get pod -l app=order-service -n fabric-apps --context fabric-core \
  -o jsonpath='{.items[0].status.containerStatuses[0].imageID}'
```
**Kết quả kỳ vọng:**
`123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-order-service@sha256:4f8d5e...`
*(Khớp 100% với mã băm đã trích xuất từ ECR).*

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Nếu phiên bản mới phát sinh lỗi logic ứng dụng:
1. Tạo Pull Request đảo ngược (Revert PR) commit vừa merge trên Git:
   ```bash
   git revert HEAD
   git push origin main
   ```
2. Argo CD sẽ tự động rollback image về mã băm trước đó.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/08-devsecops/04-gitops-promotion.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] 100% container images triển khai trên EKS được ghim trực tiếp bằng mã băm cố định `@sha256:...`.
- [ ] Tuyệt đối không còn tag nổi (`:latest`) nào tồn tại trong manifests.
- [ ] Quy trình triển khai ứng dụng đi qua Pull Request minh bạch và có bằng chứng đối soát an ninh.
- [ ] Argo CD đồng bộ thành công ứng dụng xuống cụm `fabric-core-eks`.
