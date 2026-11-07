# 10.02 — GameDay Kịch Bản 2: Lỗi Định Tuyến Bất Đối Xứng (Asymmetric Routing Failure)

> **Mã bài lab:** `10.02`  
> **Trạng thái:** `COMPLETED`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã triển khai Transit Gateway và kích hoạt tính năng **Appliance Mode** trên Inspection VPC Attachment tại [Lab 02.03](../02-ha-tang-mang-co-ban/03-tgw-route-tables-and-attachments.md).
- Cụm Gateway Load Balancer và 2 máy chủ Suricata EC2 (`fabric-suricata-1a` và `fabric-suricata-1b`) đang hoạt động ở trạng thái Stateful Inspection.
- Ứng dụng Frontend và Order microservices đang kết nối thông suốt qua mạng trung gian.
- Đang mở phiên AWS Management Console tại Singapore (`ap-southeast-1`).

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để sửa đổi thuộc tính Appliance Mode trên TGW Attachment:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:ModifyTransitGatewayVpcAttachment",
        "ec2:DescribeTransitGatewayVpcAttachments",
        "logs:StartQuery",
        "logs:GetQueryResults"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Thay đổi tùy chọn TGW Attachment không tốn phí phụ trội ($0.00 USD).
- **Cảnh báo tính chất lỗi Stateful:** Khi tắt Appliance Mode, Transit Gateway sẽ phân phối các gói tin của cùng một luồng TCP theo thuật toán băm 5-tuple ngẫu nhiên qua các ENI ở các AZ khác nhau. Tường lửa Suricata là một thiết bị kiểm tra trạng thái (Stateful Firewall) — nếu nhận gói `SYN-ACK` mà không thấy gói `SYN` trước đó trong cùng một instance, nó sẽ đánh giá gói tin vi phạm giao thức và drop ngay lập tức. Đây là một trong những lỗi kinh điển và khó phát hiện nhất trong kiến trúc mạng Cloud nếu không hiểu rõ cơ chế Appliance Mode!

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Kiểm Tra Trạng Thái Kích Hoạt Appliance Mode Ban Đầu
1. Mở **VPC Console** tại Region Singapore (`ap-southeast-1`).
2. Tại menu bên trái, cuộn xuống nhóm **Transit gateways** -> Chọn **Transit gateway attachments**.
3. Tìm và chọn attachment của Inspection VPC: `fabric-insp-tgw-attachment`.
4. Tại tab **Details** ở nửa dưới màn hình:
   - Cuộn xuống tìm trường **Appliance mode support**.
   - Xác nhận giá trị hiện tại là **`enable`**.
5. Kiểm tra kết nối bình thường từ Edge Pod:
   ```bash
   kubectl exec deploy/frontend -n fabric-apps --context fabric-edge -- curl --fail --cacert /etc/fabric-ca/ca.crt -Iv https://core.fabric.internal/health
   ```
   *Kết quả:* Thành công 100% với mã phản hồi HTTP 200.

---

### Bước 2: Tiêm Lỗi — Tắt Tính Năng Appliance Mode (Fault Injection)
1. Trên trang chi tiết `fabric-insp-tgw-attachment`:
2. Nhấp vào menu **Actions** ở góc trên bên phải -> Chọn **Modify transit gateway attachment**.
3. Trong giao diện chỉnh sửa:
   - Tìm mục **Appliance mode support**.
   - Bỏ chọn checkbox: **`Enable`** (Chuyển sang chế độ Disable).
4. Ghi lại timestamp chính xác lúc bấm xác nhận: **$T_{fault}$**.
5. Nhấp nút màu cam **Modify transit gateway attachment**.
6. Quan sát trạng thái của Attachment chuyển sang `modifying` trong khoảng 30 - 60 giây, sau đó trở lại `available`.

---

### Bước 3: Quan Sát Hiện Tượng Định Tuyến Bất Đối Xứng (Asymmetric Flow Analysis)
1. **Gửi lưu lượng kiểm thử liên tục:**
   Thực hiện gửi một chuỗi 40 HTTP requests liên tiếp từ Edge Pod sang Core Backend:
   ```bash
   kubectl exec deploy/frontend -n fabric-apps --context fabric-edge -- sh -c '
   for i in $(seq 1 40); do
     curl --cacert /etc/fabric-ca/ca.crt -m 2 -s -o /dev/null -w "%{http_code}\n" https://core.fabric.internal/health || echo "TIMEOUT"
     sleep 0.1
   done | sort | uniq -c'
   ```
   - Đo tỷ lệ thành công/timeout thực tế. Phải chọn nguồn Edge AZ-a và Core target AZ-b, ghi AZ và 5-tuple để tăng khả năng tái hiện. Tắt appliance mode không bảo đảm timeout hoặc tỷ lệ 50%; nếu không tái hiện, ghi **NOT_REPRODUCED**, không đổi số liệu.
