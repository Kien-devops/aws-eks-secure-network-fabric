# 10.03 — Đặc Tả GameDay Kịch Bản 3: Tắt Cưỡng Bức Máy Chủ Tường Lửa (Suricata Appliance Failover)

> **Mã bài lab:** `10.03`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/10-gameday/gameday-03-gwlb-failover-timeline.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả kịch bản diễn tập GameDay 10.03 tắt cưỡng bức một máy chủ tường lửa Suricata (`fabric-suricata-1b`) để đo lường độ trễ phát hiện sự cố (Detection Latency) của Gateway Load Balancer qua cổng HTTP 80 và kiểm chứng tính năng tự động chuyển vùng dự phòng (Cross-Zone Failover) sang node đối tác (`fabric-suricata-1a`).

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Vị Trí / Bảng Áp Dụng | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-suricata-1a` | `AWS::EC2::Instance` | Subnet `fabric-insp-fw-1a` | `i-089127472b112deff` (Node dự phòng tiếp nhận failover) |
| `fabric-suricata-1b` | `AWS::EC2::Instance` | Subnet `fabric-insp-fw-1b` | `i-091e84ae2b923eea2` (Node bị tiêm lỗi Stop) |
| `fabric-suricata-tg` | `AWS::ElasticLoadBalancingV2::TargetGroup` | Gateway Load Balancer TG | Health check: HTTP 80, Interval 10s |
| Evidence File | `Artifact::Evidence` | `evidence/10-gameday/` | `gameday-03-gwlb-failover-timeline.json` |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-*-gameday` | Tài nguyên diễn tập GameDay |
| `Project` | `aws-eks-secure-network-fabric` | Tài nguyên diễn tập GameDay |
| `Environment` | `prod` | Tài nguyên diễn tập GameDay |
| `ManagedBy` | `manual` | Quản trị kịch bản sự cố thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Thông Số Kỹ Thuật Failover Của GWLB Target Group

- **Health Check Protocol & Port:** `HTTP 80` (lắng nghe bởi `gwlbtun`).
- **Interval:** `10 seconds`, **Timeout:** `5 seconds`.
- **Healthy / Unhealthy Threshold:** `2` / `2` chu kỳ.
- **Cross-Zone Load Balancing:** Bắt buộc kích hoạt (`load_balancing.cross_zone.enabled: true`) trên `fabric-gwlb`.

### 4.2 Kịch Bản Diễn Tập & Đo Lường

1. Gửi luồng lưu lượng nền liên tục (~5 req/s) từ `edge-frontend` sang `core-service`.
2. Dừng cưỡng bức instance `fabric-suricata-1b` ($T_{fault} = \text{2026-11-07T22:02:56.989Z}$).
3. GWLB phát hiện unhealthy sau 2 chu kỳ thất bại ($T_{detect} = 32.1s$, lý do `Target.Timeout`).
4. GWLB tự động cô lập node 1b và điều hướng các kết nối mới sang `fabric-suricata-1a` tại AZ `1a`.
5. Bật lại máy chủ 1b và xác nhận trạng thái `healthy` tự phục hồi ($MTTR = 89.2s$).

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `05.01`, `05.02`: Hai máy chủ Suricata và GWLB Target Group đang `healthy`.
- Phụ thuộc vào `05.04`: Đường truyền East-West đang định tuyến qua GWLB.
- Phụ thuộc vào `04.04`: Microservices `edge-frontend` và `core-service` đang giao tiếp ổn định.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Phát Hiện Target Unhealthy** | `aws elbv2 describe-target-health --target-group-arn <TGArn>` | Node 1b chuyển sang `TargetHealth.State: unhealthy` (`Reason: Target.Timeout`). |
| **Lưu Lượng Không Gián Đoạn** | Quan sát HTTP Status trong quá trình diễn ra lỗi | Kết nối mới nhanh chóng phục hồi và trả về `HTTP 200` qua node 1a. |
| **Tự Động Phục Hồi (Auto Re-join)** | Khởi động lại instance 1b | Trạng thái tự động phục hồi về `healthy` sau 2 chu kỳ probe thành công. |
| **Chỉ Số Thực Tế** | Phân tích file `gameday-03-gwlb-failover-timeline.json` | $MTTD = 32.1s$, $MTTR = 89.2s$. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo tính toàn vẹn phiên (Session Drops):** GWLB không đồng bộ trạng thái TCP giữa 2 cụm Suricata độc lập. Các phiên TCP dài hạn đang chạy dở trên node 1b sẽ bị gián đoạn và phải tái thiết lập bắt tay 3 bước sang node 1a.
- **Quy trình Rollback:**
  ```bash
  # Khởi động lại máy chủ Suricata AZ-b (i-091e84ae2b923eea2)
  aws ec2 start-instances --region ap-southeast-1 --instance-ids i-091e84ae2b923eea2
  ```
