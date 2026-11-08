# 11.01 — Thu Thập Bằng Chứng Kỹ Thuật Runtime Kèm Dấu Thời Gian (Timestamp)

> **Mã bài lab:** `11.01`
> **Trạng thái:** `RUNTIME_PASS`
> **Thời gian dự kiến:** 40 phút
> **Chi phí ước tính:** $0.00 USD (Read-Only API Calls)
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)

---

## 1. Mục Tiêu (Objective)

Đặc tả quy chuẩn và phương thức tự động thu thập trích xuất bằng chứng kỹ thuật runtime từ AWS Cloud API và Kubernetes API. Đảm bảo 100% dữ liệu telemetry, trạng thái routing, cấu hình firewall và log kiểm thử đều có dấu thời gian ISO 8601 UTC theo nguyên tắc Zero Fake Data.

---

## 2. Tài Nguyên (Resources)

| Tên Tập Tin Bằng Chứng | Loại Dữ Liệu | Nguồn Trích Xuất (AWS API / K8s) | Đường Dẫn Lưu Trữ |
| :--- | :--- | :--- | :--- |
| `vpcs.json` | JSON Telemetry | `ec2:DescribeVpcs` | `evidence/01-network-topology/vpcs.json` |
| `subnets.json` | JSON Telemetry | `ec2:DescribeSubnets` | `evidence/01-network-topology/subnets.json` |
| `tgw-route-tables.json` | JSON Telemetry | `ec2:DescribeTransitGatewayRouteTables` | `evidence/01-network-topology/tgw-route-tables.json` |
| `gwlb-target-health.json` | JSON Telemetry | `elbv2:DescribeTargetHealth` | `evidence/02-gwlb-inspection/gwlb-target-health.json` |
| `nfw-status.json` | JSON Telemetry | `network-firewall:DescribeFirewall` | `evidence/03-egress-firewall/nfw-status.json` |
| `eks-clusters.json` | JSON Telemetry | `eks:DescribeCluster` | `evidence/01-network-topology/eks-clusters.json` |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `evidence-*` | Quy chuẩn định danh toàn dự án |
| `Project` | `aws-eks-secure-network-fabric` | Quy chuẩn định danh toàn dự án |
| `Environment` | `prod` | Phân vùng môi trường đối soát |
| `ManagedBy` | `manual` | Quản lý quy trình thu thập thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Quy Chuẩn Dấu Thời Gian & Cấu Trúc Bằng Chứng
* **Chuẩn thời gian:** ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`), ví dụ: `2026-11-08T16:00:00Z`.
* **Cấu trúc JSON Root:** Mọi file bằng chứng JSON phải chứa trường root `Timestamp` và trường payload tương ứng:
  ```json
  {
    "Timestamp": "2026-11-08T16:00:00Z",
    "Data": []
  }
  ```

### 4.2 Lệnh Trích Xuất Runtime CLI
1. **Hạ tầng VPCs & Subnets:**
   ```bash
   aws ec2 describe-vpcs --region ap-southeast-1 \
     --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
     --query "{Timestamp: '$(date -u +%Y-%m-%dT%H:%M:%SZ)', Vpcs: Vpcs[*].{VpcId:VpcId,Cidr:CidrBlock,Name:Tags[?Key=='Name'].Value | [0]}}" \
     > evidence/01-network-topology/vpcs.json
   ```
2. **GWLB Target Health:**
   ```bash
   aws elbv2 describe-target-health --region ap-southeast-1 \
     --target-group-arn "arn:aws:elasticloadbalancing:ap-southeast-1:123456789012:targetgroup/fabric-suricata-tg/1234567890abcdef" \
     --query "{Timestamp: '$(date -u +%Y-%m-%dT%H:%M:%SZ)', Targets: TargetHealthDescriptions[*].{Id:Target.Id,Port:Target.Port,State:TargetHealth.State}}" \
     > evidence/02-gwlb-inspection/gwlb-target-health.json
   ```
3. **AWS Network Firewall Status:**
   ```bash
   aws network-firewall describe-firewall --region ap-southeast-1 \
     --firewall-name "fabric-egress-nfw" \
     --query "{Timestamp: '$(date -u +%Y-%m-%dT%H:%M:%SZ)', Status: FirewallStatus.Status, Endpoints: FirewallStatus.SyncStates}" \
     > evidence/03-egress-firewall/nfw-status.json
   ```

---

## 5. Phụ Thuộc (Dependencies)

* Toàn bộ tài nguyên hạ tầng từ Module 00 đến Module 10 đã được khởi tạo hoặc cấu hình.
* Tài khoản AWS IAM có quyền Read-Only: `ec2:Describe*`, `elasticloadbalancing:Describe*`, `network-firewall:Describe*`, `eks:Describe*`, `logs:GetQueryResults`.

---

## 6. Kiểm Tra Đạt (Verification)

| Hạng Mục | Lệnh Kiểm Tra / Metric | Kỳ Vọng Đạt |
| :--- | :--- | :--- |
| **Tính Hợp Lệ JSON** | `jq . evidence/**/*.json` | Toàn bộ tệp parse cú pháp JSON thành công không lỗi |
| **Dấu Thời Gian ISO 8601** | `jq -r '.Timestamp' evidence/**/*.json` | 100% tệp có nhãn ISO 8601 UTC hợp lệ |
| **Tính Hiện Hữu Tài Nguyên** | So sánh Resource IDs trong evidence với AWS Console | IDs (VPC, Subnet, TGW, GWLB, NFW) trùng khớp hoàn toàn với thực tế |
| **Zero Fake Data** | Kiểm tra chuỗi dữ liệu trong file | Không chứa dữ liệu placeholder, mock hay giả lập |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

> [!NOTE]
> Hoạt động thu thập bằng chứng là thao tác chỉ đọc (Read-Only API Calls), hoàn toàn an toàn và không gây gián đoạn hay phát sinh chi phí hạ tầng.

### Kế Hoạch Làm Sạch (Cleanup Evidence)
Nếu cần thu thập lại từ đầu, thực hiện xóa thư mục cache và khởi tạo lại cấu trúc rỗng:
```bash
rm -rf evidence/01-network-topology/* evidence/02-gwlb-inspection/* evidence/03-egress-firewall/*
```
