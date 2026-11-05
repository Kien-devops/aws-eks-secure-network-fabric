# 02.02 — Khởi Tạo AWS Transit Gateway & Tắt Tự Động Định Tuyến Mặc Định

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Khởi tạo bộ định tuyến trung tâm Transit Gateway (`fabric-tgw`) với các thiết lập bảo mật cô lập.

---

## 1. Mục Tiêu Kỹ Thuật

- Khởi tạo **AWS Transit Gateway** (`fabric-tgw`) tại Region Singapore (`ap-southeast-1`).
- **Tắt hoàn toàn:**
  - `Default route table association` (Không tự động gán attachment vào route table mặc định).
  - `Default route table propagation` (Không tự động quảng bá route vào route table mặc định).
  - `Auto accept shared attachments` (Không tự động chấp nhận attachment từ tài khoản khác).
- Cấu hình Autonomous System Number (ASN) riêng tư: `64512`.

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Mở Menu Transit Gateways
1. Tại giao diện **VPC Console** (`ap-southeast-1`), cuộn thanh menu bên trái xuống nhóm **Transit Gateways**.
2. Nhấp vào **Transit gateways** -> Nhấp nút cam **Create transit gateway**.

### Bước 2: Cấu Hình Tham Số Transit Gateway
1. **Name tag:** Nhập `fabric-tgw`.
2. **Description:** Nhập `Central transit gateway with isolated route domains for EKS network fabric`.
3. **Amazon side Autonomous System Number (ASN):** Nhập `64512`.
4. **Cấu hình tùy chọn bảo mật định tuyến (CỰC KỲ QUAN TRỌNG):**
   - **DNS support:** Tích chọn `Enable`.
   - **VPN ECMP support:** Tích chọn `Enable`.
   - **Default route table association:** **BỎ TÍCH** (`Disable`).
   - **Default route table propagation:** **BỎ TÍCH** (`Disable`).
   - **Auto accept shared attachments:** **BỎ TÍCH** (`Disable`).
   - **Multicast support:** Bỏ chọn (`Disable`).
5. **Tags:**
   - `Name` = `fabric-tgw`
   - `Project` = `aws-eks-secure-network-fabric`
   - `Environment` = `dev`
6. Nhấp nút cam **Create transit gateway**.

---

## 3. Xác Minh (Verification)

Chạy lệnh kiểm tra cấu hình Transit Gateway qua AWS CLI:
```bash
aws ec2 describe-transit-gateways \
  --region ap-southeast-1 \
  --filters "Name=tag:Name,Values=fabric-tgw" \
  --query 'TransitGateways[0].{Id:TransitGatewayId,State:State,ASN:Options.AmazonSideAsn,DefaultAssoc:Options.DefaultRouteTableAssociation,DefaultProp:Options.DefaultRouteTablePropagation}' \
  --output table
```

> **Kết quả mong đợi:**
> - `State`: `available`
> - `DefaultAssoc`: `disable`
> - `DefaultProp`: `disable`

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Transit Gateway `fabric-tgw` chuyển sang trạng thái `available`.
- [ ] Tính năng Default Route Table Association và Propagation đều ở trạng thái `disable`.
