# 06.04 — Cấu Hình Bảng Định Tuyến Egress Return Path & Kiểm Thử Lọc Tên Miền

> **Mã bài lab:** `06.04`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — Subnets: Egress VPC  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành toàn bộ các bài lab [06.01](01-nat-gateways-per-az.md), [06.02](02-network-firewall-rule-groups.md), và [06.03](03-network-firewall-deployment.md).
- Đã trích xuất chính xác 2 Firewall Endpoint IDs (`vpce-...`) của AWS Network Firewall tại AZ-a và AZ-b.
- Cụm Core EKS đang hoạt động và sẵn sàng thực thi lệnh kiểm thử từ Pods.
- Đang mở phiên AWS Management Console tại Singapore `ap-southeast-1`.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để thực thi bài lab này:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateRouteTable",
        "ec2:AssociateRouteTable",
        "ec2:CreateRoute",
        "ec2:ReplaceRoute",
        "ec2:DescribeRouteTables",
        "logs:FilterLogEvents",
        "logs:GetLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD.
- **CẢNH BÁO QUAN TRỌNG NHẤT VỀ RETURN PATH (Tránh Bypass Tường Lửa):**
  Lưu lượng phản hồi từ Internet về NAT Gateway sẽ mang IP đích là CIDR của Edge (`10.40.0.0/16`) hoặc Core (`10.50.0.0/16`). Bảng định tuyến của **Public NAT Subnet BẮT BUỘC PHẢI TRỎ `10.40.0.0/16` và `10.50.0.0/16` VỀ NETWORK FIREWALL ENDPOINT (`vpce-...`) TRONG CÙNG AZ**. 
  **TUYỆT ĐỐI KHÔNG ĐƯỢC TRỎ TRỰC TIẾP VỀ TGW!** Nếu trỏ trực tiếp về TGW, lưu lượng chiều về sẽ bypass hoàn toàn tường lửa, khiến Network Firewall ngắt kết nối do không thấy gói tin ACK trở về và gây đứt kết nối TCP.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Thu Thập 2 Firewall Endpoint IDs
Trước khi cấu hình bảng định tuyến, mở **VPC Console** -> **Network Firewall** -> **Firewalls** -> `fabric-egress-nfw`:
- Tại tab **Firewall details** -> Mục **Subnet mappings**:
  - Ghi nhận `VPCE_1A`: Endpoint ID gắn với `fabric-egress-fw-1a` tại `ap-southeast-1a`.
  - Ghi nhận `VPCE_1B`: Endpoint ID gắn với `fabric-egress-fw-1b` tại `ap-southeast-1b`.

---

### Bước 2: Cấu Hình 6 Bảng Định Tuyến Phân Tách Theo Từng AZ Tại Egress VPC
Mở **VPC Console** -> Menu bên trái chọn **Route tables**:

#### 1. Nhóm Bảng Định Tuyến TGW Subnets (Gói tin từ TGW vào Egress VPC):
- **Tạo `fabric-egress-tgw-rt-1a`:**
  - Nhấp **Create route table** -> Name: `fabric-egress-tgw-rt-1a` | VPC: `fabric-egress-vpc` -> Nhấp **Create**.
  - Tab **Subnet associations**: Gắn duy nhất subnet `fabric-egress-tgw-1a` (`10.80.0.0/28`).
  - Tab **Routes** -> **Edit routes**:
    - Nhấp **Add route**: Destination: `0.0.0.0/0` -> Target: Chọn **VPC Endpoint** -> Chọn `VPCE_1A`.
    - Nhấp **Save changes**.
- **Tạo `fabric-egress-tgw-rt-1b`:**
  - Nhấp **Create route table** -> Name: `fabric-egress-tgw-rt-1b` | VPC: `fabric-egress-vpc` -> Nhấp **Create**.
  - Tab **Subnet associations**: Gắn duy nhất subnet `fabric-egress-tgw-1b` (`10.80.0.16/28`).
  - Tab **Routes** -> **Edit routes**:
    - Nhấp **Add route**: Destination: `0.0.0.0/0` -> Target: Chọn **VPC Endpoint** -> Chọn `VPCE_1B`.
    - Nhấp **Save changes**.

#### 2. Nhóm Bảng Định Tuyến Firewall Subnets (Gói tin sau khi Firewall kiểm tra cho phép):
- **Tạo `fabric-egress-fw-rt-1a`:**
  - Nhấp **Create route table** -> Name: `fabric-egress-fw-rt-1a` | VPC: `fabric-egress-vpc` -> Nhấp **Create**.
  - Tab **Subnet associations**: Gắn subnet `fabric-egress-fw-1a` (`10.80.1.0/28`).
  - Tab **Routes** -> **Edit routes**:
    - Nhấp **Add route**: Destination: `0.0.0.0/0` -> Target: Chọn **NAT Gateway** -> Chọn `fabric-nat-gw-1a`.
    - Nhấp **Add route**: Destination: `10.40.0.0/16` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
    - Nhấp **Add route**: Destination: `10.50.0.0/16` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
    - Nhấp **Save changes**.
- **Tạo `fabric-egress-fw-rt-1b`:**
  - Nhấp **Create route table** -> Name: `fabric-egress-fw-rt-1b` | VPC: `fabric-egress-vpc` -> Nhấp **Create**.
  - Tab **Subnet associations**: Gắn subnet `fabric-egress-fw-1b` (`10.80.1.16/28`).
  - Tab **Routes** -> **Edit routes**:
    - Nhấp **Add route**: Destination: `0.0.0.0/0` -> Target: Chọn **NAT Gateway** -> Chọn `fabric-nat-gw-1b`.
    - Nhấp **Add route**: Destination: `10.40.0.0/16` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
    - Nhấp **Add route**: Destination: `10.50.0.0/16` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
    - Nhấp **Save changes**.

