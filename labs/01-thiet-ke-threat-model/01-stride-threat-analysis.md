# 01.01 — Phân Tích Mô Hình Đe Dọa STRIDE Cho Hạ Tầng Mạng & EKS

> **Mã bài lab:** `01.01`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 30 phút  
> **Chi phí ước tính:** $0.00 USD (Thiết kế kiến trúc & phân tích rủi ro an ninh)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành toàn bộ các bài lab thuộc [Module 00: Chuẩn Bị & Inventory](../00-chuan-bi-inventory/README.md).
- Hiểu rõ sơ đồ kiến trúc tổng thể 4 VPC (Edge, Core, Inspection, Egress) theo [spec.md](../../spec.md).
- Đăng nhập vào AWS Console tại Singapore (`ap-southeast-1`).

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để rà soát bề mặt an ninh và dịch vụ phân tích trên AWS Console:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:GetAccountSummary",
        "access-analyzer:ListAnalyzers",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeNetworkAcls",
        "ec2:DescribeRouteTables"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD. Thao tác thiết kế và rà soát bề mặt tấn công không phát sinh chi phí.
- **Cảnh báo an ninh:** Các biện pháp kiểm soát an ninh (Controls) được xác định trong bài lab này là yêu cầu bắt buộc phải được hiện thực hóa trong các module tiếp theo (NACL, SG, NetworkPolicy, Suricata, Network Firewall, AWS WAF). Bất kỳ khoảng trống (gap) nào chưa có biện pháp kiểm soát sẽ tạo rủi ro nghiêm trọng khi đưa vào môi trường Production.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Rà Soát Bề Mặt Tấn Công & 5 Ranh Giới Tin Cậy (Trust Boundaries)
Mở tài liệu kiến trúc và đối chiếu các ranh giới kết nối trên AWS Console:
1. **Ranh giới Ingress (Internet <-> Edge EKS VPC):**
   - Bề mặt tấn công: ALB công khai nhận lưu lượng HTTP/HTTPS cổng 80/443.
   - Nguy cơ: Tấn công DDoS L7, SQL Injection, Cross-Site Scripting (XSS), quét dò cổng trái phép.
   - Kiểm soát: AWS WAF v2 gắn trên ALB (Count-to-Block), Security Group chỉ mở 80/443 từ Internet.
2. **Ranh giới Đông - Tây (Edge EKS <-> Core EKS East-West):**
   - Bề mặt tấn công: Lưu lượng gọi nội bộ từ `frontend` sang `order-service` / `inventory-service`.
   - Nguy cơ: Kẻ tấn công chiếm được Pod frontend tại Edge và cố gắng thực hiện di chuyển ngang (Lateral Movement) tấn công tầng dữ liệu lõi hoặc khai thác lỗ hổng deserialization/RCE.
   - Kiểm soát: Bắt buộc đi qua Transit Gateway -> Inspection VPC (GWLB + Cụm Suricata EC2 IDS/IPS giải mã GENEVE UDP 6081) -> Kiểm duyệt verdict -> Core EKS.
3. **Ranh giới Thoát Ra Ngoài (Core EKS <-> Centralized Egress):**
   - Bề mặt tấn công: Pod trong Core EKS gửi yêu cầu ra ngoài Internet để tải dependency hoặc gọi webhook đối tác.
   - Nguy cơ: Mã độc cài cắm exfiltration đánh cắp dữ liệu thẻ/PII ra C2 Server bên ngoài thông qua DNS tunneling hoặc cổng TCP lạ.
   - Kiểm soát: Bắt buộc định tuyến qua Centralized Egress VPC -> AWS Network Firewall (Domain Filtering TLS SNI allowlist `.quay.io`, `.github.com`, `.amazonaws.com`).
4. **Ranh giới Trung Tâm (VPC <-> Transit Gateway):**
   - Bề mặt tấn công: Rò rỉ định tuyến (Route Leak) giữa các VPC phân vùng khác nhau.
   - Nguy cơ: Dev VPC hoặc đối tác bên ngoài nhảy cóc truy cập trực tiếp vào Core VPC DB Subnet mà không qua Inspection.
   - Kiểm soát: Phân đoạn logic 4 bảng TGW Route Tables riêng biệt, tắt `Default Association` và `Default Propagation`.
