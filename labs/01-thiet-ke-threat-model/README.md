# Module 01: Thiết Kế Kiến Trúc & Mô Hình Đe Dọa (Threat Model)

## 1. Thứ Tự Phụ Thuộc (Execution Order)

```text
01-stride-threat-analysis.md (Mô hình đe dọa STRIDE & 5 ranh giới bảo mật)
  │
  ▼
02-cidr-ip-allocation-plan.md (Quy hoạch dải mạng RFC 1918 cho 4 VPCs & 28 Subnets)
  │
  ▼
03-tgw-routing-matrix-hop-tables.md (Ma trận định tuyến TGW & Bảng bước nhảy Hop-by-Hop)
```

---

## 2. Danh Mục Tài Nguyên (Resource Inventory)

| Tài Nguyên (Resource) | Loại (Type) | Phạm Vi / Vùng | Mô Tả & Tiêu Chuẩn |
| :--- | :--- | :--- | :--- |
| `STRIDE Matrix` | Security Specification | Toàn hệ thống | Ma trận kiểm soát 6 họ nguy cơ an ninh |
| `fabric-edge-vpc` | VPC (`10.40.0.0/16`) | `ap-southeast-1` | 8 subnets đa vùng, đón nhận Ingress Internet |
| `fabric-core-vpc` | VPC (`10.50.0.0/16`) | `ap-southeast-1` | 8 subnets đa vùng, chứa `core-service`, Aurora DB & Redis |
| `fabric-inspection-vpc` | VPC (`10.70.0.0/16`) | `ap-southeast-1` | 6 subnets đa vùng, phục vụ GWLB & Suricata IDS/IPS |
| `fabric-egress-vpc` | VPC (`10.80.0.0/16`) | `ap-southeast-1` | 6 subnets đa vùng, phục vụ Dual NAT GWs & AWS Network Firewall |
| `fabric-tgw-*` RTs | 4 TGW Route Tables | Global TGW | `edge-rt`, `core-rt`, `inspection-rt`, `egress-rt` |
