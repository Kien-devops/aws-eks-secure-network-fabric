# 02.05 — Thiết Lập Centralized VPC Flow Logs Về CloudWatch Logs

> **Mã bài lab:** `02.05`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 30 phút  
> **Chi phí ước tính:** ~$0.50 USD / GB dữ liệu logs nạp vào CloudWatch Logs  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab từ [02.01](01-four-vpcs-and-subnets.md) đến [02.04](04-subnet-route-tables-chaining.md).
- Có quyền IAM quản trị để tạo IAM Role, Inline Policy và CloudWatch Log Group.
- Đang mở phiên AWS Console tại Singapore `ap-southeast-1`.

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
        "iam:CreateRole",
        "iam:PutRolePolicy",
        "iam:GetRole",
        "iam:PassRole",
        "logs:CreateLogGroup",
        "logs:PutRetentionPolicy",
        "logs:DescribeLogGroups",
        "ec2:CreateFlowLogs",
        "ec2:DescribeFlowLogs",
        "ec2:DeleteFlowLogs"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** CloudWatch Logs tính phí $0.50 USD/GB nạp vào (Ingestion) và $0.03 USD/GB lưu trữ hàng tháng. Để tối ưu hóa ngân sách $50.00 USD, **BẮT BUỘC ĐẶT RETENTION LÀ 7 NGÀY**.
- **Cảnh báo độ trễ:** VPC Flow Logs có độ trễ thu thập từ 1 đến 5 phút trước khi xuất hiện trên CloudWatch Logs. Khi kiểm thử GameDay, hãy chọn khoảng thời gian tổng hợp (aggregation interval) là **1 minute** để có phản hồi telemetry nhanh nhất.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Tạo IAM Role Cho Phép VPC Ghi Log Vào CloudWatch
1. Mở **IAM Console** (dịch vụ toàn cầu).
2. Tại menu điều hướng bên trái, chọn **Roles** -> Nhấp nút cam **Create role**.
3. **Step 1 - Select trusted entity:**
   - Trusted entity type: Chọn **Custom trust policy**.
   - Trong ô JSON Trust Policy, dán đoạn mã cho phép dịch vụ `vpc-flow-logs.amazonaws.com`:
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Sid": "AllowVPCFlowLogsAssumeRole",
           "Effect": "Allow",
           "Principal": {
             "Service": "vpc-flow-logs.amazonaws.com"
           },
           "Action": "sts:AssumeRole"
         }
       ]
     }
     ```
   - Nhấp nút **Next** ở cuối trang.
4. **Step 2 - Add permissions:**
   - Nhấp **Next** (sẽ gán inline policy sau khi tạo role).
5. **Step 3 - Name, review, and create:**
   - **Role name:** Nhập `fabric-vpc-flow-logs-role`.
   - **Description:** Nhập `Allows Amazon VPC Flow Logs to push traffic records to CloudWatch Logs`.
   - Nhấp **Create role**.
6. Tại danh sách Roles, tìm và nhấp vào `fabric-vpc-flow-logs-role`:
   - Chọn menu **Add permissions** -> Chọn **Create inline policy**.
   - Chuyển sang tab **JSON** và dán đoạn chính sách quyền ghi log:
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Effect": "Allow",
           "Action": [
             "logs:CreateLogGroup",
             "logs:CreateLogStream",
             "logs:PutLogEvents",
             "logs:DescribeLogGroups",
             "logs:DescribeLogStreams"
           ],
           "Resource": "*"
         }
       ]
     }
     ```
   - Nhấp **Next** -> Policy name: Nhập `fabric-vpc-flow-logs-policy` -> Nhấp **Create policy**.
   - Sao chép lại **Role ARN** (dạng `arn:aws:iam::123456789012:role/fabric-vpc-flow-logs-role`).

### Bước 2: Khởi Tạo CloudWatch Log Group Tập Trung
1. Trên thanh tìm kiếm AWS Console, nhập `CloudWatch` và chọn dịch vụ **CloudWatch**.
2. Đảm bảo góc trên bên phải hiển thị vùng **Singapore `ap-southeast-1`**.
3. Tại menu bên trái, mở rộng mục **Logs** -> Chọn **Log groups**.
4. Nhấp nút cam **Create log group** ở góc trên bên phải:
   - **Log group name:** Nhập `/aws/vpc/fabric-centralized-flow-logs`.
   - **Retention setting:** Chọn **7 days (1 week)** để tiết kiệm chi phí.
   - **KMS key ID:** Để trống (sử dụng mã hóa mặc định AWS).
   - **Tags:** Key: `Project` | Value: `aws-eks-secure-network-fabric`.
