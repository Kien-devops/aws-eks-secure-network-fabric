# 03.01 — Khởi Tạo Khóa Mã Hóa AWS KMS CMK Cho Secrets Của 2 Cụm EKS

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Thiết lập bảo mật phong bì (Envelope Encryption) cho tài nguyên Secrets trên cả 2 cụm EKS độc lập.

---

## 1. Mục Tiêu Kỹ Thuật

- Khởi tạo 2 khóa mã hóa riêng biệt do khách hàng quản lý (**KMS Customer Managed Key - CMK**) tại Singapore (`ap-southeast-1`):
  1. `fabric-edge-eks-secrets-key`
  2. `fabric-core-eks-secrets-key`
- Cấu hình Key Policy cho phép dịch vụ Amazon EKS sử dụng khóa để mã hóa và giải mã dữ liệu Secrets được lưu trong etcd.

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Mở Dịch Vụ AWS Key Management Service (KMS)
1. Mở dịch vụ **KMS** tại Region Singapore (`ap-southeast-1`).
2. Chọn **Customer managed keys** -> Nhấp nút cam **Create key**.

### Bước 2: Cấu Hình Khóa Mã Hóa
1. **Key type:** Chọn `Symmetric`.
2. **Key usage:** Chọn `Encrypt and decrypt`.
3. Nhấp **Next**.
4. **Add labels:**
   - **Alias:** Nhập `alias/fabric-edge-eks-secrets-key`.
   - **Description:** Nhập `KMS key for fabric-edge-eks cluster secrets envelope encryption`.
   - **Tags:** `Project` = `aws-eks-secure-network-fabric`, `Environment` = `dev`.
5. Nhấp **Next**.
6. **Key administrators:** Chọn IAM User hoặc Role hiện tại của bạn.
7. **Key deletion:** Cho phép Key Administrator xóa khóa.
8. **Key users:** Thêm IAM Role được dùng để tạo EKS Cluster hoặc để mặc định để cập nhật sau.
9. Nhấp **Finish**.

### Bước 3: Lặp Lại Tạo Khóa Thứ 2
Thực hiện tương tự để tạo khóa cho cụm Core:
- **Alias:** `alias/fabric-core-eks-secrets-key`.
- **Description:** `KMS key for fabric-core-eks cluster secrets envelope encryption`.

---

## 3. Xác Minh (Verification)

Kiểm tra danh sách khóa KMS qua AWS CLI:
```bash
aws kms list-aliases \
  --region ap-southeast-1 \
  --query 'Aliases[?starts_with(AliasName, `alias/fabric-`)].{Alias:AliasName,KeyId:TargetKeyId}' \
  --output table
```

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] 2 Khóa KMS CMK được tạo thành công và ở trạng thái `Enabled`.
- [ ] Key Policy có cấu hình quyền hạn rõ ràng, tuân thủ nguyên tắc Least Privilege.

