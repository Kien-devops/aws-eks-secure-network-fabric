# 11.02 — Kiểm Toán Vệ Sinh Dữ Liệu & Khử Trùng Thông Tin Nhạy Cảm (Sanitization Audit)

> **Mã bài lab:** `11.02`
> **Trạng thái:** `RUNTIME_PASS`
> **Thời gian dự kiến:** 30 phút
> **Chi phí ước tính:** $0.00 USD (Static Audit / Script Execution)
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)

---

## 1. Mục Tiêu (Objective)

Đặc tả quy chuẩn kiểm toán an toàn và khử trùng dữ liệu nhạy cảm (Sanitization Gate) trên toàn bộ tài liệu lab và tệp bằng chứng kỹ thuật. Đảm bảo che giấu 100% AWS Account ID thực tế (thay bằng `123456789012`), loại bỏ Access Keys, Private Keys, Bearer Tokens và mật khẩu trước khi lưu trữ hoặc xuất bản.

---

## 2. Tài Nguyên (Resources)

| Tên Resource / Tệp Kiểm Toán | Loại Resource | Phạm Vi Áp Dụng | Đường Dẫn Lưu Trữ |
| :--- | :--- | :--- | :--- |
| `sanitize-evidence.sh` | Bash Script | Máy trạm / CI Runner | `scripts/sanitize-evidence.sh` |
| `audit-sanitization.sh` | Bash Script (Gate) | Toàn bộ repository | `scripts/audit-sanitization.sh` |
| `SANITIZATION-AUDIT-REPORT.md` | Báo cáo Markdown | Thư mục báo cáo bằng chứng | `evidence/05-reports/SANITIZATION-AUDIT-REPORT.md` |
| `evidence/**` | Tập hợp tệp JSON/Log | Toàn bộ bằng chứng GameDay | `evidence/` |

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `audit-*` | Tiêu chuẩn định danh dự án |
| `Project` | `aws-eks-secure-network-fabric` | Tiêu chuẩn định danh dự án |
| `Environment` | `prod` | Phân vùng dữ liệu nghiệm thu |
| `ManagedBy` | `manual` | Quản lý quy trình kiểm toán thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Bộ Quy Tắc 5 Lớp Khử Trùng & Mẫu Regex (Sanitization Rules)

| Lớp Kiểm Tra | Mẫu Nhận Diện (Regex Pattern) | Quy Chuẩn Thay Thế / Xử Lý | Trạng Thái Bắt Buộc |
| :--- | :--- | :--- | :--- |
| **Lớp 1: AWS Access Keys** | `AKIA[0-9A-Z]{16}` | Cấm tuyệt đối (0 occurrences) | **BLOCKING / FAIL** |
| **Lớp 2: Private Keys** | `BEGIN (RSA\|OPENSSH\|EC) PRIVATE KEY` | Cấm tuyệt đối (0 occurrences) | **BLOCKING / FAIL** |
| **Lớp 3: Passwords & Secrets** | `(password\|secret_key)\s*=\s*["'][^"']+["']` | Sử dụng AWS Secrets Manager tham chiếu | **BLOCKING / FAIL** |
| **Lớp 4: JWT Bearer Tokens** | `Bearer ey[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+` | Cắt ngắn hoặc ẩn danh hóa bằng `Bearer ey***` | **BLOCKING / FAIL** |
| **Lớp 5: AWS Account ID** | `arn:aws:[a-z0-9-]+:[a-z0-9-]+:([0-9]{12}):` | Thay thế chuỗi 12 số bằng `123456789012` | **100% REPLACED** |

### 4.2 Lệnh Khử Trùng Hàng Loạt (Mass Sanitization)
```bash
# Thay thế Account ID thực tế bằng 123456789012
find evidence/ labs/ -type f \( -name "*.json" -o -name "*.log" -o -name "*.txt" -o -name "*.md" \) \
  -exec sed -i -E "s/arn:aws:([a-z0-9-]+):ap-southeast-1:[0-9]{12}:/arn:aws:\1:ap-southeast-1:123456789012:/g" {} +
```

---

## 5. Phụ Thuộc (Dependencies)

* [Lab 11.01](01-runtime-evidence-collection.md): Đã thu thập đầy đủ tệp telemetry và runtime evidence vào `evidence/`.
* Công cụ dòng lệnh: `grep`, `sed`, `jq`, `find`.

---

## 6. Kiểm Tra Đạt (Verification)

| Hạng Mục | Lệnh Kiểm Tra / Metric | Kỳ Vọng Đạt |
| :--- | :--- | :--- |
| **Zero Access Key Leak** | `grep -rE "AKIA[0-9A-Z]{16}" evidence/ labs/` | 0 kết quả trả về |
| **Zero Private Key Leak** | `grep -rE "BEGIN .* PRIVATE KEY" evidence/` | 0 kết quả trả về |
| **Zero Raw Account ID** | `grep -rE "arn:aws:[^:]*:[^:]*:[0-9]{12}:" evidence/ \| grep -v "123456789012"` | 0 kết quả trả về |
| **Báo Cáo Nghiệm Thu** | Kiểm tra tệp `SANITIZATION-AUDIT-REPORT.md` | Có chữ ký tuân thủ, mốc ISO 8601 UTC và kết quả 5/5 Lớp PASSED |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

> [!CAUTION]
> Thao tác `sed -i` ghi đè trực tiếp lên tệp. Phải sao lưu thư mục `evidence/` trước khi thực thi để tránh hỏng cú pháp JSON gốc.

### Quy Trình Sao Lưu & Phục Hồi
```bash
# Sao lưu trước khi khử trùng
cp -r evidence /tmp/evidence-backup-pre-sanitize

# Phục hồi khi có lỗi cú pháp
rm -rf evidence && cp -r /tmp/evidence-backup-pre-sanitize evidence
```
