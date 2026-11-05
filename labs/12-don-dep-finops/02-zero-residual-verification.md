# 12.02 — Kiểm Kê Tồn Dư Tự Động & Chứng Minh Hóa Đơn Chi Phí Về Đúng $0.00

> **Trạng thái:** Quy trình kiểm toán xác nhận sạch tài nguyên đám mây (Clean Slate Verification).  
> **Áp dụng cho:** Thực thi script kiểm kê tự động xác nhận không còn bất kỳ tài nguyên tính phí ngầm nào còn sót lại.

---

## 1. Mục Tiêu Kỹ Thuật

- Chạy các lệnh kiểm kê qua AWS CLI / MCP trên toàn bộ dịch vụ đã triển khai tại Singapore (`ap-southeast-1`).
- Chứng minh danh sách tài nguyên trả về hoàn toàn rỗng (**Empty List**).
- Xác nhận chi phí phát sinh hàng giờ của tài khoản AWS đã trở về đúng mức **$0.00 USD/hour**.

---

## 2. Kịch Bản Kiểm Kê Tồn Dư Toàn Diện (Zero-Residual Check Script)

Chạy đồng loạt các câu lệnh truy vấn qua AWS CLI:

```bash
echo "=== BẮT ĐẦU KIỂM KÊ TỒN DƯ TÀI NGUYÊN TẠI AP-SOUTHEAST-1 ==="

# 1. Kiểm tra VPCs
echo "[1] Kiểm tra VPCs..."
aws ec2 describe-vpcs \
  --region ap-southeast-1 \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query 'Vpcs[*].VpcId' --output text

# 2. Kiểm tra Transit Gateways
echo "[2] Kiểm tra Transit Gateways..."
aws ec2 describe-transit-gateways \
  --region ap-southeast-1 \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query 'TransitGateways[?State!=`deleted`].TransitGatewayId' --output text

# 3. Kiểm tra Load Balancers (ALB, NLB, GWLB)
echo "[3] Kiểm tra Load Balancers..."
aws elbv2 describe-load-balancers \
  --region ap-southeast-1 \
  --query 'LoadBalancers[?contains(LoadBalancerName, `fabric-`)].LoadBalancerName' --output text

# 4. Kiểm tra NAT Gateways
echo "[4] Kiểm tra NAT Gateways..."
aws ec2 describe-nat-gateways \
  --region ap-southeast-1 \
  --query 'NatGateways[?State!=`deleted`].NatGatewayId' --output text

# 5. Kiểm tra Elastic IPs còn gắn hoặc nhàn rỗi
echo "[5] Kiểm tra Elastic IPs..."
aws ec2 describe-addresses \
  --region ap-southeast-1 \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query 'Addresses[*].PublicIp' --output text

# 6. Kiểm tra AWS Network Firewall
echo "[6] Kiểm tra AWS Network Firewall..."
aws network-firewall list-firewalls \
  --region ap-southeast-1 \
  --query 'Firewalls[?contains(FirewallName, `fabric-`)].FirewallName' --output text

# 7. Kiểm tra EKS Clusters
echo "[7] Kiểm tra EKS Clusters..."
aws eks list-clusters \
  --region ap-southeast-1 \
  --query 'clusters[?contains(@, `fabric-`)]' --output text

# 8. Kiểm tra Aurora Databases & ElastiCache Redis
echo "[8] Kiểm tra Databases & Cache..."
aws rds describe-db-clusters \
  --region ap-southeast-1 \
  --query 'DBClusters[?contains(DBClusterIdentifier, `fabric-`)].DBClusterIdentifier' --output text
aws elasticache describe-cache-clusters \
  --region ap-southeast-1 \
  --query 'CacheClusters[?contains(CacheClusterId, `fabric-`)].CacheClusterId' --output text

echo "=== KIỂM KÊ HOÀN TẤT: TOÀN BỘ DANH SÁCH RỖNG - ĐẠT CHUẨN $0.00! ==="
```

---

## 3. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Không còn bất kỳ tài nguyên nào mang tag `fabric-*` hoặc thuộc Project 6 tồn tại trên AWS.
- [ ] Hóa đơn chi phí tồn dư xác nhận đạt mức tuyệt đối **$0.00 USD**.
