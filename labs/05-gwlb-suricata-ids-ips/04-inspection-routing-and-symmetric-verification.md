# 05.04 — Đặc Tả Cắt Chuyển Định Tuyến East-West Qua GWLB & Xác Minh Luồng Đối Xứng

> **Mã bài lab:** `05.04`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore) — AZs: `ap-southeast-1a`, `ap-southeast-1b`
> **File bằng chứng:** `evidence/05-gwlb/04-symmetric-tcpdump-trace.log`

---

## 1. Mục Tiêu (Objective)

Đặc tả các bảng định tuyến cắt chuyển toàn bộ lưu lượng East-West giữa Edge EKS và Core EKS qua Gateway Load Balancer trong Inspection VPC và xác minh tính đối xứng hai chiều của phiên TCP (Symmetric Flow) trên cụm Suricata IDS/IPS.

---

## 2. Tài Nguyên (Resources)

| Tên Tài Nguyên | Loại Resource | Vị Trí / Bảng Định Tuyến | Runtime ID / ARN |
| :--- | :--- | :--- | :--- |
| `fabric-insp-tgw-rt-1a` | `AWS::EC2::RouteTable` | Inspection VPC (`10.70.0.0/28`) | Gắn vào Subnet `fabric-insp-tgw-1a` |
| `fabric-insp-tgw-rt-1b` | `AWS::EC2::RouteTable` | Inspection VPC (`10.70.0.16/28`) | Gắn vào Subnet `fabric-insp-tgw-1b` |
| `fabric-insp-gwlbe-rt` | `AWS::EC2::RouteTable` | Inspection VPC (`10.70.1.0/28`, `10.70.1.16/28`) | Gắn vào Subnets GWLBe `1a`, `1b` |
| `fabric-tgw-edge-rt` | `AWS::EC2::TransitGatewayRouteTable` | Transit Gateway | Chuyển tiếp sang Inspection Attachment |
| `fabric-tgw-core-rt` | `AWS::EC2::TransitGatewayRouteTable` | Transit Gateway | Chuyển tiếp sang Inspection Attachment |

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-insp-*-rt` | Bảng định tuyến VPC và TGW Route Tables |
| `Project` | `aws-eks-secure-network-fabric` | Bảng định tuyến VPC và TGW Route Tables |
| `Environment` | `prod` | Bảng định tuyến VPC và TGW Route Tables |
| `RoutingDomain` | `east-west-inspection` | Phân đoạn lưu lượng kiểm tra |
| `ManagedBy` | `manual` | Quản trị chính sách định tuyến |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Bảng Định Tuyến Subnet Trong Inspection VPC

| Bảng Định Tuyến | Nguồn / Subnet Gắn | CIDR Đích | Next Hop Target | AZ | Mục Đích Thiết Kế |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **`fabric-insp-tgw-rt-1a`** | `fabric-insp-tgw-1a` | `10.40.0.0/16`<br>`10.50.0.0/16` | `fabric-gwlbe-1a` (`vpce-0f16354ca5bb55c14`) | `1a` | Ép toàn bộ traffic vào từ TGW AZ-a sang GWLBe AZ-a. |
| **`fabric-insp-tgw-rt-1b`** | `fabric-insp-tgw-1b` | `10.40.0.0/16`<br>`10.50.0.0/16` | `fabric-gwlbe-1b` (`vpce-0b48242bff7b44479`) | `1b` | Ép toàn bộ traffic vào từ TGW AZ-b sang GWLBe AZ-b. |
| **`fabric-insp-gwlbe-rt`** | `fabric-insp-gwlbe-1a/b` | `10.40.0.0/16`<br>`10.50.0.0/16` | `fabric-tgw` (`tgw-***`) | Cả 2 | Trả ngược gói tin đã kiểm tra về Transit Gateway. |

### 4.2 Cắt Chuyển Định Tuyến Trên Transit Gateway

| TGW Route Table | Tuyến CIDR Đích | Next Hop Attachment | Mô Tả Luồng Mạng |
| :--- | :--- | :--- | :--- |
| **`fabric-tgw-edge-rt`** | `10.50.0.0/16` (Core VPC) | `fabric-insp-tgw-attachment` | Ép traffic từ Edge sang Core phải qua Inspection VPC. |
| **`fabric-tgw-core-rt`** | `10.40.0.0/16` (Edge VPC) | `fabric-insp-tgw-attachment` | Ép traffic phản hồi từ Core về Edge phải qua Inspection VPC. |

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `05.01`, `05.02`, `05.03`: Cụm Suricata, GWLB và 2 Zonal GWLB Endpoints phải hoạt động.
- Phụ thuộc vào `02.03`: Cờ `ApplianceModeSupport: enable` phải bật trên `fabric-insp-tgw-attachment`.
- Phụ thuộc vào `04.04`: Pods `edge-frontend` và `core-service` sẵn sàng để kiểm thử kết nối.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **TGW Active Routes** | `aws ec2 search-transit-gateway-routes --transit-gateway-route-table-id <EdgeRTId>` | Route `10.50.0.0/16` trỏ tới `fabric-insp-tgw-attachment` (`state: active`). |
| **Kết nối East-West** | `kubectl exec -n fabric-apps <edge-pod> -- wget -S -O- https://core.fabric.internal/healthz` | Trả về `HTTP/1.1 200 OK` (kèm dữ liệu trạng thái database & redis UP). |
| **Xác minh Đối Xứng (Symmetry)** | Kiểm tra flow cache trên Suricata Appliance | Ghi nhận cả hai chiều Request và Response của cùng 1 phiên TCP trên cùng 1 appliance (`fabric-suricata-1a`). |
| **Nhật ký Suricata** | Đọc `/var/log/suricata/eve.json` | Xuất hiện bản ghi flow và alert tương ứng của gói tin kiểm tra. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo lỗi định tuyến bất đối xứng (Asymmetric Drop):** Nếu TGW Subnet AZ-a trỏ sang GWLBe AZ-b, gói tin đi và về sẽ bị lệch appliance, dẫn đến TCP RST và rớt kết nối hoàn toàn.
- **Quy trình Rollback:**
  ```bash
  # Khôi phục route trực tiếp trên TGW (Bỏ qua inspection trong trường hợp khẩn cấp)
  aws ec2 replace-transit-gateway-route --region ap-southeast-1 \
    --transit-gateway-route-table-id <EdgeTgwRtId> \
    --destination-cidr-block 10.50.0.0/16 \
    --transit-gateway-attachment-id <CoreAttachmentId>

  aws ec2 replace-transit-gateway-route --region ap-southeast-1 \
    --transit-gateway-route-table-id <CoreTgwRtId> \
    --destination-cidr-block 10.40.0.0/16 \
    --transit-gateway-attachment-id <EdgeAttachmentId>
  ```
