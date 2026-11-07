# AWS EKS Secure Network Fabric (Platform & Infrastructure)

Centralized security and advanced multi-VPC networking architecture for EKS workloads.

## Key Capabilities
- **Transit Gateway (TGW) Segmentation:** Isolated route domains (Edge, Core, Inspection, Egress, Dev blackhole).
- **East-West Inspection:** Centralized Gateway Load Balancer (GWLB) with GENEVE tunnel passing traffic through Suricata IDS/IPS appliances.
- **Symmetric Routing:** Inspection appliance mode preserves flow affinity; cross-zone GWLB does not guarantee the appliance shares the source AZ.
- **Centralized Egress:** AWS Network Firewall with Suricata stateful domain rules and AZ-isolated NAT Gateways.
- **Dual Private EKS Clusters:** Edge EKS (Frontend, Auth) and Core EKS (Order, Inventory, Payment).

## Structure
- `spec.md`: target architecture and scope.
- `labs/`: Vietnamese Console walkthroughs, prerequisites, validation and rollback.
- `evidence/`: historical execution records; does not establish current runtime health.
- `scripts/validate-labs.py`: static documentation validation.

Terraform, application source/manifests and CI/CD pipelines are not yet supplied. Capabilities above describe the target; see [lab gates](labs/README.md) before execution. Dev blackhole is an optional extension outside the four-VPC MVP.