5. Nhấp **Create**.

### Bước 3: Bật Flow Logs Trên Cả 4 VPCs
Quay lại **VPC Console** tại Singapore `ap-southeast-1`:
1. Tại menu bên trái, chọn **Your VPCs**.
2. Thực hiện tuần tự cho từng VPC: `fabric-edge-vpc`, `fabric-core-vpc`, `fabric-inspection-vpc`, và `fabric-egress-vpc`:
   - Đánh dấu tích vào checkbox của VPC.
   - Ở nửa dưới màn hình, chọn tab **Flow logs**.
   - Nhấp nút **Create flow log**.
   - **Flow log settings:**
     - **Name:** Nhập tương ứng (ví dụ: `fabric-edge-flow-log`).
     - **Filter:** Chọn **All** (Ghi lại cả gói tin được chấp nhận `ACCEPT` và gói tin bị từ chối `REJECT`).
     - **Maximum aggregation interval:** Chọn **1 minute** (Khoảng thời gian gộp 1 phút phục vụ kiểm thử GameDay chi tiết).
     - **Destination:** Chọn **Send to CloudWatch Logs**.
     - **Destination log group:** Nhập hoặc chọn `/aws/vpc/fabric-centralized-flow-logs`.
     - **IAM role:** Chọn `fabric-vpc-flow-logs-role`.
     - **Log record format:** Chọn **AWS default format** (Bao gồm version, account-id, interface-id, srcaddr, dstaddr, srcport, dstport, protocol, packets, bytes, start, end, action, log-status).
     - **Log file format:** Chọn **Plain text**.
   - Nhấp nút cam **Create flow log**.
3. Xác nhận trên tab Flow logs của cả 4 VPCs đều hiển thị dòng cấu hình với trạng thái **Active**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy các lệnh xác minh trạng thái Flow Logs đang hoạt động:
```bash
# 1. Liệt kê 4 Flow Logs gắn trên 4 VPCs
aws ec2 describe-flow-logs --region ap-southeast-1 \
  --filter "Name=log-group-name,Values=/aws/vpc/fabric-centralized-flow-logs" \
  --query 'FlowLogs[*].{FlowLogId:FlowLogId,ResourceId:ResourceId,TrafficType:TrafficType,State:FlowLogStatus,Interval:MaxAggregationInterval}' \
  --output table

# 2. Kiểm tra các Log Streams đầu tiên vừa được đẩy về CloudWatch
aws logs describe-log-streams --region ap-southeast-1 \
  --log-group-name /aws/vpc/fabric-centralized-flow-logs \
  --order-by LastEventTime --descending --max-items 5 \
  --query 'logStreams[*].{StreamName:logStreamName,CreationTime:creationTime}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Nếu cần gỡ bỏ Flow Logs để dừng nạp dữ liệu:
1. Tại VPC Console -> Your VPCs -> Chọn từng VPC -> Tab Flow logs -> Chọn flow log -> Nhấp **Actions** -> Chọn **Delete flow log**.
2. Xóa CloudWatch Log Group:
   ```bash
   aws logs delete-log-group --region ap-southeast-1 --log-group-name /aws/vpc/fabric-centralized-flow-logs
   ```
3. Xóa IAM Role `fabric-vpc-flow-logs-role`.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/02-network/05-vpc-flow-logs.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] IAM Role `fabric-vpc-flow-logs-role` có Trust Policy đúng với service `vpc-flow-logs.amazonaws.com`.
- [ ] CloudWatch Log Group `/aws/vpc/fabric-centralized-flow-logs` được tạo với Retention 7 ngày.
- [ ] Toàn bộ 4 VPCs đều có Flow Log ở trạng thái `ACTIVE`.
- [ ] Bộ lọc được đặt là `ALL` và chu kỳ gộp là `1 minute`.
- [ ] Có ít nhất 1 Log Stream xuất hiện trong Log Group ghi nhận lưu lượng mạng thực tế.
