# 09.02 — Thu Thập & Đẩy Nhật Ký Suricata EVE Logs (eve.json) Về CloudWatch

> **Mã bài lab:** `09.02`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 40 phút  
> **Chi phí ước tính:** ~$0.10 USD (Ingestion log data)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn tất cài đặt cụm EC2 Suricata IDS/IPS trong Inspection VPC tại [Lab 05.01](../05-gwlb-suricata-ids-ips/01-suricata-ec2-instances.md).
- Hai máy chủ EC2 `fabric-suricata-1a` và `fabric-suricata-1b` đang chạy (`running`) và Suricata đang sinh log tại `/var/log/suricata/eve.json`.
- Log Group `/aws/suricata/fabric-inspection-eve` đã được tạo sẵn từ [Lab 09.01](01-centralized-cloudwatch-log-groups.md).
- Các máy chủ Suricata đã được kích hoạt AWS Systems Manager (SSM) Agent để truy cập từ xa qua Session Manager mà không cần mở port SSH 22.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Quyền IAM cần cấp cho IAM Role gán vào máy chủ ảo Suricata EC2 (`fabric-suricata-instance-role`):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams",
        "logs:DescribeLogGroups"
      ],
      "Resource": "arn:aws:logs:ap-southeast-1:123456789012:log-group:/aws/suricata/fabric-inspection-eve:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssm:UpdateInstanceInformation",
        "ssmmessages:CreateControlChannel",
        "ssmmessages:CreateDataChannel",
        "ssmmessages:OpenControlChannel",
        "ssmmessages:OpenDataChannel"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** CloudWatch Agent miễn phí cài đặt; dữ liệu log đẩy vào CloudWatch tính cước tiêu chuẩn ($0.50/GB).
- **Cảnh báo đầy đĩa (Disk Exhaustion):** File `/var/log/suricata/eve.json` có thể phình to rất nhanh khi có lưu lượng tải cao. Cần đảm bảo cơ chế `logrotate` trên Linux được kích hoạt đồng thời để xoay vòng và nén file log cũ trên ổ đĩa cục bộ.
- **An toàn bảo mật:** Tuyệt đối không mở cổng SSH (port 22) ra Internet hoặc gán Public IP cho máy chủ Suricata. Mọi thao tác quản trị phải đi qua AWS Systems Manager Session Manager.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Gắn Policy Quản Trị Vào IAM Role Của Máy Chủ Suricata
1. Mở **AWS IAM Console** tại Singapore (`ap-southeast-1`).
2. Tại menu bên trái, nhấp chọn **Roles**.
3. Tại ô tìm kiếm, gõ `fabric-suricata-instance-role` và nhấp vào tên Role.
4. Tại tab **Permissions**, nhấp vào nút **Add permissions** -> Chọn **Attach policies**.
5. Trong ô tìm kiếm policy, nhập `CloudWatchAgentServerPolicy`.
6. Tích chọn checkbox cạnh policy `CloudWatchAgentServerPolicy`.
7. Nhấp nút xanh **Add permissions** ở góc dưới bên phải để hoàn tất.

---

### Bước 2: Kết Nối Vào Máy Chủ Suricata Qua SSM Session Manager
1. Mở **Amazon EC2 Console** tại Region Singapore (`ap-southeast-1`).
2. Tại menu bên trái, chọn **Instances**.
3. Tìm kiếm máy chủ ảo: `fabric-suricata-1a`.
4. Tích chọn checkbox cạnh `fabric-suricata-1a` -> Nhấp vào nút **Connect** ở thanh công cụ trên cùng.
5. Chọn tab **Session Manager**.
6. Nhấp nút màu cam **Connect**. Trình duyệt sẽ mở ra một cửa sổ terminal an toàn chạy dưới quyền `ssm-user`.
7. Chuyển sang quyền root để thao tác cài đặt hệ thống:
   ```bash
   sudo su -
   ```

---

### Bước 3: Tải Và Cài Đặt Amazon CloudWatch Unified Agent
Chạy các lệnh sau trực tiếp trong cửa sổ Session Manager của `fabric-suricata-1a`:

1. Tải gói cài đặt CloudWatch Agent dành cho Ubuntu/Debian x86_64 tại Region Singapore:
   ```bash
   wget https://amazoncloudwatch-agent-ap-southeast-1.s3.ap-southeast-1.amazonaws.com/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
   ```
2. Thực hiện cài đặt gói `.deb`:
   ```bash
   dpkg -i -E ./amazon-cloudwatch-agent.deb
   ```
3. Xác nhận gói đã được cài đặt thành công tại thư mục `/opt/aws/amazon-cloudwatch-agent/`.

---

### Bước 4: Soạn Thảo Cấu Hình Thu Thập EVE JSON Cho CloudWatch Agent
1. Tạo thư mục cấu hình nếu chưa có:
   ```bash
   mkdir -p /opt/aws/amazon-cloudwatch-agent/etc/
   ```
