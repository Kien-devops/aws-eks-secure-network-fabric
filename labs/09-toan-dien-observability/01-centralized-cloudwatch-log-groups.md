# 09.01 — Khởi Tạo & Quản Trị Hệ Thống CloudWatch Log Groups Tập Trung

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Chuẩn hóa nơi lưu trữ nhật ký mạng tập trung cho toàn bộ các thành phần trong Project 6 tại Singapore (`ap-southeast-1`).

---

## 1. Mục Tiêu Kỹ Thuật

- Khởi tạo hệ thống **Amazon CloudWatch Log Groups** theo cấu trúc phân tầng rõ ràng:
  - VPC Flow Logs: `/aws/vpc/fabric-edge-flow`, `/aws/vpc/fabric-core-flow`, `/aws/vpc/fabric-inspection-flow`, `/aws/vpc/fabric-egress-flow`.
  - Transit Gateway Logs: `/aws/tgw/fabric-tgw-flow`.
  - Network Firewall: `/aws/network-firewall/fabric-egress-alerts`, `/aws/network-firewall/fabric-egress-flows`.
  - Suricata IDS/IPS: `/aws/suricata/fabric-inspection-eve`.
- Cấu hình vòng đời lưu trữ (**Retention Period: 7 Days**) để kiểm soát chi phí FinOps, tránh phát sinh chi phí lưu trữ log dài ngày không cần thiết.

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Mở Dịch Vụ CloudWatch Logs
1. Mở dịch vụ **Amazon CloudWatch** tại Region Singapore (`ap-southeast-1`).
2. Tại menu bên trái, nhấp vào nhóm **Logs** -> Chọn **Log groups**.

### Bước 2: Khởi Tạo Từng Log Group
1. Nhấp nút cam **Create log group**.
2. **Cấu hình Log Group 1:**
   - **Log group name:** `/aws/vpc/fabric-edge-flow`
   - **Retention setting:** Chọn `Expire events after` -> Chọn `7 days (1 week)`.
   - **Tags:** `Project` = `aws-eks-secure-network-fabric`, `Environment` = `dev`.
   - Nhấp **Create**.
3. Lặp lại tương tự cho:
   - `/aws/vpc/fabric-core-flow` (7 days)
   - `/aws/vpc/fabric-inspection-flow` (7 days)
   - `/aws/vpc/fabric-egress-flow` (7 days)
   - `/aws/tgw/fabric-tgw-flow` (7 days)
   - `/aws/network-firewall/fabric-egress-alerts` (7 days)
   - `/aws/network-firewall/fabric-egress-flows` (7 days)
   - `/aws/suricata/fabric-inspection-eve` (7 days)

---

## 3. Xác Minh (Verification)

Kiểm tra danh sách Log Groups qua AWS CLI:
```bash
aws logs describe-log-groups \
  --region ap-southeast-1 \
  --log-group-name-prefix "/aws/fabric-" \
  --query 'logGroups[*].{Name:logGroupName,RetentionDays:retentionInDays}' \
  --output table
```

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Toàn bộ 8 Log Groups được tạo thành công với đúng tên định danh.
- [ ] Thời gian lưu trữ (Retention) đều được cấu hình là 7 ngày.

