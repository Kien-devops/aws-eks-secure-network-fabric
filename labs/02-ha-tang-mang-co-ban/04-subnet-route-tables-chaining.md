# 02.04 — Cấu Hình Bảng Định Tuyến Subnet & Điều Phối Chuỗi Dịch Vụ (Service Chaining)

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Cấu hình các bảng định tuyến ở cấp độ Subnet trong 4 VPCs để định hướng luồng lưu lượng chính xác vào TGW, GWLBe và NAT Gateways.

---

## 1. Mục Tiêu Kỹ Thuật

- Cấu hình các bảng định tuyến VPC (VPC Route Tables) cho từng lớp Subnet trong cả 4 VPCs:
  - **Edge VPC:** Route Subnet Private trỏ `10.50.0.0/16` và `0.0.0.0/0` về TGW.
  - **Core VPC:** Route Subnet Private trỏ `10.40.0.0/16` và `0.0.0.0/0` về TGW.
  - **Inspection VPC:** Định hướng lưu lượng từ TGW vào GWLBe, và từ GWLBe quay ngược lại TGW.
  - **Egress VPC:** Định hướng lưu lượng từ TGW vào Network Firewall, và từ Firewall sang NAT Gateway.

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Cấu Hình Route Tables Trong Edge VPC
1. Mở **Route tables** -> Nhấp **Create route table**:
   - **Name:** `fabric-edge-private-rt`
   - **VPC:** `fabric-edge-vpc`
2. Gắn kết Subnets: Gắn vào `fabric-edge-node-1a` và `fabric-edge-node-1b`.
3. Thêm Routes (Tab Routes -> Edit routes):
   - `10.50.0.0/16` -> Target: `Transit Gateway` (`fabric-tgw`).
   - `0.0.0.0/0` -> Target: `Transit Gateway` (`fabric-tgw`).

---

### Bước 2: Cấu Hình Route Tables Trong Core VPC
1. Tạo Route table `fabric-core-private-rt` trong `fabric-core-vpc`.
2. Gắn kết vào `fabric-core-node-1a`, `fabric-core-node-1b`, `fabric-core-data-1a`, `fabric-core-data-1b`.
3. Thêm Routes:
   - `10.40.0.0/16` -> Target: `Transit Gateway` (`fabric-tgw`).
   - `0.0.0.0/0` -> Target: `Transit Gateway` (`fabric-tgw`).

---

### Bước 3: Cấu Hình Route Chaining Trong Inspection VPC
Tách riêng 2 bảng định tuyến cho Subnet TGW và Subnet GWLBe:
1. **Bảng định tuyến Subnet TGW (`fabric-inspection-tgw-rt-1a`):**
   - Gắn kết với `fabric-inspection-tgw-1a`.
   - Route `10.50.0.0/16` -> Trỏ tới `gwlbe-1a` (sẽ điền ID sau khi tạo GWLB ở Module 05).
   - Route `10.40.0.0/16` -> Trỏ tới `gwlbe-1a`.
2. **Bảng định tuyến Subnet GWLBe (`fabric-inspection-gwlbe-rt`):**
   - Gắn kết với `fabric-inspection-gwlbe-1a` và `1b`.
   - Route `10.50.0.0/16` -> Trỏ tới `Transit Gateway` (`fabric-tgw`).
   - Route `10.40.0.0/16` -> Trỏ tới `Transit Gateway` (`fabric-tgw`).

---

### Bước 4: Cấu Hình Route Tables Trong Egress VPC
1. **Bảng định tuyến Subnet Public (`fabric-egress-public-rt`):**
   - Gắn kết với `fabric-egress-public-1a` và `1b`.
   - Route `0.0.0.0/0` -> Trỏ tới `Internet Gateway` (`fabric-egress-igw`).
   - Route `10.40.0.0/16` -> Trỏ tới `Transit Gateway` (`fabric-tgw`) (Đường về cho NAT).
   - Route `10.50.0.0/16` -> Trỏ tới `Transit Gateway` (`fabric-tgw`) (Đường về cho NAT).
2. **Bảng định tuyến Subnet TGW (`fabric-egress-tgw-rt`):**
   - Gắn kết với `fabric-egress-tgw-1a` và `1b`.
   - Route `0.0.0.0/0` -> Trỏ tới `Network Firewall Endpoint ID` (sẽ điền sau ở Module 06).

---

## 3. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Bảng định tuyến của các Subnet Private trong Edge và Core đều trỏ đúng đích sang TGW.
- [ ] Bảng định tuyến Public trong Egress VPC có đủ đường về cho dải IP của Edge và Core.

