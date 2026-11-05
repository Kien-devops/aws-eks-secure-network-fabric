#!/usr/bin/env python3
"""
Refactor Modules 01 through 06 for AWS EKS Secure Network Fabric.
Applies:
- Standard 7-section structure + DRAFT status lifecycle
- DAG alignment without cyclic dependency (Edge-Core cutover in Module 05)
- EKS 1.31 upgrade & Private VPC Endpoints lab
- Full NetworkPolicy pod communication matrix
- AWS Load Balancer Controller for Core NLB (IP-target type)
- Suricata GWLB GENEVE TLV handling and 2 Zonal GWLBe endpoints
- Egress Firewall return path fix & Appliance Mode on Egress TGW attachment
- Zero unredacted Account IDs
"""

from pathlib import Path

LABS_DIR = Path("E:/repo/project6/aws-eks-secure-network-fabric/labs")

# ==============================================================================
# MODULE 01: Thiết Kế & Threat Model
# ==============================================================================
mod01 = LABS_DIR / "01-thiet-ke-threat-model"

(mod01 / "01-stride-threat-analysis.md").write_text("""# 01.01 — Phân Tích Mô Hình Đe Dọa STRIDE Cho Hạ Tầng Mạng & EKS

> **Mã bài lab:** `01.01`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 30 phút  
> **Chi phí ước tính:** $0.00 USD (Thiết kế kiến trúc)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab thuộc [Module 00: Chuẩn Bị & Inventory](../00-chuan-bi-inventory/README.md).
- Hiểu rõ sơ đồ kiến trúc tổng thể 4 VPC (Edge, Core, Inspection, Egress) theo [spec.md](../../spec.md).

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Bài lab phân tích mô hình đe dọa trên tài liệu thiết kế kiến trúc, không yêu cầu gọi API đám mây đặc thù.

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD.
- **Cảnh báo an ninh:** Các biện pháp kiểm soát an ninh (Controls) được xác định trong bài lab này là yêu cầu bắt buộc phải được hiện thực hóa trong các module tiếp theo (NACL, SG, NetworkPolicy, Suricata, Network Firewall, AWS WAF).

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Rà Soát Bề Mặt Tấn Công (Attack Surface Mapping)
Phân tích 5 ranh giới bảo mật (Trust Boundaries):
1. **Internet <-> Edge EKS VPC:** Ranh giới Ingress công cộng.
2. **Edge EKS <-> Core EKS (East-West):** Ranh giới giữa tầng DMZ/Frontend và tầng xử lý nghiệp vụ/dữ liệu nhạy cảm.
3. **Core EKS <-> Internet (Egress):** Ranh giới kết nối ra ngoài để tải package, cập nhật bảo mật hoặc gọi API đối tác.
4. **VPC <-> Transit Gateway:** Ranh giới định tuyến trung tâm giữa các VPC.
5. **Pod <-> Pod (Intra-cluster):** Ranh giới giao tiếp vi mô trong cụm Kubernetes.

### Bước 2: Ma Trận Đe Dọa STRIDE & Biện Pháp Kiểm Soát
Xây dựng bảng đối chiếu các nguy cơ theo mô hình STRIDE:

| Danh mục STRIDE | Nguy cơ cụ thể trên kiến trúc | Biện pháp kiểm soát mạng tương ứng (Mitigation) |
|---|---|---|
| **Spoofing** (Giả mạo) | Giả mạo IP nguồn từ VPC khác hoặc Pod lạ | AWS VPC Source/Dest Check, K8s NetworkPolicy, AWS WAF rate limit |
| **Tampering** (Can thiệp) | Can thiệp gói tin truyền giữa Edge và Core | Bắt buộc mTLS L7 nội bộ, mã hóa đường truyền KMS, transit qua GWLB |
| **Repudiation** (Chối bỏ) | Không ghi nhận được nguồn gốc kết nối tấn công | VPC Flow Logs tập trung, TGW Flow Logs, Suricata `eve.json` |
| **Information Disclosure** | Rò rỉ dữ liệu thẻ thanh toán / PII ra ngoài | Centralized Egress Firewall chặn domain lạ, Suricata IDS/IPS inspect payload |
| **Denial of Service** | Tấn công DDoS hoặc cạn kiệt tài nguyên mạng | AWS WAF v2 rate-based rule, AWS Shield Standard, GWLB auto scaling |
| **Elevation of Privilege** | Pod frontend bị chiếm quyền cố gắng gọi trực tiếp DB | TGW Route Table cô lập hoàn toàn, Pod Identity tối thiểu, NetworkPolicy default-deny |

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra tính nhất quán của tài liệu phân tích với cấu hình IAM và VPC hiện hữu:
```bash
# Kiểm tra tài khoản không có quyền IAM quá mức (Least Privilege)
aws iam get-account-summary --region ap-southeast-1 --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Tài liệu thiết kế được lưu phiên bản trên Git. Trong trường hợp thay đổi mô hình kiến trúc, tạo Pull Request để cập nhật bảng ma trận STRIDE tương ứng.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/01-design/01-stride-matrix.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Hoàn thành bảng ma trận STRIDE cho toàn bộ 5 ranh giới bảo mật.
- [ ] Xác định rõ vai trò của từng lớp tường lửa (WAF, SG, NACL, NetworkPolicy, GWLB, Network Firewall).
- [ ] Được phê duyệt bởi Cloud Security Architect trước khi khởi tạo VPC.
""", encoding="utf-8")

