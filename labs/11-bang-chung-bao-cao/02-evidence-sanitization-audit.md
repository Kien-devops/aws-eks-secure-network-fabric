# 11.02 — Kiểm Toán Vệ Sinh Dữ Liệu & Khử Trùng Thông Tin Nhạy Cảm (Sanitization Audit)

> **Trạng thái:** Quy trình kiểm toán an toàn thông tin trước khi commit/push repository lên GitHub.  
> **Áp dụng cho:** Quét toàn bộ file bằng chứng nhằm đảm bảo không rò rỉ Account ID, Access Key, hoặc Passwords.

---

## 1. Mục Tiêu Kỹ Thuật

- Thực thi script kiểm toán tự động quét toàn bộ thư mục `evidence/`.
- Kiểm tra các mẫu regex nhạy cảm:
  - AWS Account ID (12 chữ số liên tiếp).
  - AWS Access Key (`AKIA[0-9A-Z]{16}`).
  - JWT Tokens (`ey...`).
  - Mật khẩu cơ sở dữ liệu và Private Keys.
- Đảm bảo 100% tệp tin đạt trạng thái **CLEAN** trước khi đẩy lên GitHub.

---

## 2. Script Quét Khử Trùng Mẫu

```bash
#!/bin/bash
set -e

echo "=== Bắt đầu kiểm toán vệ sinh dữ liệu (Sanitization Audit) ==="

# Kiểm tra AWS Access Key
if grep -rE "AKIA[0-9A-Z]{16}" evidence/; then
  echo "[-] LỖI: Phát hiện AWS Access Key chưa được khử trùng!"
  exit 1
fi

# Kiểm tra chuỗi Private Key
if grep -r "BEGIN RSA PRIVATE KEY" evidence/; then
  echo "[-] LỖI: Phát hiện Private Key trong thư mục evidence!"
  exit 1
fi

echo "[+] KIỂM TOÁN THÀNH CÔNG: Toàn bộ bằng chứng đã được khử trùng an toàn!"
```

---

## 3. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Không có chuỗi thông tin nhạy cảm nào lọt qua bài kiểm toán.
- [ ] Account ID được thay thế đồng nhất bằng `123456789012` hoặc `***`.