2. Soạn file cấu hình `/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json`:
   ```bash
   cat << 'EOF' > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
   {
     "agent": {
       "metrics_collection_interval": 60,
       "run_as_user": "root"
     },
     "logs": {
       "logs_collected": {
         "files": {
           "collect_list": [
             {
               "file_path": "/var/log/suricata/eve.json",
               "log_group_name": "/aws/suricata/fabric-inspection-eve",
               "log_stream_name": "{instance_id}-eve",
               "timestamp_format": "%Y-%m-%dT%H:%M:%S.%f%z",
               "timezone": "UTC"
             },
             {
               "file_path": "/var/log/suricata/suricata.log",
               "log_group_name": "/aws/suricata/fabric-inspection-eve",
               "log_stream_name": "{instance_id}-daemon",
               "timezone": "UTC"
             }
           ]
         }
       }
     }
   }
   EOF
   ```

---

### Bước 5: Khởi Động Và Kích Hoạt CloudWatch Agent Service
1. Khởi chạy CloudWatch Agent với file cấu hình vừa tạo:
   ```bash
   /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
     -a fetch-config \
     -m ec2 \
     -s \
     -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
   ```
2. Kiểm tra trạng thái hoạt động của daemon:
   ```bash
   systemctl status amazon-cloudwatch-agent --no-pager
   ```
   *Yêu cầu:* Trạng thái hiển thị `Active: active (running)`.

---

### Bước 6: Lặp Lại Thao Tác Cho Máy Chủ Suricata Thứ Hai (`fabric-suricata-1b`)
1. Quay lại trang **EC2 Instances Console**.
2. Chọn máy chủ ảo `fabric-suricata-1b` -> Nhấp **Connect** -> Tab **Session Manager** -> Nhấp **Connect**.
3. Thực thi lặp lại toàn bộ các bước 2, 3, 4, và 5 trên node `1b`.

---

### Bước 7: Xác Minh Log Streams Trên CloudWatch Console
1. Mở dịch vụ **Amazon CloudWatch** -> Chọn **Log groups**.
2. Tìm và nhấp vào Log Group: `/aws/suricata/fabric-inspection-eve`.
3. Chọn tab **Log streams**.
4. Xác nhận sự hiện diện của 2 stream mới có định dạng:
   - `i-xxxxxxxxxxxxxxxxx-eve` (Instance ID của node 1a)
   - `i-yyyyyyyyyyyyyyyyy-eve` (Instance ID của node 1b)
5. Nhấp vào stream của node 1a, xác nhận các bản ghi JSON của Suricata với các trường `event_type`, `src_ip`, `dest_ip`, `proto` đang liên tục được ingest thành công.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra danh sách Log Streams và đọc thử bản ghi EVE mới nhất qua AWS CLI:

```bash
# Liệt kê các Log Streams trong Log Group
aws logs describe-log-streams \
  --region ap-southeast-1 \
  --log-group-name "/aws/suricata/fabric-inspection-eve" \
  --order-by "LastEventTime" \
  --descending \
  --query 'logStreams[*].{StreamName:logStreamName,LastEventTimestamp:lastEventTimestamp,StoredBytes:storedBytes}' \
  --output table

# Đọc thử 2 sự kiện log mới nhất từ Stream
STREAM_NAME=$(aws logs describe-log-streams \
  --region ap-southeast-1 \
  --log-group-name "/aws/suricata/fabric-inspection-eve" \
  --order-by "LastEventTime" \
  --descending \
  --query 'logStreams[0].logStreamName' \
  --output text)

aws logs get-log-events \
  --region ap-southeast-1 \
  --log-group-name "/aws/suricata/fabric-inspection-eve" \
  --log-stream-name "$STREAM_NAME" \
  --limit 2 \
  --query 'events[*].message' \
  --output text
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Khi cần dừng thu thập hoặc gỡ bỏ CloudWatch Agent:
1. Kết nối vào từng node Suricata qua SSM Session Manager:
   ```bash
   sudo systemctl stop amazon-cloudwatch-agent
   sudo systemctl disable amazon-cloudwatch-agent
   sudo dpkg -r amazon-cloudwatch-agent
   ```
2. Trên CloudWatch Logs Console: Xóa các Log Streams không dùng hoặc xóa Log Group nếu muốn đặt lại môi trường.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

- `evidence/09-observability/suricata-eve-streams.json`: Danh sách Log Streams hoạt động.
- `evidence/09-observability/suricata-sample-eve-event.json`: Bản ghi mẫu của sự kiện `alert` hoặc `flow` được định dạng JSON trích xuất từ CloudWatch.

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Policy `CloudWatchAgentServerPolicy` được gắn thành công vào role EC2.
- [ ] Dịch vụ `amazon-cloudwatch-agent` hoạt động ổn định (`active (running)`) trên cả 2 node Suricata.
- [ ] Log Group `/aws/suricata/fabric-inspection-eve` xuất hiện 2 stream tương ứng với 2 Instance ID.
- [ ] Các sự kiện trong stream là cấu trúc JSON hợp lệ chứa đầy đủ thông tin L3/L4/L7 từ Suricata engine.
