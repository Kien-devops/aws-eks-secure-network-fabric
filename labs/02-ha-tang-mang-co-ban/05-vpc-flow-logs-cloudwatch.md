# 02.05 — Kích Hoạt VPC Flow Logs Cho Toàn Bộ 4 VPCs Đẩy Về CloudWatch Logs

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Thiết lập khả năng giám sát mạng tầng thấp nhất (L3/L4 packet flow) cho cả 4 VPCs.

---

## 1. Mục Tiêu Kỹ Thuật

- Khởi tạo IAM Role `fabric-vpc-flow-logs-role` cho phép dịch vụ VPC đẩy log về CloudWatch Logs.
- Khởi tạo 4 CloudWatch Log Groups tương ứng với 4 VPCs.
- Kích hoạt VPC Flow Logs trên cả 4 VPCs ở mức độ giám sát toàn bộ (`ALL` traffic: cả ACCEPT và REJECT).

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Khởi Tạo IAM Role Cho VPC Flow Logs
1. Mở dịch vụ **IAM** -> Chọn **Roles** -> Nhấp **Create role**.
2. **Trusted entity type:** Chọn `AWS service`.
3. **Use case:** Chọn `EC2` -> Nhấp **Next**.
4. Gắn policy: Tạo policy tùy chỉnh với quyền:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Effect": "Allow",
      "Resource": "*"
    }
  ]
}
```
5. Tại mục **Trust relationship**, sửa `Principal` thành `"Service": "vpc-flow-logs.amazonaws.com"`.
6. Đặt tên Role: `fabric-vpc-flow-logs-role` -> Nhấp **Create role**.

---

### Bước 2: Tạo CloudWatch Log Groups
1. Mở dịch vụ **CloudWatch** tại `ap-southeast-1` -> Chọn **Log groups** -> Nhấp **Create log group**.
2. Tạo lần lượt 4 Log Groups:
   - `/aws/vpc/fabric-edge-flow`
   - `/aws/vpc/fabric-core-flow`
   - `/aws/vpc/fabric-inspection-flow`
   - `/aws/vpc/fabric-egress-flow`
3. Retention period: Đặt `7 days` để tối ưu chi phí.

---

### Bước 3: Kích Hoạt Flow Logs Trên Từng VPC
1. Quay lại **VPC Console** -> Chọn **Your VPCs**.
2. Chọn `fabric-edge-vpc` -> Chọn tab **Flow logs** bên dưới -> Nhấp **Create flow log**.
3. **Cấu hình Flow log:**
   - **Name:** `fabric-edge-flow-log`
   - **Filter:** Chọn `All`.
   - **Maximum aggregation interval:** Chọn `1 minute` (để log hiển thị nhanh khi test sự cố).
   - **Destination:** Chọn `Send to CloudWatch Logs`.
   - **Destination log group:** Chọn `/aws/vpc/fabric-edge-flow`.
   - **IAM role:** Chọn `fabric-vpc-flow-logs-role`.
   - **Log record format:** Chọn `AWS default format`.
4. Nhấp **Create flow log**.
5. Lặp lại thao tác trên cho `fabric-core-vpc`, `fabric-inspection-vpc`, và `fabric-egress-vpc`.

---

## 3. Xác Minh (Verification)

Kiểm tra trạng thái Flow Logs qua AWS CLI:
```bash
aws ec2 describe-flow-logs \
  --region ap-southeast-1 \
  --query 'FlowLogs[*].{LogId:FlowLogId,VpcId:ResourceId,Status:FlowLogStatus,LogGroup:LogGroupName}' \
  --output table
```
> Kết quả: Cả 4 Flow Logs đều có `FlowLogStatus = ACTIVE`.

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] 4 VPC Flow Logs được kích hoạt thành công trên 4 VPCs.
- [ ] Dữ liệu log stream xuất hiện trong CloudWatch Log Groups sau vài phút.
