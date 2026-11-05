# 02.03 — Tạo Bảng Định Tuyến TGW, VPC Attachments & Bật Appliance Mode

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Thiết lập 5 miền định tuyến TGW, liên kết VPC Attachments và kích hoạt cờ **Appliance Mode** trên Inspection VPC.

---

## 1. Mục Tiêu Kỹ Thuật

- Khởi tạo 5 bảng định tuyến trên Transit Gateway:
  1. `fabric-tgw-rt-edge`
  2. `fabric-tgw-rt-core`
  3. `fabric-tgw-rt-inspection`
  4. `fabric-tgw-rt-egress`
  5. `fabric-tgw-rt-dev`
- Tạo 4 Transit Gateway VPC Attachments gắn vào 4 VPCs tương ứng qua các Subnets TGW chuyên dụng (`/28`).
- **Kích hoạt tính năng `ApplianceModeSupport = enable` trên Inspection VPC Attachment** để đảm bảo định tuyến đối xứng (Symmetric Routing).
- Gắn kết (Associate) từng attachment vào đúng bảng định tuyến TGW tương ứng.

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Khởi Tạo 5 TGW Route Tables
1. Tại VPC Console, menu bên trái chọn **Transit gateway route tables** -> Nhấp **Create transit gateway route table**.
2. **Name tag:** `fabric-tgw-rt-edge` -> Chọn Transit gateway `fabric-tgw` -> Nhấp **Create**.
3. Lặp lại tạo tiếp 4 bảng định tuyến:
   - `fabric-tgw-rt-core`
   - `fabric-tgw-rt-inspection`
   - `fabric-tgw-rt-egress`
   - `fabric-tgw-rt-dev`

---

### Bước 2: Tạo 4 TGW VPC Attachments
1. Menu bên trái chọn **Transit gateway attachments** -> Nhấp **Create transit gateway attachment**.
2. **Attachment 1 (Edge VPC):**
   - **Name tag:** `fabric-tgw-att-edge`
   - **Transit gateway ID:** Chọn `fabric-tgw`
   - **Attachment type:** `VPC`
   - **VPC ID:** Chọn `fabric-edge-vpc`
   - **Subnet IDs:** Chọn đúng 2 subnets TGW (`fabric-edge-tgw-1a` và `fabric-edge-tgw-1b`).
   - Nhấp **Create transit gateway attachment**.
3. **Attachment 2 (Core VPC):**
   - **Name tag:** `fabric-tgw-att-core` -> Chọn VPC `fabric-core-vpc` -> Chọn 2 subnets TGW Core (`1a` và `1b`).
4. **Attachment 3 (Inspection VPC - BẮT BUỘC BẬT APPLIANCE MODE):**
   - **Name tag:** `fabric-tgw-att-inspection`
   - **Transit gateway ID:** Chọn `fabric-tgw`
   - **VPC ID:** Chọn `fabric-inspection-vpc`
   - **Subnet IDs:** Chọn đúng 2 subnets TGW Inspection (`fabric-inspection-tgw-1a` và `fabric-inspection-tgw-1b`).
   - **Appliance Mode support:** **TÍCH CHỌN `Enable`** (Đảm bảo flow đối xứng cho GWLB).
   - Nhấp **Create transit gateway attachment**.
5. **Attachment 4 (Egress VPC):**
   - **Name tag:** `fabric-tgw-att-egress` -> Chọn VPC `fabric-egress-vpc` -> Chọn 2 subnets TGW Egress (`1a` và `1b`).

---

### Bước 3: Gắn Kết (Associate) Từng Attachment Vào Route Table Tương Ứng
1. Vào **Transit gateway route tables** -> Chọn `fabric-tgw-rt-edge`.
2. Mở tab **Associations** ở bảng chi tiết bên dưới -> Nhấp **Create association**.
3. Chọn Attachment: `fabric-tgw-att-edge` -> Nhấp **Create association**.
4. Lặp lại tương tự cho:
   - `fabric-tgw-rt-core` <---> `fabric-tgw-att-core`
   - `fabric-tgw-rt-inspection` <---> `fabric-tgw-att-inspection`
   - `fabric-tgw-rt-egress` <---> `fabric-tgw-att-egress`

---

### Bước 4: Tạo Static Routes Trên Các TGW Route Tables
1. **Tại `fabric-tgw-rt-edge` (Tab Routes -> Create static route):**
   - CIDR `10.50.0.0/16` -> Chọn Attachment `fabric-tgw-att-inspection`.
   - CIDR `0.0.0.0/0` -> Chọn Attachment `fabric-tgw-att-egress`.
2. **Tại `fabric-tgw-rt-core`:**
   - CIDR `10.40.0.0/16` -> Chọn Attachment `fabric-tgw-att-inspection`.
   - CIDR `0.0.0.0/0` -> Chọn Attachment `fabric-tgw-att-egress`.
3. **Tại `fabric-tgw-rt-inspection`:**
   - CIDR `10.40.0.0/16` -> Chọn Attachment `fabric-tgw-att-edge`.
   - CIDR `10.50.0.0/16` -> Chọn Attachment `fabric-tgw-att-core`.
4. **Tại `fabric-tgw-rt-egress`:**
   - CIDR `10.40.0.0/16` -> Chọn Attachment `fabric-tgw-att-edge`.
   - CIDR `10.50.0.0/16` -> Chọn Attachment `fabric-tgw-att-core`.
5. **Tại `fabric-tgw-rt-dev`:**
   - CIDR `10.40.0.0/16` -> Chọn `Blackhole`.
   - CIDR `10.50.0.0/16` -> Chọn `Blackhole`.

---

## 3. Xác Minh (Verification)

Kiểm tra Appliance Mode trên Inspection Attachment:
```bash
aws ec2 describe-transit-gateway-vpc-attachments \
  --region ap-southeast-1 \
  --filters "Name=tag:Name,Values=fabric-tgw-att-inspection" \
  --query 'TransitGatewayVpcAttachments[0].Options.ApplianceModeSupport' \
  --output text
```
> Kết quả: `enable`

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] 5 TGW Route Tables và 4 Attachments được cấu hình chính xác.
- [ ] `ApplianceModeSupport` của Inspection Attachment là `enable`.
- [ ] Các static routes được tạo đầy đủ theo đúng thiết kế Hop-by-Hop.