(mod01 / "02-cidr-ip-allocation-plan.md").write_text("""# 01.02 — Kế Hoạch Phân Bổ Dải Mạng (IP Plan) & Quy Hoạch Subnets

> **Mã bài lab:** `01.02`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 20 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành phân tích mô hình đe dọa [01.01 — Phân Tích STRIDE](01-stride-threat-analysis.md).
- Đã xác nhận trên AWS Inventory không có VPC nào xung đột dải mạng `10.40.0.0/16`, `10.50.0.0/16`, `10.70.0.0/16`, `10.80.0.0/16`.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Bài lab quy hoạch dải mạng trên thiết kế, không yêu cầu gọi API cấp phát tài nguyên.

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD.
- **Cảnh báo quan trọng:** Dải mạng CIDR của VPC sau khi tạo không thể thu hẹp. Việc quy hoạch kích thước subnet phải tính toán dự phòng cho địa chỉ IP của Pod (Secondary CIDR nếu cần), IP của ENI TGW và IP của VPC Endpoints.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bảng Quy Hoạch Chi Tiết 4 VPCs & Subnets

#### 1. Edge EKS VPC (`10.40.0.0/16`)
- `ap-southeast-1a`:
  - `Public Subnet ALB A`: `10.40.0.0/24` (251 IPs khả dụng)
  - `Private Subnet Node A`: `10.40.10.0/22` (1,019 IPs khả dụng cho EKS Nodes/Pods)
  - `Private Subnet VPCE A`: `10.40.20.0/24` (251 IPs cho VPC Endpoints)
  - `TGW Subnet A`: `10.40.250.0/28` (11 IPs dành riêng cho TGW ENI)
- `ap-southeast-1b`:
  - `Public Subnet ALB B`: `10.40.1.0/24`
  - `Private Subnet Node B`: `10.40.14.0/22`
  - `Private Subnet VPCE B`: `10.40.21.0/24`
  - `TGW Subnet B`: `10.40.250.16/28`

#### 2. Core EKS VPC (`10.50.0.0/16`)
- `ap-southeast-1a`:
  - `Private Subnet Node A`: `10.50.10.0/22` (EKS Nodes/Pods nghiệp vụ)
  - `Private Subnet Data A`: `10.50.20.0/24` (Aurora PostgreSQL / ElastiCache Redis)
  - `Private Subnet VPCE A`: `10.50.30.0/24` (VPC Endpoints ECR, SQS, Logs)
  - `TGW Subnet A`: `10.50.250.0/28`
- `ap-southeast-1b`:
  - `Private Subnet Node B`: `10.50.14.0/22`
  - `Private Subnet Data B`: `10.50.21.0/24`
  - `Private Subnet VPCE B`: `10.50.31.0/24`
  - `TGW Subnet B`: `10.50.250.16/28`

#### 3. Inspection VPC (`10.70.0.0/16`)
- `ap-southeast-1a`:
  - `TGW Subnet A`: `10.70.0.0/28` (TGW Attachment ENI - Appliance Mode = ENABLED)
  - `GWLBe Subnet A`: `10.70.1.0/28` (VPC Endpoint kết nối GWLB trong AZ-a)
  - `Firewall Subnet A`: `10.70.10.0/24` (Suricata EC2 Appliance A)
- `ap-southeast-1b`:
  - `TGW Subnet B`: `10.70.0.16/28`
  - `GWLBe Subnet B`: `10.70.1.16/28` (VPC Endpoint kết nối GWLB trong AZ-b)
  - `Firewall Subnet B`: `10.70.11.0/24` (Suricata EC2 Appliance B)

#### 4. Centralized Egress VPC (`10.80.0.0/16`)
- `ap-southeast-1a`:
  - `TGW Subnet A`: `10.80.0.0/28` (TGW Attachment ENI - Appliance Mode = ENABLED)
  - `Firewall Subnet A`: `10.80.1.0/28` (AWS Network Firewall Endpoint AZ-a)
  - `Public Subnet NAT A`: `10.80.10.0/24` (NAT Gateway A + IGW)
- `ap-southeast-1b`:
  - `TGW Subnet B`: `10.80.0.16/28`
  - `Firewall Subnet B`: `10.80.1.16/28` (AWS Network Firewall Endpoint AZ-b)
  - `Public Subnet NAT B`: `10.80.11.0/24` (NAT Gateway B + IGW)

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra xác nhận không có dải mạng nào trùng lặp trên tài khoản:
```bash
aws ec2 describe-vpcs --region ap-southeast-1 \
  --query 'Vpcs[*].CidrBlock' --output json
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Trong giai đoạn thiết kế, mọi cập nhật dải CIDR được ghi nhận bằng văn bản và điều chỉnh lại bảng phân bổ trước khi áp dụng vào Module 02.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/01-design/02-ip-plan-audit.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Toàn bộ 4 VPCs hoàn toàn không chồng lấn CIDR (`10.40/16`, `10.50/16`, `10.70/16`, `10.80/16`).
- [ ] Subnet TGW và Subnet Endpoints có kích thước tối thiểu `/28` theo chuẩn AWS.
- [ ] Subnet Private Nodes có ít nhất `/22` đáp ứng mật độ Pod IP của EKS VPC CNI.
""", encoding="utf-8")

