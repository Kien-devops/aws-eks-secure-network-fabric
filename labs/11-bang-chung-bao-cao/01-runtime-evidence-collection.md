# 11.01 — Thu Thập Bằng Chứng Kỹ Thuật Runtime Kèm Dấu Thời Gian (Timestamp)

> **Trạng thái:** Hướng dẫn quy chuẩn thu thập bằng chứng kỹ thuật chuẩn SRE.  
> **Áp dụng cho:** Tổ chức lưu trữ bằng chứng thực nghiệm của Project 6, phục vụ nghiệm thu 9 PASS criteria.

---

## 1. Mục Tiêu Kỹ Thuật

- Thiết lập cấu trúc thư mục lưu trữ bằng chứng chuẩn: `evidence/`.
- Thu thập raw outputs có gắn nhãn thời gian thực tế (**ISO 8601 Timestamp**).
- Đảm bảo tính trung thực (Zero Fake Data), không sử dụng bảng mô phỏng hoặc tài liệu lý thuyết.

---

## 2. Cấu Trúc Thư Mục Evidence

```text
evidence/
├── 01-network-topology/
│   ├── vpc-subnets.json
│   ├── tgw-attachments-routes.json
│   └── reachability-analyzer-result.json
├── 02-gwlb-inspection/
│   ├── tcpdump-symmetric-az-a.log
│   ├── suricata-eve-alerts.json
│   └── gwlb-target-health.json
├── 03-egress-firewall/
│   ├── nfw-domain-allowlist-test.log
│   └── nfw-block-unauthorized.log
├── 04-gameday/
│   ├── gameday-asymmetric-routing-drop.log
│   ├── gameday-appliance-failover-timeline.csv
│   └── gameday-route-leak-detection.log
└── 05-reports/
    ├── INCIDENT-POST-MORTEM.md
    └── FINOPS-COST-SUMMARY.md
```

---

## 3. Lệnh Thu Thập Mẫu

```bash
# Thu thập trạng thái VPC & Subnets kèm timestamp
echo "=== Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ") ===" > evidence/01-network-topology/vpc-subnets.json
aws ec2 describe-vpcs --region ap-southeast-1 --output json >> evidence/01-network-topology/vpc-subnets.json

# Thu thập log Suricata EVE
aws logs filter-log-events \
  --log-group-name /aws/suricata/fabric-inspection-eve \
  --region ap-southeast-1 \
  --limit 50 \
  --output json > evidence/02-gwlb-inspection/suricata-eve-alerts.json
```

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] 100% tệp bằng chứng có timestamp xác thực thời điểm chạy lệnh.
- [ ] Dữ liệu định dạng chuẩn JSON, CSV hoặc Log text hợp lệ.
