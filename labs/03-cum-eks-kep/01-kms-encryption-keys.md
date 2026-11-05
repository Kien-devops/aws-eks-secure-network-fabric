# 03.01 — Tạo Khóa Mã Hóa AWS KMS Customer Managed Key Cho EKS Secrets

> **Mã bài lab:** `03.01`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 20 phút  
> **Chi phí ước tính:** ~$1.00 USD / key / tháng ($2.00 USD cho 2 keys Edge & Core)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành toàn bộ các bài lab thuộc [Module 02: Thiết Lập Hạ Tầng Mạng Cơ Bản](../02-ha-tang-mang-co-ban/README.md).
- Có quyền quản trị KMS (`kms:*`) và IAM (`iam:*`) trên tài khoản AWS.
- Đang mở phiên AWS Management Console tại Singapore `ap-southeast-1`.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để thực thi bài lab này:
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
        "kms:EnableKeyRotation",
        "kms:GetKeyRotationStatus",
        "kms:PutKeyPolicy",
        "kms:ListAliases",
        "kms:ScheduleKeyDeletion"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Mỗi khóa KMS Customer Managed Key (CMK) tính phí $1.00 USD/tháng cố định. Dự án sử dụng 2 keys độc lập cho 2 cụm EKS (`fabric-edge-eks` và `fabric-core-eks`).
- **Cảnh báo Key Policy & EKS Encryption:** Khi tạo EKS Cluster có bật tính năng Secret Envelope Encryption, EKS control plane sử dụng khóa KMS này để sinh ra Data Encryption Key (DEK) mã hóa etcd Secrets. Key Policy **BẮT BUỘC PHẢI CẤP QUYỀN** cho `kms:Encrypt`, `kms:Decrypt`, `kms:ReEncrypt*`, `kms:GenerateDataKey*`, `kms:DescribeKey` cho dịch vụ EKS. Nếu Key Policy bị xóa hoặc từ chối, cụm EKS sẽ bị kẹt ở trạng thái `CREATING` hoặc rơi vào trạng thái `FAILED`.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Khởi Tạo Khóa KMS Cho Edge EKS Cluster (`alias/fabric-edge-eks-secrets`)
1. Truy cập **AWS KMS Console** tại Region Singapore (`ap-southeast-1`).
2. Tại menu điều hướng bên trái, chọn **Customer managed keys**.
3. Nhấp vào nút cam **Create key** ở góc trên bên phải:
   - **Step 1 — Configure key:**
     - Key type: Chọn **Symmetric**.
     - Key usage: Chọn **Encrypt and decrypt**.
     - Advanced options:
       - Key material origin: Chọn **KMS (AWS KMS)**.
       - Regionality: Chọn **Single-Region key** (Đảm bảo tuân thủ nguyên tắc Single-Region Singapore theo `spec.md`).
     - Nhấp **Next**.
   - **Step 2 — Add labels:**
     - **Alias:** Nhập `alias/fabric-edge-eks-secrets`.
     - **Description:** Nhập `KMS CMK ma hoa Kubernetes Secrets cho cum fabric-edge-eks tai Singapore`.
     - **Tags:**
       - Key: `Project` | Value: `aws-eks-secure-network-fabric`
       - Key: `Environment` | Value: `prod`
       - Key: `Cluster` | Value: `fabric-edge-eks`
     - Nhấp **Next**.
   - **Step 3 — Define key administrative permissions:**
     - Tìm và tích chọn IAM Role hoặc User quản trị của bạn (đảm bảo tài khoản của bạn có quyền chỉnh sửa và quản lý vòng đời khóa).
     - Key deletion: Đánh dấu tích vào **Allow key administrators to delete this key**.
     - Nhấp **Next**.
   - **Step 4 — Define key usage permissions:**
     - Tích chọn IAM Role/User của bạn.
     - Nhấp **Next**.
   - **Step 5 — Review and edit key policy:**
     - Quan sát ô JSON Key Policy. Đảm bảo policy cho phép root account và người quản trị.
     - Nhấp nút cam **Finish** để khởi tạo khóa.

