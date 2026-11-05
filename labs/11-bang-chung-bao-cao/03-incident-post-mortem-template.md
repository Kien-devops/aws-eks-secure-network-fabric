# 11.03 — Mẫu Báo Cáo Phân Tích Sự Cố Sau Diễn Tập (Incident Post-Mortem Report)

> **Mã bài lab:** `11.03`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 35 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã thực hiện ít nhất một kịch bản diễn tập sự cố mạng có chủ đích trong [Module 10](../10-gameday-su-co-mang/01-gameday-route-leak-test.md) (ví dụ: Kịch bản 10.02 — Lỗi định tuyến bất đối xứng hoặc 10.03 — Sập máy chủ Suricata).
- Đã thu thập đầy đủ mốc thời gian ($T_{fault}, T_{detect}, T_{mitigate}, T_{recover}$) từ CloudWatch Logs Insights.
- Hiểu rõ văn hóa hậu kiểm không đổ lỗi (**Blameless Post-Mortem Culture**) theo tiêu chuẩn Google SRE.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để tra cứu dữ liệu lịch sử sự cố và nhật ký cảnh báo:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:StartQuery",
        "logs:GetQueryResults",
        "cloudwatch:GetMetricData",
        "cloudwatch:DescribeAlarms"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD.
- **Văn Hóa SRE Blameless:** Bản phân tích sự cố tuyệt đối không nhằm mục đích quy kết trách nhiệm cá nhân, mà tập trung 100% vào các lỗ hổng quy trình, kiến trúc mạng, cơ chế tự động hóa bảo vệ, và giải pháp kỹ thuật phòng ngừa sự cố lặp lại trong tương lai.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Tái Hiện Dòng Thời Gian Chính Xác Trên CloudWatch Logs Insights
1. Đăng nhập vào **AWS Management Console** -> Chọn Region Singapore (`ap-southeast-1`).
2. Mở dịch vụ **CloudWatch** -> Tại menu bên trái chọn **Logs Insights**.
3. Chọn Log Group: `/aws/vpc/fabric-inspection-flow` và `/aws/suricata/fabric-inspection-eve`.
4. Thiết lập khung thời gian bao trùm thời điểm diễn ra GameDay 10.02 (ví dụ: 1 giờ vừa qua).
5. Chạy query truy vấn các sự kiện drop và bất thường:
   ```sql
   fields @timestamp, srcAddr, dstAddr, action, logStream
   | filter action = "REJECT" or event_type = "alert"
   | sort @timestamp asc
   | limit 50
   ```
6. Ghi nhận chính xác 4 mốc thời gian UTC:
   - **$T_{fault}$ (Thời điểm tiêm lỗi):** Ví dụ `2026-11-05T08:00:00Z`
   - **$T_{detect}$ (Thời điểm phát hiện cảnh báo đầu tiên):** Ví dụ `2026-11-05T08:01:45Z`
   - **$T_{mitigate}$ (Thời điểm áp dụng biện pháp khắc phục):** Ví dụ `2026-11-05T08:03:15Z`
   - **$T_{recover}$ (Thời điểm lưu lượng ổn định 100%):** Ví dụ `2026-11-05T08:04:00Z`

---

### Bước 2: Trích Xuất Dữ Liệu Tác Động Nghiệp Vụ (Impact Analysis)
1. Mở **CloudWatch Metrics**:
   - Chọn namespace `AWS/ApplicationELB` hoặc `AWS/NetworkELB`.
   - Xem biểu đồ `UnHealthyHostCount` và `TargetResponseTime`.
2. Ghi nhận số liệu:
   - Tổng số requests kiểm thử gửi đi trong thời gian sự cố: 200 requests.
   - Số requests bị lỗi (Timeout / Drop): 98 requests (~49% packet drop).
   - Thời gian gián đoạn dịch vụ: 4 phút.
   - Chỉ số **MTTD (Mean Time to Detect)**: 1 phút 45 giây.
   - Chỉ số **MTTR (Mean Time to Remediate)**: 2 phút 15 giây.

---

### Bước 3: Thực Hiện Phân Tích 5 Lần Tại Sao (5 Whys Root Cause Analysis)
Trả lời tuần tự 5 câu hỏi kỹ thuật chuyên sâu:
1. *Tại sao ứng dụng Frontend không nhận được phản hồi từ Order backend?*
   -> Do các gói tin phản hồi TCP SYN-ACK từ Backend bị ngắt kết nối.