#### 3. Nhóm Bảng Định Tuyến Public NAT Subnets (Gói tin phản hồi từ Internet quay về — ĐIỂM SỐNG CÒN):
- **Tạo `fabric-egress-public-rt-1a`:**
  - Nhấp **Create route table** -> Name: `fabric-egress-public-rt-1a` | VPC: `fabric-egress-vpc` -> Nhấp **Create**.
  - Tab **Subnet associations**: Gắn subnet `fabric-egress-public-1a` (`10.80.10.0/24`).
  - Tab **Routes** -> **Edit routes**:
    - Nhấp **Add route**: Destination: `0.0.0.0/0` -> Target: Chọn **Internet Gateway** -> Chọn `fabric-egress-igw`.
    - Nhấp **Add route**: Destination: `10.40.0.0/16` -> Target: Chọn **VPC Endpoint** -> Chọn `VPCE_1A` *(Bắt buộc qua Firewall)*.
    - Nhấp **Add route**: Destination: `10.50.0.0/16` -> Target: Chọn **VPC Endpoint** -> Chọn `VPCE_1A` *(Bắt buộc qua Firewall)*.
    - Nhấp **Save changes**.
- **Tạo `fabric-egress-public-rt-1b`:**
  - Nhấp **Create route table** -> Name: `fabric-egress-public-rt-1b` | VPC: `fabric-egress-vpc` -> Nhấp **Create**.
  - Tab **Subnet associations**: Gắn subnet `fabric-egress-public-1b` (`10.80.11.0/24`).
  - Tab **Routes** -> **Edit routes**:
    - Nhấp **Add route**: Destination: `0.0.0.0/0` -> Target: Chọn **Internet Gateway** -> Chọn `fabric-egress-igw`.
    - Nhấp **Add route**: Destination: `10.40.0.0/16` -> Target: Chọn **VPC Endpoint** -> Chọn `VPCE_1B`.
    - Nhấp **Add route**: Destination: `10.50.0.0/16` -> Target: Chọn **VPC Endpoint** -> Chọn `VPCE_1B`.
    - Nhấp **Save changes**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

### 1. Kiểm Thử Dương Tính: Truy Cập Tên Miền Trong Allowlist (PASS HTTP 200)
Từ một Pod trong cụm `fabric-core-eks`, thực hiện gọi HTTPS tới các domain đã cho phép trong Stateful Domain Group (`github.com`, `quay.io`):
```bash
# Thực thi từ pod kiểm thử trong cụm Core EKS
kubectl run egress-allow-test --rm -it --image=curlimages/curl --restart=Never -n fabric-apps --context fabric-core -- \
  curl -Iv https://github.com --connect-timeout 5
```
**Kết quả kỳ vọng:** Bắt tay TLS thành công, trả về mã trạng thái `HTTP/2 200` hoặc `HTTP/1.1 200 OK`.

---

### 2. Kiểm Thử Âm Tính: Truy Cập Tên Miền Ngoài Danh Mục (Kỳ vọng: DROP / Timeout)
Thực hiện truy cập một domain không có trong danh mục allowlist (ví dụ: `example.com` hoặc `facebook.com`):
```bash
kubectl run egress-deny-test --rm -it --image=curlimages/curl --restart=Never -n fabric-apps --context fabric-core -- \
  curl -Iv https://example.com --connect-timeout 5 || echo "PASSED: Unauthorized Domain Blocked by Network Firewall!"
```
**Kết quả kỳ vọng:** Kết nối bị treo và báo `Connection timed out` sau 5 giây do gói tin bị Network Firewall DROP âm thầm.

---

### 3. Kiểm Tra Bằng Chứng Cảnh Báo Trên CloudWatch Logs
Truy vấn trực tiếp Log Group cảnh báo của AWS Network Firewall:
```bash
aws logs filter-log-events --region ap-southeast-1 \
  --log-group-name /aws/network-firewall/fabric-egress-alerts \
  --max-items 5 \
  --query 'events[*].message' \
  --output text
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Trong trường hợp phát sinh lỗi định tuyến khiến toàn bộ kết nối ra Internet bị tắc nghẽn:
1. Kiểm tra lại việc trỏ Endpoint ID tại các bảng `fabric-egress-public-rt-1a/b`.
2. Nếu cần khôi phục khẩn cấp, có thể tạm thời trỏ `10.40.0.0/16` và `10.50.0.0/16` trên Public Subnet về `fabric-tgw` để xác định nguyên nhân.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/06-firewall/04-egress-domain-filter-test.log`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Cấu hình đúng 6 Route Tables phân tách theo AZ tại Egress VPC.
- [ ] Bảng định tuyến Public Subnet trỏ `10.40.0.0/16` và `10.50.0.0/16` về đúng Firewall Endpoint trong cùng AZ.
- [ ] Pod trong Core EKS truy cập thành công tên miền allowlist (`github.com`, `quay.io`).
- [ ] Pod trong Core EKS bị chặn 100% khi truy cập tên miền ngoài allowlist (`example.com`).
- [ ] CloudWatch Log Group `/aws/network-firewall/fabric-egress-alerts` ghi nhận chính xác sự kiện DROP/ALERT.
