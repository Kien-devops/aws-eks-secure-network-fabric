# 09.02 — Thu Thập & Đẩy Nhật Ký Suricata EVE Logs (eve.json) Về CloudWatch

> **Trạng thái:** Hướng dẫn thực hành cài đặt agent thu thập nhật ký trên máy chủ ảo Suricata.  
> **Áp dụng cho:** Đẩy toàn bộ dữ liệu sự kiện IDS/IPS chi tiết từ `/var/log/suricata/eve.json` lên đám mây để phân tích và cảnh báo.

---

## 1. Mục Tiêu Kỹ Thuật

- Cài đặt **AWS CloudWatch Unified Agent** trên cả 2 máy chủ ảo `fabric-suricata-appliance-1a` và `1b`.
- Cấu hình Agent theo dõi file log sự kiện Extensible Event Format (**`eve.json`**) của Suricata theo thời gian thực (Real-time log tailing).
- Đẩy dữ liệu log vào Log Group `/aws/suricata/fabric-inspection-eve` tại Singapore.

---

## 2. Các Bước Thực Hiện Chi Tiết

### Bước 1: Gắn IAM Role Cho Phép Đẩy Log Vào Máy Chủ EC2
1. Tại dịch vụ **IAM**, mở Role gán cho máy chủ Suricata EC2 (`fabric-suricata-instance-profile`).
2. Gắn policy quản lý của AWS: **`CloudWatchAgentServerPolicy`**.

---

### Bước 2: Cài Đặt CloudWatch Unified Agent
Kết nối vào máy chủ Suricata qua SSM Session Manager:
```bash
# Tải và cài đặt agent trên Amazon Linux / Ubuntu
wget https://amazoncloudwatch-agent-ap-southeast-1.s3.ap-southeast-1.amazonaws.com/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb
```

---

### Bước 3: Tạo File Cấu Hình Cho CloudWatch Agent
Tạo file cấu hình tại `/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json`:
```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/suricata/eve.json",
            "log_group_name": "/aws/suricata/fabric-inspection-eve",
            "log_stream_name": "{instance_id}",
            "timezone": "UTC"
          }
        ]
      }
    }
  }
}
```

Khởi động CloudWatch Agent:
```bash
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
```

---

## 3. Xác Minh (Verification)

Kiểm tra trạng thái Agent:
```bash
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -m ec2 -a status
```
> Kết quả: `"status": "running"`.

Kiểm tra luồng log trên AWS Console: Mở Log Group `/aws/suricata/fabric-inspection-eve`, quan sát log stream mang tên Instance ID của cả 2 máy chủ đã xuất hiện và cập nhật dữ liệu.

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] CloudWatch Agent chạy liên tục trên cả 2 máy chủ Suricata.
- [ ] Sự kiện trong `eve.json` được stream lên CloudWatch Logs với độ trễ dưới 5 giây.

