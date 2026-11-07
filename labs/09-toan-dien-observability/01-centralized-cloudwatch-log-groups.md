# 09.01 — Khởi Tạo & Quản Trị Hệ Thống CloudWatch Log Groups Tập Trung

> **Mã bài lab:** `09.01`  
> **Trạng thái:** `COMPLETED`  
> **Thời gian dự kiến:** 30 phút  
> **Chi phí ước tính:** ~$0.20 USD (Lưu trữ và ingestion CloudWatch Logs)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn tất cấu hình hạ tầng mạng cơ bản tại [Module 02](../02-ha-tang-mang-co-ban/01-four-vpcs-and-subnets.md).
- Đã cấu hình khóa KMS đa dụng `fabric-cloudwatch-kms` hoặc sử dụng AWS managed key mặc định cho CloudWatch Logs.
- Tài khoản IAM có đủ quyền quản trị dịch vụ CloudWatch Logs tại Region Singapore (`ap-southeast-1`).
- Đang mở phiên AWS Management Console với Region `ap-southeast-1`.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để khởi tạo và cấu hình Log Groups:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:DescribeLogGroups",
        "logs:PutRetentionPolicy",
        "logs:TagLogGroup",
        "logs:ListTagsForResource",
        "logs:AssociateKmsKey"
      ],
      "Resource": "arn:aws:logs:ap-southeast-1:123456789012:log-group:*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** CloudWatch Logs tính phí $0.50 per GB dữ liệu ingest và $0.03 per GB/tháng cho lưu trữ.
- **Quy tắc FinOps cốt lõi:** Luôn thiết lập **Retention Period: 7 days** cho toàn bộ log groups môi trường Lab/Dev để ngăn chặn tích lũy dung lượng lưu trữ ngoài tầm kiểm soát khi chạy lưu lượng cao.
- **Tính toán chi phí dự trù:** Với lưu lượng lab trung bình ~2GB logs/tuần, chi phí duy trì không vượt quá $1.50 USD.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Mở Bảng Điều Khiển CloudWatch Logs
1. Đăng nhập vào **AWS Management Console**.
2. Tại thanh điều hướng trên cùng, xác nhận Region là **Singapore (`ap-southeast-1`)**.
3. Tại ô tìm kiếm trung tâm, gõ `CloudWatch` và chọn dịch vụ **CloudWatch**.
4. Tại thanh điều hướng bên trái (Navigation pane), mở rộng mục **Logs** -> Nhấp vào liên kết **Log groups**.

---

### Bước 2: Khởi Tạo 4 Log Groups Cho VPC Flow Logs
Nhấp nút màu cam **Create log group** ở góc trên bên phải màn hình:

1. **Log Group 1 — Edge VPC Flow Logs:**
   - **Log group name:** `/aws/vpc/fabric-edge-flow`
   - **Retention setting:**
     - Đánh dấu chọn radio button: **`Expire events after`**
     - Chọn thời gian trong dropdown: **`7 days (1 week)`**
   - **Log class:** Chọn **`Standard`**
   - **KMS key ARN (Optional):** Để trống (sử dụng AWS managed KMS key) hoặc dán ARN khóa `fabric-cloudwatch-kms`
   - **Tags:**
     - Key: `Project` | Value: `aws-eks-secure-network-fabric`
     - Key: `Environment` | Value: `dev`
     - Key: `Module` | Value: `09-observability`
   - Nhấp nút cam **Create** ở cuối trang.

2. **Log Group 2 — Core VPC Flow Logs:**
   - Nhấp **Create log group**.
   - **Log group name:** `/aws/vpc/fabric-core-flow`
   - **Retention setting:** `7 days (1 week)`.
   - **Tags:** Gán thẻ tương tự với `Name` = `fabric-core-flow-logs`.
   - Nhấp **Create**.

3. **Log Group 3 — Inspection VPC Flow Logs:**
   - Nhấp **Create log group**.
   - **Log group name:** `/aws/vpc/fabric-inspection-flow`
   - **Retention setting:** `7 days (1 week)`.
   - Nhấp **Create**.

4. **Log Group 4 — Egress VPC Flow Logs:**
   - Nhấp **Create log group**.
   - **Log group name:** `/aws/vpc/fabric-egress-flow`
   - **Retention setting:** `7 days (1 week)`.
   - Nhấp **Create**.

---

### Bước 3: Khởi Tạo Log Group Cho Transit Gateway Flow Logs
1. Trên trang **Log groups**, tiếp tục nhấp nút **Create log group**.
2. Điền thông tin:
   - **Log group name:** `/aws/tgw/fabric-tgw-flow`
   - **Retention setting:** Chọn `Expire events after` -> chọn `7 days (1 week)`.
   - **Log class:** `Standard`.
   - **Tags:**
     - `Project` = `aws-eks-secure-network-fabric`
     - `Service` = `transit-gateway`
3. Nhấp **Create**.

---

