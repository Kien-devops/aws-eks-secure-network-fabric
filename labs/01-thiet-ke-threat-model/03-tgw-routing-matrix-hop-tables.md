# 01.03 — Ma Trận Định Tuyến TGW & Bảng Bước Nhảy Gói Tin (Hop Tables)

> **Mã bài lab:** `01.03`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 30 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — AZs: `ap-southeast-1a`, `ap-southeast-1b`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bảng phân bổ IP [01.02 — Kế Hoạch Phân Bổ Dải Mạng](02-cidr-ip-allocation-plan.md).
- Nắm vững nguyên lý hoạt động của AWS Transit Gateway Route Tables, Subnet Route Chaining và Appliance Mode.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Bài lab phân tích ma trận định tuyến logic và mô phỏng bước nhảy trên tài liệu thiết kế:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeTransitGateways",
        "ec2:DescribeTransitGatewayRouteTables",
        "ec2:DescribeRouteTables"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD.
- **Cảnh báo định tuyến đối xứng (Symmetric Routing & Appliance Mode):** Tường lửa kiểm tra trạng thái (Stateful Firewall như Suricata và AWS Network Firewall) sẽ lập tức DROP gói tin nếu luồng đi (Request) và luồng về (Response) đi qua 2 AZ khác nhau (Asymmetric Routing). Bắt buộc phải bật `ApplianceModeSupport = enable` trên TGW Attachment kết nối vào Inspection VPC và Egress VPC.
- **Cảnh báo bẫy định tuyến đường về (Return Path Trap):** Khi gói tin từ Internet quay trở lại qua NAT Gateway, Route Table của Public Subnet trong Egress VPC **bắt buộc phải trỏ dải mạng `10.40.0.0/16` và `10.50.0.0/16` về điểm cuối Network Firewall**, tuyệt đối không trỏ thẳng về TGW để tránh tình trạng bypass kiểm duyệt chiều về.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Thiết Kế Ma Trận Phân Đoạn Định Tuyến TGW (TGW Route Domains)
Trên AWS Transit Gateway Console, chúng ta thiết lập 4 miền định tuyến độc lập (fail-closed, tắt hoàn toàn default association và propagation):

| TGW Route Table | Attachment Được Associated | Static Routes Cấu Hình | Mục Đích Thiết Kế An Ninh |
|---|---|---|---|
| **`fabric-tgw-edge-rt`** | `fabric-edge-tgw-attachment` | `10.50.0.0/16` -> `fabric-insp-tgw-attachment`<br>`0.0.0.0/0` -> `fabric-egress-tgw-attachment` | Bắt buộc lưu lượng sang Core phải vào Inspection VPC; lưu lượng ra Internet phải vào Egress VPC. |
| **`fabric-tgw-core-rt`** | `fabric-core-tgw-attachment` | `10.40.0.0/16` -> `fabric-insp-tgw-attachment`<br>`0.0.0.0/0` -> `fabric-egress-tgw-attachment` | Bắt buộc lưu lượng về Edge phải vào Inspection VPC; lưu lượng ra Internet phải vào Egress VPC. |
| **`fabric-tgw-inspection-rt`** | `fabric-insp-tgw-attachment` | `10.40.0.0/16` -> `fabric-edge-tgw-attachment`<br>`10.50.0.0/16` -> `fabric-core-tgw-attachment` | Sau khi Suricata kiểm duyệt xong, gói tin trả về TGW và được định tuyến đến đúng VPC đích. |
| **`fabric-tgw-egress-rt`** | `fabric-egress-tgw-attachment` | `10.40.0.0/16` -> `fabric-edge-tgw-attachment`<br>`10.50.0.0/16` -> `fabric-core-tgw-attachment` | Định tuyến phản hồi từ Internet sau khi qua Network Firewall về đúng VPC khởi tạo. |
| **`fabric-tgw-dev-rt`** *(Mở rộng)* | `fabric-dev-tgw-attachment` | `10.40.0.0/16` -> `blackhole`<br>`10.50.0.0/16` -> `blackhole` | Cô lập triệt để môi trường Dev, ngăn không cho chạm vào Prod workloads. |

### Bước 2: Bảng Bước Nhảy Chi Tiết Luồng Đông - Tây (East-West Hop-by-Hop Trace)
Luồng từ Pod Frontend (`10.40.10.x`) gọi sang Internal NLB của Core EKS (`10.50.20.y`):

