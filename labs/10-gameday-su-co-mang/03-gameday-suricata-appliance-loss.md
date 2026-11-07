# 10.03 — GameDay Kịch Bản 3: Tắt Cưỡng Bức Máy Chủ Tường Lửa (Suricata Appliance Failover)

> **Mã bài lab:** `10.03`  
> **Trạng thái:** `DRAFT`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã triển khai Gateway Load Balancer `fabric-gwlb` và Target Group `fabric-suricata-tg` tại [Module 05](../05-gwlb-suricata-ids-ips/02-gateway-load-balancer-and-target-group.md).
- Cả hai máy chủ Suricata EC2 `fabric-suricata-1a` (AZ-a) và `fabric-suricata-1b` (AZ-b) đang ở trạng thái `healthy` trên GWLB Target Group.
- Lưu lượng East-West giữa Edge EKS và Core EKS đang hoạt động ổn định.
- Đang mở phiên AWS Management Console tại Singapore (`ap-southeast-1`).

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để thực hiện dừng máy chủ EC2 và giám sát sức khỏe Target Group:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:StopInstances",
        "ec2:StartInstances",
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceStatus",
        "elasticloadbalancing:DescribeTargetHealth",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeLoadBalancers"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Thao tác dừng và khởi động lại máy chủ EC2 kiểm thử không làm tăng chi phí ($0.00 USD).
- **Cơ chế:** dùng đúng HTTP port 80, interval 10s, thresholds 2, timeout 5s ở 05.02; bật GWLB cross-zone. Ghi target failover attributes. Mặc định phiên cũ không rebalance; đo kết nối mới riêng. Không cam kết MTTR từ health interval.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Kiểm Tra Trạng Thái Sức Khỏe Ban Đầu Của Cụm GWLB
1. Đăng nhập vào **AWS Management Console** -> Chọn Region Singapore (`ap-southeast-1`).
2. Mở dịch vụ **EC2**.
3. Tại menu bên trái, cuộn xuống nhóm **Load Balancing** -> Chọn **Target Groups**.
4. Nhấp vào tên Target Group: `fabric-suricata-tg`.
5. Chọn tab **Targets**:
   - Xác nhận có 2 targets đang đăng ký:
     - `fabric-suricata-1a`: IP thật thuộc `10.70.10.0/24`, healthy.
     - `fabric-suricata-1b`: IP thật thuộc `10.70.11.0/24`, healthy.

---

### Bước 2: Kích Hoạt Lưu Lượng Kiểm Thử Nền (Baseline Traffic Generation)
Từ máy trạm quản trị hoặc từ một Pod trong Edge EKS, chạy vòng lặp gửi HTTP requests liên tục (tần suất ~5 requests/giây) để quan sát tỷ lệ mất gói:

```bash
kubectl exec deploy/frontend -n fabric-apps --context fabric-edge -- sh -c '
while true; do
  ts=$(date +"%H:%M:%S")
  code=$(curl --cacert /etc/fabric-ca/ca.crt -m 2 -s -o /dev/null -w "%{http_code}" https://core.fabric.internal/health || echo "ERR")
  echo "[$ts] HTTP Status: $code"
  sleep 0.2
done'
```
*Ghi nhận:* Các dòng hiển thị liên tục `[HH:MM:SS] HTTP Status: 200`.

---

### Bước 3: Tiêm Lỗi — Tắt Cưỡng Bức Máy Chủ Suricata AZ-a (Fault Injection)
1. Trên giao diện **EC2 Console**, nhấp chọn menu **Instances** ở thanh điều hướng bên trái.
2. Tìm kiếm máy chủ ảo: `fabric-suricata-1a`.
3. Tích chọn checkbox cạnh `fabric-suricata-1a`.
4. Nhấp vào menu **Instance state** ở thanh công cụ phía trên -> Chọn **Stop instance**.
5. Hộp thoại xác nhận hiện ra: Nhấp nút màu đỏ **Stop**.
6. **Ghi lại mốc thời gian chính xác lúc bấm Stop:** **$T_{fault}$** (Ví dụ: `10:30:00 UTC`).

---

### Bước 4: Quan Sát Quá Trình GWLB Phát Hiện & Chuyển Vùng Dự Phòng (Failover Analysis)
1. Quay lại trang **EC2 Console** -> **Target Groups** -> Chọn `fabric-suricata-tg` -> Tab **Targets**.
2. Nhấp nút biểu tượng làm mới (Refresh) liên tục mỗi 2 giây:
   - Ghi timestamp từng lần đổi trạng thái target; không giả định mốc 10 giây hay trạng thái `unused`. Dùng kết nối mới để đo failover, phiên cũ đo riêng.
   - Ghi thời điểm đầu quan sát unhealthy và reason thực tế; không dự đoán cố định giây thứ 12–15.