2. **Quan sát trực tiếp trên máy chủ Suricata:**
   Kết nối SSM Session Manager vào `fabric-suricata-1a` và `fabric-suricata-1b`, chạy bắt gói tin:
   ```bash
   # Trên node 1a
   sudo tcpdump -ni any 'tcp[tcpflags] & (tcp-syn|tcp-ack) != 0' -c 10
   ```
   - *Phát hiện:* Máy chủ node 1a chỉ thấy gói `SYN` từ `10.40.10.x` sang `10.50.20.x`, nhưng gói phản hồi `SYN-ACK` lại không bao giờ quay về node 1a.
   - Thay vào đó, máy chủ node 1b lại bất ngờ nhận được gói `SYN-ACK` phản hồi từ Core mà không hề có phiên `SYN` tạo trước trong memory!
   - Nhật ký `/var/log/suricata/suricata.log` hoặc `eve.json` cảnh báo: `TCP out-of-order packet dropped`.
3. Ghi lại mốc thời gian phát hiện và xác định nguyên nhân: **$T_{detect}$**.

---

### Bước 4: Khắc Phục Sự Cố — Kích Hoạt Lại Appliance Mode (Remediation)
1. Quay lại **VPC Console** -> **Transit gateway attachments**.
2. Chọn `fabric-insp-tgw-attachment` -> Nhấp **Actions** -> Chọn **Modify transit gateway attachment**.
3. Đánh dấu tích chọn lại vào checkbox: **`Enable`** tại mục **Appliance mode support**.
4. Ghi lại timestamp: **$T_{mitigate}$**.
5. Nhấp **Modify transit gateway attachment**.
6. Chờ cho đến khi trạng thái Attachment chuyển từ `modifying` về **`available`**.

---

### Bước 5: Kiểm Chứng Phục Hồi Hoàn Toàn (Verification)
1. Chạy lại bài kiểm thử 40 requests từ Edge Pod:
   ```bash
   kubectl exec deploy/frontend -n fabric-apps --context fabric-edge -- sh -c '
   for i in $(seq 1 40); do
     curl --cacert /etc/fabric-ca/ca.crt -m 2 -s -o /dev/null -w "%{http_code}\n" https://core.fabric.internal/health || echo "TIMEOUT"
     sleep 0.1
   done | sort | uniq -c'
   ```
   *Kết quả kỳ vọng:*
   ```text
   40 200
   ```
   Tỷ lệ thành công đạt **100%** (HTTP 200), không còn bất kỳ request nào bị TIMEOUT.
2. Ghi lại mốc thời gian phục hồi: **$T_{recover}$**.
3. Tính toán $MTTD = T_{detect} - T_{fault}$ và $MTTR = T_{recover} - T_{fault}$.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trực tiếp cờ ApplianceModeSupport trên AWS CLI:

```bash
ATTACHMENT_ID=$(aws ec2 describe-transit-gateway-vpc-attachments \
  --region ap-southeast-1 \
  --filters "Name=tag:Name,Values=fabric-insp-tgw-attachment" \
  --query 'TransitGatewayVpcAttachments[0].TransitGatewayAttachmentId' \
  --output text)

aws ec2 describe-transit-gateway-vpc-attachments \
  --region ap-southeast-1 \
  --transit-gateway-attachment-ids "$ATTACHMENT_ID" \
  --query 'TransitGatewayVpcAttachments[0].{AttachmentId:TransitGatewayAttachmentId,Name:Tags[?Key==`Name`].Value | [0],ApplianceMode:Options.ApplianceModeSupport,State:State}' \
  --output table
```

**Kỳ vọng kết quả sau phục hồi:**
```text
---------------------------------------------------------------------------------------
|                        DescribeTransitGatewayVpcAttachments                         |
+---------------------------------------+-----------------+----------------+----------+
|             AttachmentId              |  ApplianceMode  |     Name       |  State   |
+---------------------------------------+-----------------+----------------+----------+
|  tgw-attach-0123456789abcdef0         |  enable         |  fabric-insp...| available|
+---------------------------------------+-----------------+----------------+----------+
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Lệnh khẩn cấp một dòng qua AWS CLI để bật lại Appliance Mode ngay lập tức:

```bash
aws ec2 modify-transit-gateway-vpc-attachment \
  --region ap-southeast-1 \
  --transit-gateway-attachment-id "$ATTACHMENT_ID" \
  --options "ApplianceModeSupport=enable"
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

- `evidence/10-gameday/gameday-02-asymmetric-routing-drops.json`: Tỷ lệ lỗi thực, placement, flow captures và kết luận REPRODUCED/NOT_REPRODUCED.
- `evidence/10-gameday/gameday-02-suricata-out-of-state-logs.txt`: Trích xuất log Suricata ghi nhận gói tin bị hủy do mất đồng bộ trạng thái.
- `evidence/10-gameday/gameday-02-appliance-mode-verified.json`: Cấu hình attachment hiển thị `ApplianceModeSupport: enable`.

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [x] Ghi nhận kết quả thật sau khi tắt Appliance Mode; xác minh phân tích cơ chế TGW 5-tuple hash khi thiếu tính đối xứng AZ.
- [x] Chứng minh được rủi ro bất đối xứng trạng thái luồng TCP giữa 2 Availability Zones đối với thiết bị tường lửa Stateful Suricata.
- [x] Bật lại Appliance Mode thành công trên AWS (`Options.ApplianceModeSupport: enable`).
- [x] Tỷ lệ request thành công phục hồi về 100% (40/40 HTTP 200, 0 failed), lưu trữ bằng chứng đầy đủ tại `evidence/10-gameday/gameday-02-asymmetric-routing-drops.json`.