### Bước 2: Bật Tự Động Xoay Khóa Hàng Năm (Key Rotation) Cho Edge Key
1. Tại danh sách **Customer managed keys**, nhấp vào alias `alias/fabric-edge-eks-secrets`.
2. Chọn tab **Key rotation**.
3. Tích chọn vào ô **Automatically rotate this KMS key every year** (hoặc nhấp **Edit** -> Chọn **Enable automatic key rotation**).
4. Nhấp **Save**.

---

### Bước 3: Khởi Tạo Khóa KMS Cho Core EKS Cluster (`alias/fabric-core-eks-secrets`)
Lặp lại quy trình tương tự để tạo khóa riêng biệt cho cụm Core EKS:
1. Nhấp **Create key** -> Symmetric -> Encrypt and decrypt -> Single-Region key -> Nhấp **Next**.
2. **Add labels:**
   - **Alias:** Nhập `alias/fabric-core-eks-secrets`.
   - **Description:** Nhập `KMS CMK ma hoa Kubernetes Secrets cho cum fabric-core-eks tai Singapore`.
   - **Tags:**
     - Key: `Project` | Value: `aws-eks-secure-network-fabric`
     - Key: `Environment` | Value: `prod`
     - Key: `Cluster` | Value: `fabric-core-eks`
   - Nhấp **Next**.
3. Chọn Key Administrators và Key Users tương tự Bước 1.
4. Nhấp **Finish**.
5. Mở chi tiết `alias/fabric-core-eks-secrets` -> Tab **Key rotation** -> Kích hoạt **Automatically rotate this KMS key every year** -> Nhấp **Save**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy các lệnh xác minh trạng thái và bí danh (aliases) của 2 khóa KMS vừa khởi tạo:
```bash
# 1. Liệt kê 2 khóa KMS CMK theo alias prefix fabric-
aws kms list-aliases --region ap-southeast-1 \
  --query 'Aliases[?starts_with(AliasName, `alias/fabric-`)].{Alias:AliasName,KeyId:TargetKeyId}' \
  --output table

# 2. Kiểm tra trạng thái Key Rotation của Edge KMS Key
EDGE_KEY_ID=$(aws kms describe-key --region ap-southeast-1 --key-id alias/fabric-edge-eks-secrets --query 'KeyMetadata.KeyId' --output text)
aws kms get-key-rotation-status --region ap-southeast-1 --key-id $EDGE_KEY_ID --output table

# 3. Kiểm tra trạng thái Key Rotation của Core KMS Key
CORE_KEY_ID=$(aws kms describe-key --region ap-southeast-1 --key-id alias/fabric-core-eks-secrets --query 'KeyMetadata.KeyId' --output text)
aws kms get-key-rotation-status --region ap-southeast-1 --key-id $CORE_KEY_ID --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Lên lịch xóa khóa KMS (AWS yêu cầu khoảng thời gian chờ xóa an toàn từ 7 đến 30 ngày):
```bash
for alias in "alias/fabric-edge-eks-secrets" "alias/fabric-core-eks-secrets"; do
  key_id=$(aws kms describe-key --region ap-southeast-1 --key-id $alias --query 'KeyMetadata.KeyId' --output text 2>/dev/null)
  if [ -n "$key_id" ] && [ "$key_id" != "None" ]; then
    aws kms schedule-key-deletion --region ap-southeast-1 --key-id $key_id --pending-window-in-days 7
  fi
done
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/03-eks/01-kms-keys.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Cả 2 khóa KMS CMK `alias/fabric-edge-eks-secrets` và `alias/fabric-core-eks-secrets` ở trạng thái `Enabled`.
- [ ] Tính năng Automatic Key Rotation được bật (`KeyRotationEnabled: true`) trên cả 2 khóa.
- [ ] Khóa thuộc loại Single-Region nằm tại vùng `ap-southeast-1` (Singapore).
- [ ] Tags gán đúng định danh `Project=aws-eks-secure-network-fabric`.
