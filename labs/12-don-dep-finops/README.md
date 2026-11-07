# Module 12: Cleanup Theo Phụ Thuộc Và Kiểm Kê Chi Phí

**Thao tác hủy dữ liệu cần được phép trước khi chạy.** Chỉ xử lý IDs thuộc dự án, lưu evidence/backups và quyết định retention trước khi xóa.

1. [12.01 Reverse teardown](01-reverse-dependency-teardown.md): dừng GitOps/pipeline reconcile; xóa Ingress/LoadBalancer Services khi controllers còn chạy; chờ LB/ENIs giải phóng, xử lý PVC/PV và DNS; sau đó mới xóa nodes/clusters, database/cache/queues, firewall/GWLBe/endpoint service/GWLB/appliances, TGW và network base.
2. [12.02 Residual verification](02-zero-residual-verification.md): walkthrough Console từng dịch vụ, gồm EBS/snapshots, logs/ECR/S3, secrets/KMS, DNS/IAM và billing. Ghi retained/pending với owner, expiry và chi phí.

Không yêu cầu toàn tài khoản sạch hoặc chỉ còn Default VPC. Không force-delete managed ENIs. Không giả định Terraform/pipeline đã có để dựng lại; dữ liệu xóa chỉ phục hồi được khi có backup và khóa giải mã còn dùng được.

Nghiệm thu dựa inventory IDs, timestamps, raw outputs, ngoại lệ retention và khoảng usage billing đã cập nhật. Billing có độ trễ; cleanup không xóa phí đã phát sinh, không bảo đảm chi phí tương lai chính xác $0.
