# 09.02 — Đặc Tả Thu Thập & Đẩy Nhật Ký Suricata EVE Logs Về CloudWatch

> **Mã bài lab:** `09.02`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/09-observability/suricata-eve-streams.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả quy trình thu thập và đẩy tập trung nhật ký kiểm tra gói tin sâu Suricata EVE JSON (`/var/log/suricata/eve.json`) từ 2 máy chủ ảo Inspection EC2 về CloudWatch Log Group bằng Amazon CloudWatch Unified Agent thông qua kênh truyền an toàn không mở SSH.

---

## 2. Tài Nguyên (Resources)

| Tên Tài Nguyên | Loại Resource | Vị Trí / Máy Chủ Áp Dụng | Runtime ID / ARN |
| :--- | :--- | :--- | :--- |
| `amazon-cloudwatch-agent` | `Linux::Daemon` | `fabric-suricata-1a`, `1b` | Quản trị bởi systemd |
| `CloudWatchAgentServerPolicy` | `AWS::IAM::Policy` | Global (IAM) | Gắn vào IAM Role của SSM Instance Profile |
| `/aws/suricata/fabric-inspection-eve` | `AWS::Logs::LogGroup` | Regional (`ap-southeast-1`) | Retention: `7 days` |
| Log Streams EVE | `AWS::Logs::LogStream` | Log Group Suricata | Định dạng `{instance_id}-eve` và `{instance_id}-daemon` |

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `/aws/suricata/fabric-inspection-eve` | Log Group, Cấu hình Agent |
| `Project` | `aws-eks-secure-network-fabric` | Log Group, Cấu hình Agent |
| `Environment` | `prod` | Log Group, Cấu hình Agent |
| `Appliance` | `suricata-gwlb` | Dán nhãn máy chủ phát sinh log |
| `ManagedBy` | `manual` | Quản trị agent thu thập nhật ký |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Cấu Hình Agent JSON (`amazon-cloudwatch-agent.json`)

```json
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
```

### 4.2 Yêu Cầu An Ninh & Quản Trị

- **Giao Thức:** Đẩy log qua CloudWatch Interface VPC Endpoint hoặc S3 Gateway Endpoint đã cấu hình tại Module 02.
- **Không Mở Port 22:** Quản trị cấu hình và theo dõi trạng thái agent 100% qua AWS Systems Manager Session Manager.

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `05.01`: Cả hai máy chủ Suricata EC2 đang hoạt động và sinh log tại `/var/log/suricata/eve.json`.
- Phụ thuộc vào `09.01`: Log Group `/aws/suricata/fabric-inspection-eve` sẵn sàng.
- Là nguồn dữ liệu L7 đầu vào cho các câu truy vấn điều tra sự cố tại `09.03`.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng Thái Daemon** | `systemctl is-active amazon-cloudwatch-agent` | Trả về `active`. |
| **Log Streams trên CloudWatch** | `aws logs describe-log-streams --log-group-name "/aws/suricata/fabric-inspection-eve"` | Xuất hiện các streams có đuôi `-eve` và `-daemon` tương ứng với 2 Instance IDs. |
| **Cấu Trúc Sự Kiện EVE** | `aws logs get-log-events --log-group-name "/aws/suricata/fabric-inspection-eve" --log-stream-name <StreamName> --limit 1` | Bản ghi JSON chứa đầy đủ các trường `event_type`, `src_ip`, `dest_ip`, `proto`. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo đầy ổ cứng (Disk Full):** File `eve.json` có thể tăng trưởng rất nhanh nếu có bão lưu lượng. Bắt buộc kích hoạt `logrotate` trên máy chủ Linux để xoay vòng file log.
- **Quy trình Rollback:**
  ```bash
  # Dừng và gỡ bỏ CloudWatch Agent trên instance
  sudo systemctl stop amazon-cloudwatch-agent
  sudo systemctl disable amazon-cloudwatch-agent
  ```
