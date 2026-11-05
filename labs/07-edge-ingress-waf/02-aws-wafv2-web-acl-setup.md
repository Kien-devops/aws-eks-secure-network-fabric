# 07.02 — Khởi Tạo AWS WAF v2 Web ACL & Các Nhóm Quy Tắc Bảo Vệ L7

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Cấu hình tường lửa ứng dụng web L7 bảo vệ cổng vào Ingress khỏi các cuộc tấn công OWASP Top 10 và DDoS L7.

---

## 1. Mục Tiêu Kỹ Thuật

- Khởi tạo **AWS WAF v2 Web ACL** ở phạm vi khu vực (**Regional**) tại Region Singapore (`ap-southeast-1`).
- Kích hoạt 3 nhóm quy tắc quản lý sẵn có của AWS (AWS Managed Rule Groups):
  1. `AWSManagedRulesCommonRuleSet` (Chống SQL Injection, XSS, Path Traversal...).
  2. `AWSManagedRulesKnownBadInputsRuleSet` (Chặn các input độc hại đã biết như Log4j, Shellshock...).
  3. `AWSManagedRulesAmazonIpReputationList` (Chặn các IP botnet, proxy độc hại từ mạng tình báo của Amazon).
- Thiết lập quy tắc tự định nghĩa giới hạn tần suất truy cập (**Rate Limiting Rule**): Tối đa 500 requests / 5 phút trên từng địa chỉ IP nguồn.
- Cấu hình trạng thái ban đầu ở chế độ **Đếm (Count Mode)** để quan sát hành vi trước khi chuyển sang chế độ Chặn (Block).

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Mở Bảng Điều Khiển AWS WAF & Shield
1. Trên thanh tìm kiếm Console, nhập **WAF** -> Chọn **AWS WAF & Shield**.
2. Chọn **Web ACLs** ở menu bên trái.
3. Chắc chắn bộ chọn Region đang ở **Asia Pacific (Singapore) `ap-southeast-1`** -> Nhấp **Create web ACL**.

---

### Bước 2: Cấu Hình Web ACL Cơ Bản
1. **Name:** `fabric-edge-web-acl`.
2. **Resource type:** Chọn `Regional resources (Application Load Balancer, API Gateway...)`.
3. **Region:** `ap-southeast-1`.
4. Nhấp **Next**.

---

### Bước 3: Thêm Các Nhóm Quy Tắc (Rules)
1. Nhấp **Add rules** -> Chọn **Add managed rule groups**:
   - Mở nhóm **AWS managed rule groups**:
     - Tìm `Core rule set` -> Bật công tắc `Add to web ACL` -> Bật tùy chọn **Set all rule actions to count** (để chạy chế độ Count trước).
     - Tìm `Known bad inputs` -> Bật công tắc `Add to web ACL` -> Bật tùy chọn **Set all rule actions to count**.
     - Tìm `Amazon IP reputation list` -> Bật công tắc `Add to web ACL` -> Bật tùy chọn **Set all rule actions to count**.
   - Nhấp **Add rules**.
2. Nhấp **Add rules** lần 2 -> Chọn **Add my own rules and rule groups**:
   - **Rule type:** Chọn **Rule builder**.
   - **Name:** `fabric-rate-limit-rule`.
   - **Type:** Chọn **Rate-based rule**.
   - **Rate limit:** Nhập `500`.
   - **Evaluation window:** `5 minutes`.
   - **Action:** Chọn **Count** (tạm thời để đếm).
   - Nhấp **Add rule**.
3. **Default web ACL action:** Chọn **Allow** (Cho phép các request không vi phạm đi qua).
4. Nhấp **Next** -> Nhấp **Next** -> Nhấp nút cam **Create web ACL**.

---

## 3. Xác Minh (Verification)

Kiểm tra Web ACL qua AWS CLI:
```bash
aws wafv2 list-web-acls \
  --scope REGIONAL \
  --region ap-southeast-1 \
  --query 'WebACLs[?Name==`fabric-edge-web-acl`].{Name:Name,Id:Id,Arn:ARN}' \
  --output table
```
Ghi lại chuỗi **ARN** của Web ACL để liên kết với ALB ở bài sau.

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Web ACL `fabric-edge-web-acl` được tạo thành công với 4 quy tắc an ninh.
- [ ] Toàn bộ các rule đang ở chế độ `Count` an toàn, sẵn sàng liên kết với Ingress.