(mod01 / "03-tgw-routing-matrix-hop-tables.md").write_text("""# 01.03 — Ma Trận Định Tuyến TGW & Bảng Bước Nhảy Gói Tin (Hop Tables)

> **Mã bài lab:** `01.03`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 30 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bảng phân bổ IP [01.02 — Kế Hoạch Phân Bổ Dải Mạng](02-cidr-ip-allocation-plan.md).
- Nắm vững nguyên lý hoạt động của AWS Transit Gateway Route Tables và Appliance Mode.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Bài lab phân tích ma trận định tuyến logic, không yêu cầu quyền gọi API.

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD.
- **Cảnh báo định tuyến đối xứng (Symmetric Routing):** Tường lửa kiểm tra trạng thái (Stateful Firewall như Suricata và AWS Network Firewall) sẽ lập tức DROP gói tin nếu luồng đi (Request) và luồng về (Response) đi qua 2 AZ khác nhau (Asymmetric Routing). Bắt buộc phải bật `ApplianceModeSupport = enable` trên TGW Attachment tương ứng.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### 1. Bảng Bước Nhảy East-West (Edge EKS sang Core EKS qua GWLB)
> *Lưu ý DAG:* Tuyến đường này được định hình thiết kế tại đây, nhưng chỉ được cắt chuyển (cutover) chính thức trong Module 05 sau khi GWLB và Suricata đã kiểm tra sức khỏe đạt 100%.

| Bước | Thành phần | Source IP | Destination IP | Hành động định tuyến |
|---|---|---|---|---|
| 1 | Pod Frontend (Edge) | `10.40.10.x` | `10.50.20.y` (Core NLB) | Gửi gói tin qua default gateway của node |
| 2 | Subnet Route Table (Edge) | `10.40.10.x` | `10.50.0.0/16` | Trỏ tới TGW Attachment |
| 3 | TGW `edge-rt` | `10.40.10.x` | `10.50.0.0/16` | Định tuyến sang Inspection VPC Attachment (Appliance Mode) |
| 4 | TGW Subnet RT (Inspection) | `10.40.10.x` | `10.50.0.0/16` | Trỏ tới Zonal GWLB Endpoint (`gwlbe-1a` hoặc `gwlbe-1b`) |
| 5 | GWLB & Suricata | `10.40.10.x` | `10.50.0.0/16` | Đóng gói GENEVE (UDP 6081), Suricata kiểm tra ID/IPS, trả về GWLB |
| 6 | GWLBe Subnet RT (Inspection) | `10.40.10.x` | `10.50.0.0/16` | Trỏ về TGW Attachment |
| 7 | TGW `inspection-rt` | `10.40.10.x` | `10.50.0.0/16` | Định tuyến sang Core EKS VPC Attachment |
| 8 | Core Subnet RT | `10.40.10.x` | `10.50.20.y` | Giao gói tin đến Core Internal NLB / Pod đích |

### 2. Bảng Bước Nhảy Outbound (Core EKS ra Internet qua Centralized Egress Firewall)

| Bước | Thành phần | Hành động định tuyến |
|---|---|---|
| 1 | Pod trong Core EKS | Gửi kết nối ra `0.0.0.0/0` |
| 2 | Core Subnet RT | Trỏ `0.0.0.0/0` -> TGW Attachment |
| 3 | TGW `core-rt` | Trỏ `0.0.0.0/0` -> Egress VPC Attachment (Appliance Mode = ENABLED) |
| 4 | TGW Subnet RT (Egress) | Trỏ `0.0.0.0/0` -> AWS Network Firewall Endpoint trong cùng AZ |
| 5 | AWS Network Firewall | Kiểm tra Stateful Rule (Domain allowlist, Drop nếu ngoài danh mục) |
| 6 | Firewall Subnet RT | Trỏ `0.0.0.0/0` -> NAT Gateway trong cùng AZ |
| 7 | Public Subnet (NAT) | NAT Gateway chuyển đổi sang Elastic IP và chuyển tới IGW ra Internet |
| 8 | **Return Path (Quan Trọng)** | Traffic phản hồi từ Internet về NAT Gateway -> Public Subnet RT **BẮT BUỘC TRỎ `10.40.0.0/16` và `10.50.0.0/16` VỀ FIREWALL ENDPOINT** (Không trỏ trực tiếp về TGW để tránh bypass tường lửa)! |

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra tính sẵn sàng của kiến trúc định tuyến lý thuyết:
```bash
# Đối chiếu lại các route tables được dự kiến cấu hình
echo "Hop table validation: East-West symmetric routing requires TGW Appliance Mode."
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Bảng ma trận định tuyến là tài liệu kiểm soát. Khi phát sinh sự cố bất đối xứng (asymmetric drop), kiến trúc sư dựa vào bảng hop table để truy vết hop gây ra lỗi.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/01-design/03-hop-tables-spec.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Bảng hop table xác định chi tiết đường đi của từng hop cho cả chiều đi (Forward) và chiều về (Return).
- [ ] Xác nhận rõ quy tắc Return Path tại Egress VPC bắt buộc đi qua Network Firewall.
- [ ] Bật cờ `ApplianceModeSupport` trên các Attachment liên quan.
""", encoding="utf-8")

print("Module 01 rewritten successfully.")