```text
[Pod Frontend] 
    │ (1. Node default route)
    ▼
[Edge Node Subnet RT] ─── 10.50.0.0/16 ───► [Edge TGW Attachment]
                                                    │ (2. Ingress TGW lookup fabric-tgw-edge-rt)
                                                    ▼
[TGW fabric-tgw-edge-rt] ── 10.50.0.0/16 ──► [Inspection TGW Attachment] (Appliance Mode = ON)
                                                    │ (3. Gói tin giữ nguyên AZ-a)
                                                    ▼
[Inspection TGW Subnet RT] ─ 10.50.0.0/16 ─► [GWLB Endpoint AZ-a (gwlbe-1a)]
                                                    │ (4. Đóng gói GENEVE UDP 6081)
                                                    ▼
[Gateway Load Balancer] ───────────────────► [Suricata EC2 Appliance A]
                                                    │ (5. Kiểm tra IDS/IPS: ALLOW)
                                                    ▼
[Gateway Load Balancer] ◄─────────────────── [Suricata EC2 Appliance A]
    │ (6. Trả lại gói tin đã inspect)
    ▼
[Inspection GWLBe Subnet RT] 10.50.0.0/16 ─► [Inspection TGW Attachment]
                                                    │ (7. Ingress TGW lookup fabric-tgw-inspection-rt)
                                                    ▼
[TGW fabric-tgw-inspection-rt] 10.50.0.0/16► [Core TGW Attachment]
                                                    │ (8. Giao cho Core VPC)
                                                    ▼
[Core Subnet RT] ──────────────────────────► [Core Internal NLB] ──► [Pod Order Service]
```

### Bước 3: Bảng Bước Nhảy Chi Tiết Luồng Egress Ra Internet & Đường Về (Outbound & Return Trace)
Luồng từ Pod Core EKS kết nối ra Internet và gói tin phản hồi quay lại:

1. **Chiều Đi (Outbound Forward):**
   - **Hop 1:** Pod Core gửi gói tin `SYN` tới `quay.io:443`.
   - **Hop 2:** Subnet Route Table của Core EKS: `0.0.0.0/0` -> Target: `fabric-tgw`.
   - **Hop 3:** TGW `fabric-tgw-core-rt`: `0.0.0.0/0` -> Target: `fabric-egress-tgw-attachment`.
   - **Hop 4:** TGW Subnet RT trong Egress VPC: `0.0.0.0/0` -> Target: AWS Network Firewall Endpoint trong cùng AZ.
   - **Hop 5:** AWS Network Firewall kiểm tra TLS SNI allowlist. Kết quả: `ALLOW`.
   - **Hop 6:** Firewall Subnet RT trong Egress VPC: `0.0.0.0/0` -> Target: NAT Gateway trong cùng AZ.
   - **Hop 7:** NAT Gateway thực hiện SNAT sang Public IP và gửi qua Internet Gateway (IGW) ra ngoài.

2. **Chiều Về (Inbound Return Path — Điểm Sống Còn):**
   - **Hop 8:** Gói tin phản hồi `SYN-ACK` từ Internet quay trở về qua IGW tới Public Subnet NAT Gateway.
   - **Hop 9 (Bắt buộc):** Route Table của Public Subnet trong Egress VPC:
     - `10.40.0.0/16` -> Target: Network Firewall Endpoint cùng AZ.
     - `10.50.0.0/16` -> Target: Network Firewall Endpoint cùng AZ.
   - **Hop 10:** Network Firewall nhận diện đúng phiên kết nối TCP hợp lệ (Stateful inspection).
   - **Hop 11:** Firewall Subnet RT: `10.50.0.0/16` -> Target: `fabric-tgw`.
   - **Hop 12:** TGW `fabric-tgw-egress-rt`: `10.50.0.0/16` -> Target: `fabric-core-tgw-attachment`.
   - **Hop 13:** Gói tin quay trở lại Pod Core an toàn, hoàn tất bắt tay TCP 3 bước.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra tính sẵn sàng của kiến trúc định tuyến lý thuyết:
```bash
# Kiểm tra tài khoản sẵn sàng khởi tạo TGW
aws ec2 describe-transit-gateways --region ap-southeast-1 \
  --query 'TransitGateways[*].TransitGatewayId' --output text
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Bảng ma trận định tuyến là tài liệu kiểm soát. Khi phát sinh sự cố bất đối xứng (asymmetric drop) trong Module 10 (GameDay), kiến trúc sư đối soát từng hop trong bảng này để khôi phục cấu hình.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/01-threat-model/03-hop-tables-spec.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Bảng hop table xác định chi tiết đường đi của từng hop cho cả chiều đi (Forward) và chiều về (Return).
- [ ] Xác nhận rõ quy tắc Return Path tại Egress VPC bắt buộc đi qua Network Firewall Endpoint.
- [ ] Bật cờ `ApplianceModeSupport = enable` trên Inspection và Egress TGW Attachments.
- [ ] Phân vùng Blackhole được thiết kế chuẩn mực để cô lập môi trường Dev.