3. **Ghi lại mốc thời gian phát hiện của GWLB:** **$T_{detect}$**.
4. **Quan sát terminal gửi lưu lượng:**
   - Trong khoảng cửa sổ 10 - 15 giây khi node 1a vừa sập, một số requests thuộc luồng cũ đi qua AZ-a sẽ nhận mã `ERR` (gián đoạn tạm thời).
   - Với cross-zone enabled, kiểm tra **kết nối mới** chuyển sang 1b bằng capture/EVE. Phiên TCP đã tồn tại có thể đứt; không coi GWLB đồng bộ state Suricata.
   - Luồng log trên terminal lập tức phục hồi và trả về đều đặn `HTTP Status: 200`.
5. **Ghi lại mốc thời gian phục hồi hoàn toàn:** **$T_{recover}$**.
6. **Tính toán chỉ số phục hồi:**
   - Detection Time = $T_{detect} - T_{fault}$; MTTR = $T_{recover} - T_{fault}$. Điền số đo và số mẫu sau thử, không điền trước.

---

### Bước 5: Khôi Phục Máy Chủ Suricata AZ-a (Incident Remediation)
1. Quay lại trang **EC2 Instances**.
2. Chọn `fabric-suricata-1a`.
3. Nhấp vào menu **Instance state** -> Chọn **Start instance**.
4. Quan sát Instance State chuyển từ `stopped` -> `pending` -> **`running`**, và Status check đạt **`2/2 checks passed`**.
5. Sau khi hệ điều hành khởi động, daemon `suricata` và tunnel handler tự động chạy thông qua systemd.
6. Mở lại **Target Groups** -> `fabric-suricata-tg` -> Tab **Targets**:
   - Quan sát node 1a sau 3 chu kỳ health check thành công (khoảng 15s) tự động trở lại màu xanh: **`healthy`**.
   - Cụm GWLB tự động phân tải đều lưu lượng trên cả 2 Availability Zones.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Theo dõi sức khỏe Target Group và trạng thái Instance qua AWS CLI:

```bash
# 1. Kiểm tra trạng thái Target Health của GWLB
GWLB_TG_ARN=$(aws elbv2 describe-target-groups \
  --region ap-southeast-1 \
  --names "fabric-suricata-tg" \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

aws elbv2 describe-target-health \
  --region ap-southeast-1 \
  --target-group-arn "$GWLB_TG_ARN" \
  --query 'TargetHealthDescriptions[*].{Id:Target.Id,Port:Target.Port,State:TargetHealth.State,Reason:TargetHealth.Reason}' \
  --output table

# 2. Kiểm tra trạng thái 2 máy chủ EC2
aws ec2 describe-instances \
  --region ap-southeast-1 \
  --filters "Name=tag:Name,Values=fabric-suricata-1*" \
  --query 'Reservations[*].Instances[*].{InstanceId:InstanceId,Name:Tags[?Key==`Name`].Value | [0],State:State.Name,PrivateIp:PrivateIpAddress}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Lệnh khẩn cấp qua AWS CLI để bật lại máy chủ Suricata nếu giao diện Console bị trục trặc:

```bash
SURICATA_1A_ID=$(aws ec2 describe-instances \
  --region ap-southeast-1 \
  --filters "Name=tag:Name,Values=fabric-suricata-1a" \
  --query 'Reservations[0].Instances[0].InstanceId' \
  --output text)

aws ec2 start-instances --region ap-southeast-1 --instance-ids "$SURICATA_1A_ID"
```

Chờ EC2 status checks và SSM Online. Session Manager → kiểm tra `sudo systemctl status fabric-suricata gwlb-handler`, NFQUEUE/routing hooks. Nếu đã dừng service, khởi động lại **cả hai** bằng `sudo systemctl restart fabric-suricata gwlb-handler`; chờ target healthy rồi chạy controls. Không coi StartInstances thành công là traffic đã phục hồi.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

- `evidence/10-gameday/gameday-03-gwlb-failover-timeline.json`: Mốc thời gian $T_{fault}$, $T_{detect}$, $T_{recover}$.
- `evidence/10-gameday/gameday-03-target-health-unhealthy.json`: Dữ liệu JSON `describe-target-health` tại thời điểm node 1a bị unheathy.
- `evidence/10-gameday/gameday-03-target-health-restored.json`: Dữ liệu JSON xác nhận cả 2 targets đều `healthy` sau khi bật lại.

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Thực hiện tắt máy chủ `fabric-suricata-1a` thành công và ghi nhận chính xác mốc $T_{fault}$.
- [ ] Đo thời gian unhealthy, ghi health config và cross-zone attributes.
- [ ] Kết nối mới phục hồi qua node 1b; báo MTTR thực, số lỗi và ảnh hưởng phiên cũ, không ép dưới 25 giây.
- [ ] Khởi động lại node `1a` thành công; GWLB tự động khôi phục trạng thái `healthy` cho cả 2 targets.