5. **Ranh giới Vi Mô Trong Cụm (Pod <-> Pod Intra-cluster):**
   - Bề mặt tấn công: Giao tiếp giữa các namespace và pods trong cùng một nút EKS.
   - Nguy cơ: Pod frontend gọi trực tiếp Pod payment mà không qua cơ chế xác thực.
   - Kiểm soát: EKS NetworkPolicy với chính sách `default-deny-all`, chỉ mở ingress/egress cụ thể qua nhãn `app.kubernetes.io/name`.

### Bước 2: Thiết Lập Ma Trận Đe Dọa STRIDE Đầy Đủ

| Danh mục STRIDE | Nguy cơ cụ thể trên kiến trúc Fabric | Biện pháp kiểm soát mạng tương ứng (Mitigation) | Vị trí hiện thực |
|---|---|---|---|
| **Spoofing** (Giả mạo) | Giả mạo IP nguồn từ VPC khác hoặc Pod lạ để vượt qua firewall | VPC Source/Dest Check, AWS VPC CNI strict ENI binding, K8s NetworkPolicy | Module 02, Module 03 |
| **Tampering** (Can thiệp) | Bắt trộm gói tin truyền giữa Edge và Core, can thiệp payload HTTP | Bắt buộc mTLS L7 nội bộ, mã hóa KMS Secrets, chuyển tiếp toàn bộ qua GWLB | Module 03, Module 04, Module 05 |
| **Repudiation** (Chối bỏ) | Kẻ tấn công xóa dấu vết, không thể truy vết IP nguồn gây sự cố | Bật VPC Flow Logs cho 4 VPC, TGW Flow Logs, Suricata `eve.json` đẩy về CloudWatch | Module 02, Module 09 |
| **Information Disclosure** | Rò rỉ dữ liệu thẻ thanh toán / PII khách hàng ra C2 server ngoài Internet | Centralized Egress Firewall chặn domain lạ, Suricata IDS/IPS inspect payload | Module 05, Module 06 |
| **Denial of Service** | Tấn công SYN flood, HTTP flood làm cạn kiệt tài nguyên mạng Edge/Core | AWS WAF v2 rate-based rule, AWS Shield Standard, GWLB auto-scaling | Module 05, Module 07 |
| **Elevation of Privilege** | Chiếm quyền Pod frontend cố gắng kết nối trực tiếp cổng DB PostgreSQL 5432 | TGW Route Table cô lập hoàn toàn, Pod Identity tối thiểu, NetworkPolicy default-deny | Module 02, Module 03 |

### Bước 3: Rà Soát IAM Access Analyzer & Network Analyzer (Console)
1. Đăng nhập **AWS Management Console**, chọn Region Singapore `ap-southeast-1`.
2. Trên thanh tìm kiếm, nhập `IAM` -> Chọn **IAM** -> Menu bên trái chọn **Access Analyzer**.
3. Xác nhận trên Region Singapore đã có Analyzer hoạt động để phát hiện các tài nguyên bị chia sẻ công khai ngoài ý muốn.
4. Mở **VPC Console** -> Menu bên trái chọn **Network Access Analyzer** (dùng cho các bài phân tích đường đi mạng sau này).

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra tính nhất quán của tài liệu phân tích với cấu hình IAM và VPC hiện hữu:
```bash
# 1. Kiểm tra tài khoản không có quyền IAM quá mức (Least Privilege)
aws iam get-account-summary --region ap-southeast-1 --output table

# 2. Kiểm tra trạng thái IAM Access Analyzer tại Region Singapore
aws access-analyzer list-analyzers --region ap-southeast-1 --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Tài liệu thiết kế được lưu phiên bản trên Git. Trong trường hợp thay đổi mô hình kiến trúc, tạo Pull Request để cập nhật bảng ma trận STRIDE tương ứng.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/01-threat-model/01-stride-matrix.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Hoàn thành bảng ma trận STRIDE cho toàn bộ 5 ranh giới bảo mật.
- [ ] Xác định rõ vai trò và vị trí của từng lớp tường lửa (WAF, SG, NACL, NetworkPolicy, GWLB, Network Firewall).
- [ ] Xác nhận không có đường tắt (bypass) trực tiếp từ Edge/Core ra Internet mà không qua Egress VPC.
