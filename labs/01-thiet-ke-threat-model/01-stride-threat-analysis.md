# Lab 01.01: Phân Tích Mô Hình Đe Dọa STRIDE Cho Hạ Tầng Mạng & EKS

**Mã tài liệu:** `LAB-01-01`
**Trạng thái:** `RUNTIME_PASS`
**Vùng áp dụng:** `ap-southeast-1` (Singapore)

---

## 1. Mục Tiêu (Objective)
Xác định bề mặt tấn công trên 5 ranh giới tin cậy (Trust Boundaries) và thiết lập ma trận kiểm soát an ninh mạng theo mô hình STRIDE cho cụm EKS kép và hạ tầng phân đoạn đa VPC.

---

## 2. Tài Nguyên (Resources)

| Tên / Ranh Giới Tin Cậy | Loại Tài Nguyên | Phạm Vi Kiểm Soát | Biện Pháp Bảo Mật Thiết Kế |
| :--- | :--- | :--- | :--- |
| Ranh giới Ingress L7 | AWS WAFv2 + Public ALB | `fabric-edge-vpc` | Chặn SQLi, XSS, rate-limit trên Public ALB |
| Ranh giới Đông - Tây (East-West) | TGW + GWLB + Suricata IPS | `fabric-inspection-vpc` | Inline Deep Packet Inspection qua GENEVE UDP 6081 |
| Ranh giới Thoát (Egress) | AWS Network Firewall | `fabric-egress-vpc` | Domain allowlist SNI, chặn botnet/C2 exfiltration |
| Ranh giới Trung Tâm (Inter-VPC) | AWS Transit Gateway | Toàn bộ 4 VPCs | 4 TGW Route Tables cô lập, chống Route Leak |
| Ranh giới Vi Mô (Intra-cluster) | K8s NetworkPolicy | `edge-eks` & `core-eks` | Default-deny-all, chỉ cho phép `edge-frontend` gọi `core-service` |

---

## 3. Thẻ Định Danh (Tags)

| Khóa (Key) | Giá Trị (Value) | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-*` | Toàn bộ tài nguyên an ninh mạng |
| `Project` | `aws-eks-secure-network-fabric` | Quy chuẩn thiết kế an ninh |
| `Environment` | `prod` | Toàn bộ các chốt chặn an ninh |
| `ManagedBy` | `manual` | Quản trị chính sách an ninh mạng thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### Ma Trận Đe Dọa STRIDE & Cơ Chế Kiểm Soát
| Danh mục STRIDE | Nguy Cơ Kỹ Thuật Cụ Thể | Biện Pháp Kiểm Soát Mạng (Mitigation) | Chốt Chặn Hiện Thực |
| :--- | :--- | :--- | :--- |
| **Spoofing** (Giả mạo) | Giả mạo IP Pod hoặc IP nguồn vượt qua firewall | VPC Source/Dest Check, AWS VPC CNI strict binding, NetworkPolicy | Module 02, Module 03 |
| **Tampering** (Can thiệp) | Bắt trộm gói tin, sửa đổi payload giữa Edge và Core | Bắt buộc TLS 1.3 nội bộ, mã hóa KMS, kiểm tra qua GWLB | Module 03, Module 05 |
| **Repudiation** (Chối bỏ) | Xóa dấu vết kết nối, không thể truy vết tấn công | VPC Flow Logs 4 VPCs, TGW Flow Logs, Suricata `eve.json` | Module 02, Module 09 |
| **Information Disclosure** | Rò rỉ dữ liệu thẻ / PII ra ngoài Internet | Egress Network Firewall chặn domain ngoài danh mục | Module 06 |
| **Denial of Service** | Tấn công SYN Flood, HTTP Flood làm sập dịch vụ | AWS WAFv2 rate-based rule, Shield Standard, GWLB auto-scale | Module 05, Module 07 |
| **Elevation of Privilege** | Pod `edge-frontend` vượt rào truy cập trực tiếp Database | Cô lập TGW Route Table, EKS Pod Identity tối thiểu | Module 02, Module 03 |

---

## 5. Phụ Thuộc (Dependencies)
- Hoàn thành thiết lập môi trường và định danh tại [Module 00](../00-chuan-bi-inventory/README.md).
- Kiến trúc mạng tổng thể theo tài liệu [README.md](../../README.md).

---

## 6. Kiểm Tra Đạt (Verification)
- [x] Lập bản đồ 5 ranh giới an ninh với đầy đủ biện pháp kiểm soát cho baseline 2 services (`edge-frontend`, `core-service`).
- [x] Xác nhận không có đường tắt (bypass) trực tiếp từ Edge/Core ra Internet mà không qua Egress VPC.
- [x] Bằng chứng runtime đã thu thập: [`evidence/01-threat-model/01-stride-matrix.json`](../../evidence/01-threat-model/01-stride-matrix.json).

---

## 7. Cảnh Báo An Toàn & Rollback Plan
- **Cảnh báo an ninh:** Mọi thay đổi trong ma trận STRIDE ảnh hưởng trực tiếp đến cấu hình Security Group, NetworkPolicy và Suricata rules.
- **Kế hoạch khôi phục (Rollback):** Lưu vết thay đổi ma trận kiểm soát thông qua Git versioning.
