# 07.02 — Đặc Tả AWS WAF v2 Web ACL & Các Nhóm Quy Tắc Bảo Vệ L7

> **Mã bài lab:** `07.02`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/07-waf/web-acl-definition.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả tài nguyên AWS WAF v2 Web ACL khu vực (`fabric-edge-web-acl`) tích hợp các nhóm quy tắc quản trị AWS Managed Rules và quy tắc giới hạn tần suất (Rate Limiting) nhằm bảo vệ lớp Ingress Application Load Balancer trước các mối đe dọa OWASP Top 10 và tấn công từ chối dịch vụ tầng ứng dụng L7.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Phạm Vi Áp Dụng | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-edge-web-acl` | `AWS::WAFv2::WebACL` | Regional (`ap-southeast-1`) | ID: `a010b9c0-edfa-4ba4-bfb0-8691ae8ecf56`<br>ARN: `arn:aws:wafv2:ap-southeast-1:123456789012:regional/webacl/fabric-edge-web-acl/a010b9c0-edfa-4ba4-bfb0-8691ae8ecf56` |
| `fabric-rate-limit-rule` | `AWS::WAFv2::Rule` (Rate-based) | `fabric-edge-web-acl` (Priority 0) | Giới hạn 500 requests / 5 phút per Source IP |
| `AWS-AWSManagedRulesCommonRuleSet` | `AWS::WAFv2::ManagedRuleGroup` | `fabric-edge-web-acl` (Priority 1) | Chống OWASP Top 10, SQLi, XSS baseline |
| `AWS-AWSManagedRulesKnownBadInputsRuleSet` | `AWS::WAFv2::ManagedRuleGroup` | `fabric-edge-web-acl` (Priority 2) | Ngăn chặn payload khai thác lỗ hổng và shell injection |
| `AWS-AWSManagedRulesAmazonIpReputationList` | `AWS::WAFv2::ManagedRuleGroup` | `fabric-edge-web-acl` (Priority 3) | Chặn địa chỉ IP thuộc danh sách botnet/threat intelligence |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-edge-web-acl` | AWS WAF Web ACL |
| `Project` | `aws-eks-secure-network-fabric` | AWS WAF Web ACL |
| `Environment` | `prod` | AWS WAF Web ACL |
| `ManagedBy` | `manual` | Quản trị chính sách tường lửa ứng dụng thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Thuộc Tính Web ACL

- **Scope:** `REGIONAL` (`ap-southeast-1`).
- **Default Action:** `Allow` (Toàn bộ traffic bình thường được cho phép; chỉ can thiệp khi vi phạm quy tắc).
- **Association Target:** Gắn trực tiếp vào Ingress ALB `fabric-edge-public-alb` tại bài lab `07.03`.

### 4.2 Thứ Tự Ưu Tiên & Trạng Thái Quy Tắc (Rule Order & Mode)

| Thứ Tự (Priority) | Tên Quy Tắc / Nhóm Quy Tắc | Loại Quy Tắc | Cấu Hình Kỹ Thuật | Action Ban Đầu (Lab 07.02) | Action Cắt Chuyển (Lab 07.04) |
| :---: | :--- | :--- | :--- | :---: | :---: |
| **0** | `fabric-rate-limit-rule` | Rate-based | 500 requests / 5 phút per Source IP | `Count` | `Block` (HTTP 429) |
| **1** | `AWSManagedRulesCommonRuleSet` | Managed Rule Group | CRS baseline rules | `Count` | `Block` (HTTP 403) |
| **2** | `AWSManagedRulesKnownBadInputsRuleSet` | Managed Rule Group | Kiểm tra input, log4j, traversal | `Count` | `Block` (HTTP 403) |
| **3** | `AWSManagedRulesAmazonIpReputationList` | Managed Rule Group | IP reputation list từ Amazon Threat Intel | `Count` | `Block` (HTTP 403) |

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `07.01`: Chứng chỉ SSL/TLS đã cấp phát thành công.
- Là điều kiện tiên quyết bắt buộc trước khi liên kết với Application Load Balancer tại `07.03` và kích hoạt chế độ chặn thực tế tại `07.04`.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng thái Web ACL** | `aws wafv2 get-web-acl --name fabric-edge-web-acl --scope REGIONAL --id a010b9c0-edfa-4ba4-bfb0-8691ae8ecf56` | Trả về thông tin Web ACL hợp lệ với 4 rules. |
| **Số lượng Rules** | Kiểm tra mảng `Rules` trong phản hồi API | Đúng 4 rules với priority 0, 1, 2, 3. |
| **Đo lường Runtime (Traffic Overview)** | Quan sát AWS WAF Console Dashboard | Ghi nhận tổng cộng 407 requests đã được phân tích (385 allowed, 22 blocked, 0 captcha/challenge). |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Chiến lược Count-first:** Tuyệt đối không bật chế độ `Block` ngay khi khởi tạo Web ACL mà phải để ở chế độ `Count` nhằm quan sát lưu lượng, thu thập telemetry và loại bỏ false-positives trước khi cắt chuyển ở lab 07.04.
- **Quy trình Rollback:**
  ```bash
  # Lấy LockToken và xóa Web ACL
  WAF_ID="a010b9c0-edfa-4ba4-bfb0-8691ae8ecf56"
  LOCK_TOKEN=$(aws wafv2 get-web-acl --name "fabric-edge-web-acl" --scope REGIONAL --region ap-southeast-1 --id "$WAF_ID" --query 'LockToken' --output text)
  aws wafv2 delete-web-acl --name "fabric-edge-web-acl" --scope REGIONAL --region ap-southeast-1 --id "$WAF_ID" --lock-token "$LOCK_TOKEN"
  ```
