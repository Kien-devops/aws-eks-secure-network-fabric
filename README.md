# AWS EKS Secure Network Fabric (Platform & Infrastructure)

Centralized security and advanced multi-VPC networking architecture for EKS workloads.

## Key Capabilities
- **Transit Gateway (TGW) Segmentation:** Isolated route domains (Edge, Core, Inspection, Egress, Dev blackhole).
- **East-West Inspection:** Centralized Gateway Load Balancer (GWLB) with GENEVE tunnel passing traffic through Suricata IDS/IPS appliances.
- **Symmetric Routing:** Appliance mode enabled on Inspection TGW attachment to guarantee same-AZ inspection path.
- **Centralized Egress:** AWS Network Firewall with Suricata stateful domain rules and AZ-isolated NAT Gateways.
- **Dual Private EKS Clusters:** Edge EKS (Frontend, Auth) and Core EKS (Order, Inventory, Payment).

## Structure
- \	erraform/\: Modular Infrastructure as Code (VPCs, TGW, EKS, GWLB, Network Firewall)
- \docs/\: Network flow diagrams, hop tables, CIDR allocation, threat model
- \evidence/\: GameDay execution logs, Suricata EVE alerts, Reachability Analyzer results
