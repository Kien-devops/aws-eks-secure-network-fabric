# 02.05 — Đặc Tả Centralized VPC Flow Logs Về CloudWatch Logs

> **Mã bài lab:** `02.05`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/02-network/05-vpc-flow-logs.json`

---

## 1. Mục Tiêu (Objective)

Thiết lập cơ chế thu thập L3/L4 telemetry tập trung từ toàn bộ 4 VPCs về CloudWatch Logs với chu kỳ lấy mẫu 1 phút và thời gian lưu trữ 7 ngày để phục vụ phân tích mạng, điều tra sự cố và kiểm thử GameDay.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Vị Trí / VPC / AZ | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-vpc-flow-logs-role` | `AWS::IAM::Role` | Global (IAM) | `arn:aws:iam::123456789012:role/fabric-vpc-flow-logs-role` |
| `/aws/vpc/fabric-centralized-flow-logs` | `AWS::Logs::LogGroup` | Regional (`ap-southeast-1`) | `arn:aws:logs:ap-southeast-1:123456789012:log-group:/aws/vpc/fabric-centralized-flow-logs` |
| `fabric-edge-flow-log` | `AWS::EC2::FlowLog` | `fabric-edge-vpc` | `fl-0efbee56492922d03` |
| `fabric-core-flow-log` | `AWS::EC2::FlowLog` | `fabric-core-vpc` | `fl-0cbb7f9eb6e05f24e` |
| `fabric-inspection-flow-log` | `AWS::EC2::FlowLog` | `fabric-inspection-vpc` | `fl-007c6cbfe07183b8b` |
| `fabric-egress-flow-log` | `AWS::EC2::FlowLog` | `fabric-egress-vpc` | `fl-04b9c24c290bd8008` |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-*-flow-log` | Flow Logs |
| `Project` | `aws-eks-secure-network-fabric` | Tất cả tài nguyên Flow Logs, IAM Role, Log Group |
| `Environment` | `prod` | Tất cả tài nguyên Flow Logs, IAM Role, Log Group |
| `ManagedBy` | `manual` | Quản trị cấu hình runtime thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Cấu Hình IAM Role & Permissions

- **Trust Policy Service Principal:** `vpc-flow-logs.amazonaws.com` (Action: `sts:AssumeRole`)
- **Inline Policy (`fabric-vpc-flow-logs-policy`):**
  - Actions: `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`, `logs:DescribeLogGroups`, `logs:DescribeLogStreams`
  - Resource: `*`

### 4.2 Cấu Hình CloudWatch Log Group

- **Log Group Name:** `/aws/vpc/fabric-centralized-flow-logs`
- **Retention Period:** `7 days` (1 tuần) nhằm tối ưu chi phí lưu trữ trong ngưỡng ngân sách $50.00 USD.
- **KMS Key:** Default AWS encryption.

### 4.3 Thông Số Kỹ Thuật VPC Flow Logs

| Thuộc Tính | Giá Trị Cấu Hình | Giải Thích Thiết Kế |
| :--- | :--- | :--- |
| **Traffic Type (Filter)** | `ALL` | Thu thập cả gói tin được chấp nhận (`ACCEPT`) và bị chặn (`REJECT`). |
| **Aggregation Interval** | `60 seconds` (1 minute) | Giảm độ trễ telemetry xuống tối thiểu, hỗ trợ phản hồi nhanh trong GameDay. |
| **Log Destination** | `cloud-watch-logs` | Đẩy trực tiếp vào CloudWatch Log Group tập trung. |
| **Log Format** | Default AWS (`${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action} ${log-status}`) | Chuẩn tương thích cao với CloudWatch Logs Insights. |
| **Target VPCs** | 4 VPCs (`edge`, `core`, `inspection`, `egress`) | Giám sát toàn diện mọi mặt phẳng mạng (Ingress, East-West, Egress, Inspection). |

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `02.01`: 4 VPCs phải được khởi tạo trước khi gắn Flow Logs.
- Phụ thuộc vào IAM Role `fabric-vpc-flow-logs-role` và CloudWatch Log Group `/aws/vpc/fabric-centralized-flow-logs` hoàn tất khởi tạo trước khi gọi API `CreateFlowLogs`.
- Làm nền tảng giám sát L3/L4 cho [Module 09](../09-toan-dien-observability/README.md) và các kịch bản kiểm thử [Module 10](../10-gameday-su-co-mang/README.md).

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng thái 4 Flow Logs** | `aws ec2 describe-flow-logs --filter "Name=log-group-name,Values=/aws/vpc/fabric-centralized-flow-logs"` | Cả 4 bản ghi đều có `FlowLogStatus: ACTIVE` và `DeliverLogsStatus: SUCCESS`. |
| **Chu kỳ tổng hợp** | Truy vấn thuộc tính `MaxAggregationInterval` của 4 Flow Logs | Giá trị là `60` (giây). |
| **Ghi nhận Log Stream** | `aws logs describe-log-streams --log-group-name /aws/vpc/fabric-centralized-flow-logs --order-by LastEventTime --descending --max-items 5` | Xuất hiện các Log Stream theo từng ENI với các bản ghi `ACCEPT`/`REJECT` gần nhất. |
| **Retention Policy** | `aws logs describe-log-groups --log-group-name-prefix /aws/vpc/fabric-centralized-flow-logs` | Thuộc tính `retentionInDays` trả về chính xác `7`. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo chi phí:** CloudWatch Logs tính phí nạp dữ liệu ($0.50 USD/GB). Nếu không giới hạn retention 7 ngày hoặc có bão gói tin drop không mong muốn, chi phí log có thể tăng đột biến.
- **Quy trình Rollback:**
  ```bash
  # Xóa 4 Flow Logs
  aws ec2 delete-flow-logs --region ap-southeast-1 --flow-log-ids fl-0efbee56492922d03 fl-0cbb7f9eb6e05f24e fl-007c6cbfe07183b8b fl-04b9c24c290bd8008

  # Xóa CloudWatch Log Group
  aws logs delete-log-group --region ap-southeast-1 --log-group-name /aws/vpc/fabric-centralized-flow-logs

  # Xóa Inline Policy và IAM Role
  aws iam delete-role-policy --role-name fabric-vpc-flow-logs-role --policy-name fabric-vpc-flow-logs-policy
  aws iam delete-role --role-name fabric-vpc-flow-logs-role
  ```
