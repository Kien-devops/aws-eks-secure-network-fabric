# 07.02 — Khởi Tạo AWS WAF v2 Web ACL & Các Nhóm Quy Tắc Bảo Vệ L7

> **Mã bài lab:** `07.02`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** ~$5.00 USD / tháng (Phí duy trì Web ACL và Rules WAFv2)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn tất cấu hình chứng chỉ bảo mật ACM tại [Lab 07.01](01-acm-public-tls-certificate.md).
- Có quyền quản trị AWS WAFv2 trên Region Singapore (`ap-southeast-1`).
- Đang mở phiên AWS Management Console.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để khởi tạo và cấu hình Web ACL:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "wafv2:CreateWebACL",
        "wafv2:GetWebACL",
        "wafv2:UpdateWebACL",
        "wafv2:DeleteWebACL",
        "wafv2:ListWebACLs",
        "wafv2:TagResource"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** AWS WAF tính phí $5.00/tháng cho mỗi Web ACL và $1.00/tháng cho mỗi Rule; kèm $0.60 per 1M requests.
- **Chiến lược Count-first an toàn:** Toàn bộ Managed Rules và Rate Limit Rules được khởi tạo ở chế độ **Count Mode** (Đếm) để quan sát baseline lưu lượng và tránh false-positive trước khi kích hoạt Block ở bài [07.04](04-waf-count-to-block-transition.md).

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Mở Bảng Điều Khiển AWS WAF & Shield
1. Trên thanh tìm kiếm Console, nhập `WAF` -> Chọn **AWS WAF & Shield**.
2. Tại menu bên trái, nhấp chọn **Web ACLs**.
3. Xác nhận bộ chọn Region đang ở **Asia Pacific (Singapore) `ap-southeast-1`**.
4. Nhấp nút màu cam **Create web ACL**.

---

### Bước 2: Cấu Hình Web ACL Cơ Bản
1. **Name:** `fabric-edge-web-acl`
2. **Description:** `L7 Web Application Firewall protecting public Ingress ALB in Singapore`
3. **Resource type:** Chọn radio button **`Regional resources (Application Load Balancer, API Gateway, AWS AppSync, AWS Cognito)`**
4. **Region:** Chọn `Asia Pacific (Singapore) ap-southeast-1`.
5. **Associated AWS resources:** Tạm thời để trống (sẽ gắn ở bước sau).
6. Nhấp **Next**.

---

### Bước 3: Thêm Các Nhóm Quy Tắc AWS Managed Rules (Count Mode)
1. Nhấp nút **Add rules** -> Chọn **Add managed rule groups**.
2. Mở rộng danh mục **AWS managed rule groups**:
   - **Nhóm 1 — `Core rule set` (`AWSManagedRulesCommonRuleSet`):**
     - Bật công tắc gạt **Add to web ACL**.
     - Bật tùy chọn checkbox: **`Set all rule actions to count`** (chế độ đếm an toàn).
   - **Nhóm 2 — `Known bad inputs` (`AWSManagedRulesKnownBadInputsRuleSet`):**
     - Bật công tắc gạt **Add to web ACL**.
     - Bật tùy chọn checkbox: **`Set all rule actions to count`**.
   - **Nhóm 3 — `Amazon IP reputation list` (`AWSManagedRulesAmazonIpReputationList`):**
     - Bật công tắc gạt **Add to web ACL**.
     - Bật tùy chọn checkbox: **`Set all rule actions to count`**.
3. Nhấp nút cam **Add rules** ở góc dưới.

---

### Bước 4: Thêm Quy Tắc Tự Định Nghĩa Giới Hạn Tần Suất (Rate Limiting)
1. Nhấp tiếp **Add rules** -> Chọn **Add my own rules and rule groups**.
2. **Cấu hình Rule:**
   - **Rule type:** Chọn **Rule builder**.
   - **Name:** `fabric-rate-limit-rule`.
   - **Type:** Chọn **Rate-based rule**.
   - **Rate limit:** Nhập `500` (requests trên 5 phút).
   - **Evaluation window:** Chọn `5 minutes`.
   - **Rate limiting criteria:** Chọn `Source IP address`.
   - **Scope of inspection:** Chọn `Consider all requests`.
   - **Action:** Chọn **`Count`** (Quan sát tần suất trước khi chặn).
3. Nhấp **Add rule**.

---

### Bước 5: Cấu Hình Thứ Tự Ưu Tiên & Nhật Ký
1. Tại bước **Set rule priority**:
   - Đảm bảo thứ tự ưu tiên:
     1. `fabric-rate-limit-rule` (Priority 0)
     2. `AWS-AWSManagedRulesCommonRuleSet` (Priority 1)
     3. `AWS-AWSManagedRulesKnownBadInputsRuleSet` (Priority 2)
     4. `AWS-AWSManagedRulesAmazonIpReputationList` (Priority 3)
   - Nhấp **Next**.
2. Tại bước **Configure metrics**:
   - Để nguyên CloudWatch metric name mặc định.
   - Nhấp **Next**.
3. Kiểm tra lại toàn bộ cấu hình tại bước **Review and create web ACL** -> Nhấp **Create web ACL**.
4. Ghi lại chuỗi **ARN** của Web ACL để sử dụng cho các bài lab tiếp theo.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra Web ACL vừa tạo qua AWS CLI:

```bash
aws wafv2 list-web-acls \
  --scope REGIONAL \
  --region ap-southeast-1 \
  --query 'WebACLs[?contains(Name, `fabric`)].{Name:Name,Id:Id,ARN:ARN}' \
  --output table

aws wafv2 get-web-acl \
  --name "fabric-edge-web-acl" \
  --scope REGIONAL \
  --region ap-southeast-1 \
  --id $(aws wafv2 list-web-acls --scope REGIONAL --region ap-southeast-1 --query 'WebACLs[?Name==`fabric-edge-web-acl`].Id' --output text) \
  --query 'WebACL.{Name:Name,RulesCount:length(Rules),DefaultAction:DefaultAction}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Khi cần xóa Web ACL:
```bash
WAF_ID=$(aws wafv2 list-web-acls --scope REGIONAL --region ap-southeast-1 --query 'WebACLs[?Name==`fabric-edge-web-acl`].Id' --output text)
LOCK_TOKEN=$(aws wafv2 get-web-acl --name "fabric-edge-web-acl" --scope REGIONAL --region ap-southeast-1 --id "$WAF_ID" --query 'LockToken' --output text)

[ -n "$WAF_ID" ] && aws wafv2 delete-web-acl \
  --name "fabric-edge-web-acl" \
  --scope REGIONAL \
  --region ap-southeast-1 \
  --id "$WAF_ID" \
  --lock-token "$LOCK_TOKEN"
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

- `evidence/07-waf/web-acl-definition.json`: Cấu hình Web ACL chi tiết.
- `evidence/07-waf/web-acl-rules-count-mode.json`: Danh sách rules và trạng thái Count mode.

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Web ACL `fabric-edge-web-acl` được tạo thành công tại Region Singapore (`ap-southeast-1`).
- [ ] 3 AWS Managed Rule Groups (`CommonRuleSet`, `KnownBadInputs`, `IpReputationList`) được thêm đầy đủ.
- [ ] Quy tắc Rate Limiting `fabric-rate-limit-rule` giới hạn 500 req/5m được kích hoạt.
- [ ] Toàn bộ 4 quy tắc đang ở trạng thái `Count` an toàn.