2. *Tại sao gói tin phản hồi TCP SYN-ACK bị ngắt kết nối?*
   -> Do thiết bị tường lửa Suricata tại AZ-b drop gói tin và không chuyển tiếp qua GWLB.
3. *Tại sao Suricata AZ-b lại drop gói tin TCP SYN-ACK?*
   -> Do Suricata AZ-b không tìm thấy trạng thái phiên (TCP state table) của gói `SYN` trước đó (lỗi TCP Out-of-State).
4. *Tại sao gói SYN lại ở AZ-a trong khi gói SYN-ACK lại bị đẩy sang AZ-b?*
   -> Do Transit Gateway băm dòng gói tin độc lập theo 5-tuple trên chiều về, điều hướng sang ENI của Inspection VPC ở Availability Zone khác.
5. *Tại sao Transit Gateway không giữ tính đối xứng trên cùng một AZ?*
   -> Do thuộc tính `ApplianceModeSupport` trên TGW VPC Attachment của Inspection VPC bị tắt (`disable`), làm mất tính năng đối xứng AZ cưỡng bức.

---

### Bước 4: Soạn Thảo Báo Cáo Sự Cố Hoàn Chỉnh (Post-Mortem Document)
Biên soạn và lưu file báo cáo vào đường dẫn `evidence/05-reports/INCIDENT-POST-MORTEM-ASLR.md`:

```markdown
# BÁO CÁO PHÂN TÍCH SỰ CỐ MẠNG: ĐỊNH TUYẾN BẤT ĐỐI XỨNG (ASYMMETRIC ROUTING)

- **Mã sự cố (Incident ID):** `INC-FABRIC-2026-001`
- **Mức độ nghiêm trọng (Severity):** `P1 - High Availability Impact`
- **Thời gian bắt đầu (Start Time):** `2026-11-05T08:00:00Z`
- **Thời gian phục hồi (End Time):** `2026-11-05T08:04:00Z`
- **Chỉ số SRE:**
  - MTTD (Thời gian phát hiện): 1 phút 45 giây
  - MTTR (Thời gian khôi phục hoàn toàn): 4 phút 00 giây
- **Người chủ trì điều tra:** Principal Network Architect & SRE Lead
- **Hệ thống bị ảnh hưởng:** Toàn bộ giao tiếp East-West giữa Edge EKS và Core EKS qua Transit Gateway.

---

## 1. Tóm Tắt Tác Động (Executive Summary)
Trong phiên diễn tập GameDay có kiểm soát tại Singapore (`ap-southeast-1`), một lỗi cấu hình đã được mô phỏng: tính năng **Appliance Mode Support** trên TGW Inspection Attachment bị vô hiệu hóa. Sự cố làm phá vỡ tính đối xứng luồng lưu lượng (Flow Symmetry), khiến 49% các kết nối TCP giữa Frontend Pod và Order Service bị drop ngắt quãng do thiết bị kiểm tra an ninh Stateful Suricata drop các gói tin không có trạng thái phiên. Sự cố được phát hiện trong 1m45s và khắc phục triệt để trong 4m00s bằng việc bật lại Appliance Mode.

---

## 2. Dòng Thời Gian Chi Tiết (Detailed Timeline)

| Thời Gian (UTC) | Sự Kiện Kỹ Thuật | Người / Hệ Thống |
|---|---|---|
| **08:00:00Z** | Tiêm lỗi: Vô hiệu hóa `ApplianceModeSupport` trên Inspection TGW Attachment. | Chaos Engineer |
| **08:00:45Z** | k6 load test bắt đầu ghi nhận các lỗi kết nối timeout xuất hiện rải rác. | Giám sát k6 |
| **08:01:45Z** | Kỹ sư SRE phát hiện tỷ lệ lỗi tăng vọt lên ~50% trên biểu đồ CloudWatch Logs Insights. | SRE On-call |
| **08:02:30Z** | Mở `tcpdump` trên 2 máy chủ Suricata: Phát hiện node 1a chỉ có SYN, node 1b chỉ có SYN-ACK. | Network Engineer |
| **08:03:15Z** | Kích hoạt lại `ApplianceModeSupport = enable` trên TGW Attachment qua AWS Console. | SRE On-call |
| **08:04:00Z** | TGW Attachment chuyển trạng thái `available`. Lưu lượng phục hồi 100% thành công (HTTP 200). | Toàn hệ thống |

---

## 3. Phân Tích Nguyên Nhân Gốc Rễ (5 Whys Root Cause Analysis)
1. **Tại sao kết nối bị timeout?** -> Suricata drop gói tin phản hồi TCP SYN-ACK.
2. **Tại sao Suricata drop gói tin?** -> Gói tin đến node AZ-b mà không có bản ghi phiên ban đầu (Out-of-State).
3. **Tại sao gói tin chiều về lại rơi vào node AZ-b?** -> TGW phân phối gói tin độc lập giữa 2 AZ trên hai chiều giao tiếp.
4. **Tại sao TGW không giữ cố định AZ cho cùng một phiên TCP?** -> Thuộc tính `ApplianceModeSupport` bị tắt.
5. **Biện pháp ngăn ngừa căn bản là gì?** -> Ép buộc cấu hình `appliance_mode_support = "enable"` trong mã nguồn Terraform và triển khai Open Policy Agent (OPA) / Checkov rule ngăn chặn hành vi tắt cờ này.

---

## 4. Bài Học Rút Ra (Lessons Learned)
- **Điểm làm tốt:** Khả năng quan sát (Observability) qua CloudWatch Logs Insights giúp khoanh vùng lỗi trong dưới 2 phút; các lệnh tcpdump trên Suricata chứng minh nhanh chóng hiện tượng mất đối xứng gói tin.
- **Điểm cần cải thiện:** Cần có CloudWatch Metric Filter tự động kích hoạt Alarm gửi thông báo Slack/PagerDuty ngay khi tỷ lệ lỗi TCP RST/Timeout vượt quá 5% trong 1 phút.
- **Yếu tố may mắn:** Sự cố diễn ra trên môi trường GameDay có kịch bản trước, không gây thiệt hại cho người dùng cuối.

---

## 5. Danh Mục Hành Động Khắc Phục (Action Items)

| Mã Công Việc | Mô Tả Hành Động | Người Phụ Trách | Ưu Tiên | Hạn Chót | Trạng Thái |
|---|---|---|---|---|---|
| **ACT-01** | Khóa cứng `appliance_mode_support = "enable"` trong Terraform Module TGW. | DevOps Lead | P0 | 24h | **DONE** |
| **ACT-02** | Xây dựng Checkov custom policy chặn PR nếu `appliance_mode_support` khác `enable`. | SecOps | P1 | 48h | **DONE** |
| **ACT-03** | Tạo CloudWatch Alarm giám sát tỷ lệ Out-of-State Drops từ Suricata EVE logs. | SRE Team | P1 | 3 ngày | **IN PROGRESS** |
```

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra sự tồn tại và định dạng của tệp báo cáo Post-Mortem:

```bash
ls -la evidence/05-reports/INCIDENT-POST-MORTEM-ASLR.md

# Kiểm tra các mục chính trong báo cáo
grep -E "^## " evidence/05-reports/INCIDENT-POST-MORTEM-ASLR.md
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Tệp báo cáo Post-Mortem là tài liệu phân tích kỹ thuật tĩnh, không can thiệp vào hạ tầng runtime. Có thể chỉnh sửa hoặc bổ sung số liệu bất kỳ lúc nào qua lệnh soạn thảo Markdown chuẩn.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

- `evidence/05-reports/INCIDENT-POST-MORTEM-ASLR.md`: Báo cáo Post-Mortem hoàn chỉnh theo chuẩn SRE.

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Báo cáo ghi nhận đầy đủ 4 mốc thời gian UTC thực tế ($T_{fault}, T_{detect}, T_{mitigate}, T_{recover}$).
- [ ] Tính toán chính xác các chỉ số MTTD và MTTR.
- [ ] Áp dụng phương pháp 5 Whys phân tích triệt để tới tận bản chất TGW Appliance Mode.
- [ ] Bảng phân công Action Items có người phụ trách, thời hạn và trạng thái rõ ràng.
- [ ] Báo cáo tuân thủ nguyên tắc Blameless Post-Mortem.
