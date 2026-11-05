# 01.01 — Phân Tích Mô Hình Đe Dọa STRIDE Cho Kiến Trúc Dual EKS

> **Trạng thái:** Tài liệu thiết kế kiến trúc an ninh mạng chuyên sâu.  
> **Áp dụng cho:** Đánh giá rủi ro, phân loại lỗ hổng mạng và xác lập biện pháp phòng thủ đa tầng trong môi trường container và TGW routing.

---

## 1. Giới Thiệu Khung Phân Tích STRIDE

Mô hình **STRIDE** do Microsoft phát triển được áp dụng để rà soát toàn diện các bề mặt tấn công của kiến trúc mạng Project 6:
- **S**poofing (Giả mạo danh tính)
- **T**ampering (Can thiệp/Sửa đổi dữ liệu)
- **R**epudiation (Chối bỏ trách nhiệm)
- **I**nformation Disclosure (Lộ lọt thông tin)
- **D**enial of Service (Từ chối dịch vụ)
- **E**levation of Privilege (Leo thang đặc quyền)

---

## 2. Bảng Phân Tích Rủi Ro Chi Tiết & Giải Pháp Thiết Kế

| Phân Loại | Bề Mặt Tấn Công (Attack Surface) | Kịch Bản Khai Thác Tiềm Ẩn | Biện Pháp Kiểm Soát Kỹ Thuật (Mitigation) |
|---|---|---|---|
| **Spoofing** | Giao diện mạng ENI giữa các VPC | Kẻ tấn công trong Dev VPC giả mạo địa chỉ IP nguồn để gửi request tới Core EKS. | - Bật Reverse Path Filtering (`rp_filter`) trên Suricata.<br>- TGW Blackhole route table chặn đứng luồng Dev.<br>- NACL stateless tại Core VPC chỉ cho phép IP nguồn từ dải `10.40.0.0/16`. |
| **Tampering** | Luồng dữ liệu East-West qua Transit Gateway | Man-in-the-middle (MITM) chặn bắt và thay đổi payload giữa Frontend và Order Service. | - Mã hóa đường truyền nội bộ bằng TLS 1.3.<br>- Xác thực chữ ký JWT bằng Secret lưu trong KMS.<br>- Giám sát toàn vẹn gói tin bằng Suricata deep-packet inspection. |
| **Repudiation** | Hoạt động mạng nội bộ và gọi API | Kẻ tấn công xóa dấu vết truy cập hoặc quét cổng trái phép trong mạng nội bộ. | - Bật VPC Flow Logs mức độ `ALL` (Accept + Reject).<br>- Thu thập log sự kiện Suricata `eve.json` tập trung trên CloudWatch Logs.<br>- Ghi nhận đầy đủ audit log trên cả 2 cụm EKS. |
| **Information Disclosure** | Luồng dữ liệu ra ngoài Internet (Outbound Egress) | Mã độc trong Core EKS cố gắng exfiltrate dữ liệu nhạy cảm ra máy chủ C2 bên ngoài. | - Chặn tuyệt đối đường ra Internet trực tiếp từ Core VPC.<br>- Buộc toàn bộ traffic `0.0.0.0/0` qua AWS Network Firewall.<br>- Lọc tên miền nghiêm ngặt qua TLS SNI Allowlist (chỉ cho phép các domain được cấp phép như `quay.io`, `github.com`). |
| **Denial of Service** | Cổng vào công khai Edge ALB Ingress | Tấn công SYN Flood, HTTP Flood hoặc khai thác lỗ hổng L7 gây quá tải hệ thống. | - Gắn AWS WAF v2 trực tiếp tại ALB Ingress.<br>- Áp dụng Rate Limiting Rule (500 requests / 5 phút per IP).<br>- Tích hợp AWS Shield Standard chống DDoS L3/L4. |
| **Elevation of Privilege** | Pod trong cụm Edge EKS bị chiếm quyền | Pod frontend bị chiếm quyền cố gắng truy cập trực tiếp vào Database Aurora hoặc Redis. | - Áp dụng Kubernetes `NetworkPolicy` mặc định Default Deny.<br>- Database đặt trong Data Subnet riêng biệt, Security Group chỉ cho phép kết nối từ Core EKS Node Security Group trên cổng 5432/6379. |

---

## 3. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Mọi rủi ro trong 6 hạng mục STRIDE đều có biện pháp kiểm soát kỹ thuật tương ứng trên hạ tầng mạng.
- [ ] Không có kịch bản nào cho phép traffic đi tắt (bypass) qua cụm kiểm soát an ninh (GWLB hoặc Network Firewall).

