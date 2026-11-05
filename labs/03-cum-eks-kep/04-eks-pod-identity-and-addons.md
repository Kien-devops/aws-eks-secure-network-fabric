# 03.04 — Cài Đặt Managed Add-ons & Cấu Hình EKS Pod Identity

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Cài đặt các thành phần nền tảng Kubernetes và cấu hình phân quyền hiện đại EKS Pod Identity thay thế cho IRSA cũ.

---

## 1. Mục Tiêu Kỹ Thuật

- Cài đặt 4 Managed Add-ons chuẩn trên cả 2 cụm EKS:
  1. `vpc-cni` (Hỗ trợ Pod networking)
  2. `coredns` (Phân giải tên miền trong cụm)
  3. `kube-proxy` (Định tuyến service)
  4. `eks-pod-identity-agent` (Cung cấp cơ chế xác thực IAM cho Pod)
- Cấu hình EKS Pod Identity Association cho các ứng dụng và controller cần quyền AWS (AWS Load Balancer Controller, External Secrets Operator).

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Cài Đặt Managed Add-ons
1. Tại dịch vụ **EKS Console**, chọn cụm `fabric-edge-eks`.
2. Mở tab **Add-ons** -> Nhấp nút **Get more add-ons**.
3. Tích chọn lần lượt 4 add-ons:
   - **Amazon VPC CNI**
   - **CoreDNS**
   - **kube-proxy**
   - **Amazon EKS Pod Identity Agent**
4. Nhấp **Next** -> Giữ nguyên cấu hình phiên bản tương thích mặc định -> Nhấp **Create**.
5. Lặp lại thao tác trên cho cụm `fabric-core-eks`.

---

### Bước 2: Khởi Tạo IAM Role Cho EKS Pod Identity
Ví dụ phân quyền cho ServiceAccount `fabric-app-sa`:
1. Mở dịch vụ **IAM** -> Tạo Role mới.
2. Chọn Trusted entity type: **Custom trust policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "pods.eks.amazonaws.com"
      },
      "Action": [
        "sts:AssumeRole",
        "sts:TagSession"
      ]
    }
  ]
}
```
3. Đặt tên: `fabric-order-service-pod-role`.

---

### Bước 3: Tạo EKS Pod Identity Association Trên Console
1. Quay lại EKS Console, chọn cụm `fabric-core-eks`.
2. Mở tab **Access** -> Cuộn xuống mục **Pod Identity associations** -> Nhấp **Create Pod Identity association**.
3. **Configure Pod Identity association:**
   - **IAM role:** Chọn `fabric-order-service-pod-role`.
   - **Kubernetes namespace:** Nhập `default` (hoặc namespace ứng dụng).
   - **Kubernetes service account:** Nhập `order-service-sa`.
4. Nhấp **Create**.

---

## 3. Xác Minh (Verification)

Kiểm tra danh sách Add-ons đã cài đặt qua AWS CLI:
```bash
aws eks list-addons \
  --cluster-name fabric-edge-eks \
  --region ap-southeast-1 \
  --output table
```
> Kết quả: Có đủ cả 4 add-ons: `vpc-cni`, `coredns`, `kube-proxy`, `eks-pod-identity-agent`.

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Cả 4 Add-ons ở trạng thái `ACTIVE` trên cả 2 cụm EKS.
- [ ] Pod Identity association được tạo thành công, gắn đúng ServiceAccount và IAM Role.