### Bước 4: Khởi Tạo Log Groups Cho AWS Network Firewall
1. **Log Group Cảnh Báo An Ninh (Alerts):**
   - Nhấp **Create log group**.
   - **Log group name:** `/aws/network-firewall/fabric-egress-alerts`
   - **Retention setting:** `7 days (1 week)`.
   - **Tags:** `SecurityClassification` = `High-Alert`, `Module` = `09-observability`.
   - Nhấp **Create**.

2. **Log Group Nhật Ký Lưu Lượng (Flows):**
   - Nhấp **Create log group**.
   - **Log group name:** `/aws/network-firewall/fabric-egress-flows`
   - **Retention setting:** `7 days (1 week)`.
   - **Tags:** `SecurityClassification` = `Telemetry`, `Module` = `09-observability`.
   - Nhấp **Create**.

---

### Bước 5: Khởi Tạo Log Group Cho Suricata IDS/IPS EVE Logs
1. Nhấp **Create log group**.
2. Điền thông tin:
   - **Log group name:** `/aws/suricata/fabric-inspection-eve`
   - **Retention setting:** `7 days (1 week)`.
   - **Tags:**
     - `Appliance` = `suricata-gwlb`
     - `LogType` = `eve-json`
3. Nhấp **Create**.

---

### Bước 6: Kiểm Tra Tổng Quan Trên Console
1. Tại bảng danh sách **Log groups**, nhập bộ lọc tìm kiếm tại ô *Search log groups*: `/aws/`
2. Đảm bảo toàn bộ 8 Log Groups sau hiển thị đầy đủ và cột **Retention** đều ghi rõ `7 days`:
   - `/aws/network-firewall/fabric-egress-alerts`
   - `/aws/network-firewall/fabric-egress-flows`
   - `/aws/suricata/fabric-inspection-eve`
   - `/aws/tgw/fabric-tgw-flow`
   - `/aws/vpc/fabric-core-flow`
   - `/aws/vpc/fabric-edge-flow`
   - `/aws/vpc/fabric-egress-flow`
   - `/aws/vpc/fabric-inspection-flow`

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy lệnh AWS CLI để kiểm tra trạng thái và thời hạn lưu trữ của toàn bộ các Log Groups vừa tạo:

```bash
aws logs describe-log-groups \
  --region ap-southeast-1 \
  --log-group-name-prefix "/aws/" \
  --query 'logGroups[?contains(logGroupName, `fabric`)].{LogGroupName:logGroupName,RetentionInDays:retentionInDays,StoredBytes:storedBytes}' \
  --output table
```

**Kỳ vọng kết quả mẫu:**
```text
--------------------------------------------------------------------------------------
|                                  DescribeLogGroups                                 |
+------------------------------------------------+------------------+----------------+
|                  LogGroupName                  | RetentionInDays  |  StoredBytes   |
+------------------------------------------------+------------------+----------------+
|  /aws/network-firewall/fabric-egress-alerts    |  7               |  0             |
|  /aws/network-firewall/fabric-egress-flows     |  7               |  0             |
|  /aws/suricata/fabric-inspection-eve           |  7               |  0             |
|  /aws/tgw/fabric-tgw-flow                      |  7               |  0             |
|  /aws/vpc/fabric-core-flow                     |  7               |  0             |
|  /aws/vpc/fabric-edge-flow                     |  7               |  0             |
|  /aws/vpc/fabric-egress-flow                   |  7               |  0             |
|  /aws/vpc/fabric-inspection-flow               |  7               |  0             |
+------------------------------------------------+------------------+----------------+
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Trong trường hợp cần xóa nhanh các Log Groups để cấu hình lại hoặc dọn dẹp môi trường:

1. **Trên Console:**
   - Tích chọn checkbox cạnh tên từng Log Group cần xóa.
   - Nhấp vào menu **Actions** ở góc trên danh sách -> Chọn **Delete log group(s)**.
   - Nhập chuỗi xác nhận `delete` vào hộp thoại -> Nhấp **Delete**.
2. **Qua AWS CLI:**
   ```bash
   for lg in \
     /aws/vpc/fabric-edge-flow \
     /aws/vpc/fabric-core-flow \
     /aws/vpc/fabric-inspection-flow \
     /aws/vpc/fabric-egress-flow \
     /aws/tgw/fabric-tgw-flow \
     /aws/network-firewall/fabric-egress-alerts \
     /aws/network-firewall/fabric-egress-flows \
     /aws/suricata/fabric-inspection-eve; do
       aws logs delete-log-group --region ap-southeast-1 --log-group-name "$lg" 2>/dev/null || true
   done
   ```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Lưu kết quả xác minh vào thư mục bằng chứng chuẩn hóa của dự án:
- `evidence/09-observability/log-groups-inventory.json`
- `evidence/09-observability/log-groups-retention-policy.txt`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [x] Tạo thành công 8 Log Groups với đúng cú pháp đặt tên quy chuẩn `fabric-*`.
- [x] 100% Log Groups được cấu hình Retention Period chính xác là `7 days (1 week)`.
- [x] Áp dụng đầy đủ thẻ Tag (`Project`, `Environment`, `Module`) trên toàn bộ tài nguyên.
- [x] Lệnh kiểm tra CLI trả về danh sách 8 Log Groups với `RetentionInDays = 7`.
