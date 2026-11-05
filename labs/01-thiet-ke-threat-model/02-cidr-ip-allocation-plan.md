# 01.02 — Kế Hoạch Phân Bổ Dải Mạng CIDR & Địa Chỉ IP Không Chồng Lấn

> **Trạng thái:** Tài liệu thiết kế dải mạng (IP Plan).  
> **Áp dụng cho:** Toàn bộ 4 VPCs và các Subnet chuyên dụng trong Region Singapore (`ap-southeast-1`).

---

## 1. Nguyên Tắc Phân Bổ Không Chồng Lấn (Non-Overlapping IP Scheme)

- **Nguyên tắc cốt lõi:**
  - 4 VPCs sử dụng 4 dải mạng `/16` hoàn toàn tách biệt:
    - Edge VPC: `10.40.0.0/16`
    - Core VPC: `10.50.0.0/16`
    - Inspection VPC: `10.70.0.0/16`
    - Egress VPC: `10.80.0.0/16`
  - Đảm bảo đủ không gian địa chỉ cho EKS Pods (AWS VPC CNI cấp IP thực tế từ Subnet cho từng Pod).
  - Tách riêng biệt từng lớp Subnet theo chức năng và theo từng Availability Zone (`ap-southeast-1a` và `ap-southeast-1b`).

---

## 2. Bảng Phân Bổ Chi Tiết Toàn Bộ Subnets

### 1. VPC Edge EKS (`10.40.0.0/16`)
| Tên Subnet | CIDR Block | Availability Zone | Số Lượng IPs Khả Dụng | Mục Đích Sử Dụng |
|---|---|---|---|---|
| `fabric-edge-public-1a` | `10.40.0.0/24` | `ap-southeast-1a` | 251 | Public Ingress ALB Endpoint |
| `fabric-edge-public-1b` | `10.40.1.0/24` | `ap-southeast-1b` | 251 | Public Ingress ALB Endpoint |
| `fabric-edge-node-1a` | `10.40.10.0/22` | `ap-southeast-1a` | 1019 | EKS Worker Nodes & Pods (frontend, auth) |
| `fabric-edge-node-1b` | `10.40.14.0/22` | `ap-southeast-1b` | 1019 | EKS Worker Nodes & Pods (frontend, auth) |
| `fabric-edge-tgw-1a` | `10.40.250.0/28` | `ap-southeast-1a` | 11 | Giao diện TGW Attachment ENI |
| `fabric-edge-tgw-1b` | `10.40.250.16/28` | `ap-southeast-1b` | 11 | Giao diện TGW Attachment ENI |

### 2. VPC Core EKS (`10.50.0.0/16`)
| Tên Subnet | CIDR Block | Availability Zone | Số Lượng IPs Khả Dụng | Mục Đích Sử Dụng |
|---|---|---|---|---|
| `fabric-core-node-1a` | `10.50.10.0/22` | `ap-southeast-1a` | 1019 | EKS Worker Nodes & Pods (order, inv, pay) |
| `fabric-core-node-1b` | `10.50.14.0/22` | `ap-southeast-1b` | 1019 | EKS Worker Nodes & Pods (order, inv, pay) |
| `fabric-core-data-1a` | `10.50.20.0/24` | `ap-southeast-1a` | 251 | Aurora PostgreSQL, ElastiCache Redis |
| `fabric-core-data-1b` | `10.50.21.0/24` | `ap-southeast-1b` | 251 | Aurora Standby, ElastiCache Replica |
| `fabric-core-tgw-1a` | `10.50.250.0/28` | `ap-southeast-1a` | 11 | Giao diện TGW Attachment ENI |
| `fabric-core-tgw-1b` | `10.50.250.16/28` | `ap-southeast-1b` | 11 | Giao diện TGW Attachment ENI |

### 3. VPC Inspection (`10.70.0.0/16`)
| Tên Subnet | CIDR Block | Availability Zone | Số Lượng IPs Khả Dụng | Mục Đích Sử Dụng |
|---|---|---|---|---|
| `fabric-inspection-tgw-1a` | `10.70.0.0/28` | `ap-southeast-1a` | 11 | TGW Attachment ENI (Appliance Mode) |
| `fabric-inspection-tgw-1b` | `10.70.0.16/28` | `ap-southeast-1b` | 11 | TGW Attachment ENI (Appliance Mode) |
| `fabric-inspection-gwlbe-1a`| `10.70.1.0/28` | `ap-southeast-1a` | 11 | Điểm cuối GWLB Endpoint (GWLBe-a) |
| `fabric-inspection-gwlbe-1b`| `10.70.1.16/28` | `ap-southeast-1b` | 11 | Điểm cuối GWLB Endpoint (GWLBe-b) |
| `fabric-inspection-fw-1a` | `10.70.10.0/24` | `ap-southeast-1a` | 251 | Máy chủ Suricata EC2 Instance AZ-a |
| `fabric-inspection-fw-1b` | `10.70.11.0/24` | `ap-southeast-1b` | 251 | Máy chủ Suricata EC2 Instance AZ-b |

### 4. VPC Centralized Egress (`10.80.0.0/16`)
| Tên Subnet | CIDR Block | Availability Zone | Số Lượng IPs Khả Dụng | Mục Đích Sử Dụng |
|---|---|---|---|---|
| `fabric-egress-tgw-1a` | `10.80.0.0/28` | `ap-southeast-1a` | 11 | TGW Attachment ENI |
| `fabric-egress-tgw-1b` | `10.80.0.16/28` | `ap-southeast-1b` | 11 | TGW Attachment ENI |
| `fabric-egress-nfw-1a` | `10.80.1.0/28` | `ap-southeast-1a` | 11 | Điểm cuối AWS Network Firewall Endpoint A |
| `fabric-egress-nfw-1b` | `10.80.1.16/28` | `ap-southeast-1b` | 11 | Điểm cuối AWS Network Firewall Endpoint B |
| `fabric-egress-public-1a` | `10.80.10.0/24` | `ap-southeast-1a` | 251 | NAT Gateway A & Internet Gateway (IGW) |
| `fabric-egress-public-1b` | `10.80.11.0/24` | `ap-southeast-1b` | 251 | NAT Gateway B & Internet Gateway (IGW) |

---

## 3. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Tổng thể 4 VPCs không có bất kỳ dải IP nào chồng chéo.
- [ ] Subnet TGW có kích thước `/28` (chuẩn AWS cho giao diện TGW).
- [ ] Subnet Node có kích thước `/22` đáp ứng hơn 1000 IPs cho Pod scale.

