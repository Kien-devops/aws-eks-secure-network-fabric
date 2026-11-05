# 01.03 — Ma Trận Định Tuyến TGW & Bảng Đường Đi Từng Chặng (Hop-by-Hop Tables)

> **Trạng thái:** Tài liệu thiết kế định tuyến chi tiết (Routing Design).  
> **Áp dụng cho:** Cấu hình 5 bảng định tuyến TGW và các bảng định tuyến Subnet trong 4 VPCs.

---

## 1. Ma Trận Miền Định Tuyến TGW (TGW Route Domains)

Transit Gateway đóng vai trò làm Router trung tâm ảo kết nối 4 VPCs, nhưng được cô lập chặt chẽ thông qua 5 Bảng định tuyến riêng biệt:

```text
[Edge VPC Attachment]       --> Associated with: fabric-tgw-rt-edge
[Core VPC Attachment]       --> Associated with: fabric-tgw-rt-core
[Inspection VPC Attachment] --> Associated with: fabric-tgw-rt-inspection
[Egress VPC Attachment]     --> Associated with: fabric-tgw-rt-egress
[Dev VPC Attachment (Opt)]  --> Associated with: fabric-tgw-rt-dev
```

### Bảng Cấu Hình Routes Trên Từng TGW Route Table
| TGW Route Table | Tuyến Đường (Route Destination) | Target (Attachment) | Giải Thích Kỹ Thuật |
|---|---|---|---|
| **`fabric-tgw-rt-edge`** | `10.50.0.0/16` (Core VPC) | Inspection VPC Attachment | Bắt buộc mọi traffic gửi sang Core phải đi vào Inspection VPC để kiểm tra |
| | `0.0.0.0/0` (Internet) | Egress VPC Attachment | Mọi traffic đi ra ngoài Internet phải chuyển tiếp tới Egress VPC |
| **`fabric-tgw-rt-core`** | `10.40.0.0/16` (Edge VPC) | Inspection VPC Attachment | Bắt buộc mọi traffic phản hồi hoặc gọi Edge phải qua Inspection VPC |
| | `0.0.0.0/0` (Internet) | Egress VPC Attachment | Mọi traffic ra Internet của Core phải chuyển tiếp tới Egress VPC |
| **`fabric-tgw-rt-inspection`**| `10.40.0.0/16` (Edge VPC) | Edge VPC Attachment | Trả traffic hợp lệ sau khi Suricata kiểm tra về Edge VPC |
| | `10.50.0.0/16` (Core VPC) | Core VPC Attachment | Trả traffic hợp lệ sau khi Suricata kiểm tra về Core VPC |
| **`fabric-tgw-rt-egress`** | `10.40.0.0/16` (Edge VPC) | Edge VPC Attachment | Định tuyến gói tin phản hồi từ Internet về lại Edge VPC |
| | `10.50.0.0/16` (Core VPC) | Core VPC Attachment | Định tuyến gói tin phản hồi từ Internet về lại Core VPC |
| **`fabric-tgw-rt-dev`** | `10.40.0.0/16` | `blackhole` | Chặn đứng hoàn toàn traffic giữa Dev và Edge Prod |
| | `10.50.0.0/16` | `blackhole` | Chặn đứng hoàn toàn traffic giữa Dev và Core Prod |

---

## 2. Bảng Phân Tích Đường Đi Từng Chặng (Hop-by-Hop Packet Table)

### Kịch Bản 1: Frontend (Edge) gọi Order Service (Core) qua Cổng 443

| Chặng (Hop) | Thành Phần Xử Lý | Vị Trí (Location) | Thao Tác Của Thiết Bị Mạng |
|---|---|---|---|
| **Hop 1** | Frontend Pod | Edge EKS (`10.40.10.15`) | Gửi gói tin TCP SYN tới IP của Core NLB (`10.50.20.100:443`). |
| **Hop 2** | Edge Node Route Table | Edge VPC Private Subnet | Khớp route `10.50.0.0/16` -> Chuyển tiếp tới TGW Attachment ENI (`10.40.250.x`). |
| **Hop 3** | Transit Gateway | `fabric-tgw-rt-edge` | Khớp route `10.50.0.0/16` -> Chuyển sang Inspection VPC Attachment. |
| **Hop 4** | Inspection TGW Subnet | Inspection VPC (`10.70.0.x`) | Do TGW Attachment có cờ `ApplianceMode=enable`, TGW giữ nguyên flow tại AZ ban đầu (ví dụ `1a`). Tra bảng route Subnet: `10.50.0.0/16` -> trỏ sang `gwlbe-1a`. |
| **Hop 5** | GWLB Endpoint (GWLBe) | Inspection VPC (`10.70.1.x`) | Đóng gói gói tin vào GENEVE Header (UDP 6081) -> Gửi tới Gateway Load Balancer. |
| **Hop 6** | Gateway Load Balancer | Inspection VPC | Chuyển tiếp gói tin GENEVE tới Suricata EC2 Instance AZ-a (`10.70.10.x`). |
| **Hop 7** | Suricata Engine | Suricata EC2 (`geneve0`) | Giải mã gói tin, kiểm tra signature, không có dấu hiệu bất thường -> Gửi trả lại GWLB qua GENEVE. |
| **Hop 8** | GWLBe Subnet Route Table| Inspection VPC (`10.70.1.x`) | Khớp route `10.50.0.0/16` -> Chuyển tiếp tới Inspection TGW Attachment ENI. |
| **Hop 9** | Transit Gateway | `fabric-tgw-rt-inspection` | Khớp route `10.50.0.0/16` -> Chuyển tiếp sang Core VPC Attachment. |
| **Hop 10** | Core Private Route Table | Core VPC | Chuyển tiếp gói tin tới Core Internal NLB (`10.50.20.100`) -> Chuyển tới Order Service Pod. |

---

## 3. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Mọi bước nhảy (Hops) đều có thiết bị tiếp nhận rõ ràng và cấu hình định tuyến tương ứng.
- [ ] Không có hiện tượng gói tin bị quay vòng (Loop) giữa Inspection và TGW.

