# 08.04 — Khóa Mã Băm Bất Biến (Immutable Digest) & Tự Động Hóa PR GitOps

> **Trạng thái:** Hướng dẫn triển khai quy trình phân phối an toàn (Secure Deployment Handoff).  
> **Áp dụng cho:** Đảm bảo không xảy ra tấn công thay thế ảnh (Image Tampering) và quản lý cấu hình bằng Git PR có kiểm duyệt.

---

## 1. Mục Tiêu Kỹ Thuật

- Lấy mã băm định danh bất biến (**SHA256 Digest**) của ảnh container sau khi đã vượt qua các bài kiểm tra bảo mật:
  `@sha256:4f8d5e...` thay vì sử dụng mutable tag như `:latest` hay `:v1.0.0`.
- Tự động cập nhật SHA digest vào file manifest Kubernetes tương ứng trong repository GitOps `aws-eks-secure-network-fabric-app`.
- Tạo **Pull Request (PR)** tự động lên nhánh `main` với đầy đủ thông tin bằng chứng kiểm thử để kỹ sư SRE phê duyệt.

---

## 2. Các Bước Thực Hiện Chi Tiết

### Bước 1: Trích Xuất Mã Băm SHA256 Từ ECR
Sau khi push ảnh thành công lên AWS ECR:
```bash
IMAGE_DIGEST=$(aws ecr describe-images \
  --repository-name fabric-order-service \
  --image-ids imageTag=v1.0.0 \
  --region ap-southeast-1 \
  --query 'imageDetails[0].imageDigest' \
  --output text)

echo "Immutable Digest: $IMAGE_DIGEST"
```

---

### Bước 2: Cập Nhật Manifest Kubernetes Trong Repo GitOps
Sử dụng công cụ `kustomize` để ghim mã băm bất biến:
```bash
cd gitops/core/
kustomize edit set image fabric-order-service=123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-order-service@${IMAGE_DIGEST}
```

Kiểm tra nội dung manifest sau khi sửa đổi:
```yaml
spec:
  template:
    spec:
      containers:
      - name: order-service
        image: 123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/fabric-order-service@sha256:4f8d5e6a7b8c...
```

---

### Bước 3: Tạo Nhánh Git Mới & Gửi Pull Request (PR)
```bash
git checkout -b promote/order-service-${IMAGE_DIGEST:7:8}
git add kustomization.yaml
git commit -m "chore(gitops): promote order-service to immutable digest ${IMAGE_DIGEST:7:8}"
git push origin promote/order-service-${IMAGE_DIGEST:7:8}
```
Sau đó tạo PR trên GitHub để kỹ sư xem xét và merge vào nhánh `main`, Argo CD sẽ tự động phát hiện thay đổi và đồng bộ xuống cluster EKS.

---

## 3. Xác Minh (Verification)

Kiểm tra Pod đang chạy trong cụm EKS có đúng mã băm hay không:
```bash
kubectl get pod -l app=order-service -o jsonpath='{.items[0].status.containerStatuses[0].imageID}'
```
> Kết quả: `.../fabric-order-service@sha256:4f8d5e...` (Khớp 100% với digest đã phê duyệt).

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Tuyệt đối không còn tag `:latest` nào tồn tại trong manifests triển khai.
- [ ] Quy trình triển khai ứng dụng đi qua Pull Request minh bạch và có truy vết lịch sử git.
