import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { Diagram, group, frame, icon, box, grid, phantom, renderTree } from "drawio-ai-kit";
import { execFileSync as __exec } from "node:child_process";

const d = new Diagram("network");

// Subnet helpers
const pubSubnet = (id, label, children) =>
  group(id, "group_subnet", `Public Subnet · ${label}`, { dir: "col", gap: 10, align: "center" }, children);

const privSubnet = (id, label, children) =>
  group(id, "group_subnet", `Private Subnet · ${label}`, { dir: "col", gap: 10, align: "center" }, children);

// ---------------------------------------------------------------------------
// 1. VPC EDGE EKS (10.40.0.0/16)
// ---------------------------------------------------------------------------
const edgeAzA = group("edge_az_a", "group_availability_zone", "AZ ap-southeast-1a", { dir: "col", gap: 12 }, [
  pubSubnet("edge_pub_a", "10.40.0.0/24 (Ingress)", [
    icon("alb_edge_a", "application_load_balancer", "ALB Ingress (AZ-A)"),
  ]),
  privSubnet("edge_node_a", "10.40.8.0/22 (Nodes)", [
    icon("node_edge_a", "eks", "Edge Node (Frontend)"),
  ]),
  privSubnet("edge_vpce_a", "10.40.20.0/24 (VPCE)", [
    icon("vpce_edge_a", "vpc_privatelink", "VPCE (ECR/Logs/eks-auth)"),
  ]),
  privSubnet("edge_tgw_sub_a", "10.40.250.0/28 (TGW)", [
    icon("tgw_att_edge_a", "transit_gateway_attachment", "TGW Attach ENI 1a"),
  ]),
]);

const edgeAzB = group("edge_az_b", "group_availability_zone", "AZ ap-southeast-1b", { dir: "col", gap: 12 }, [
  pubSubnet("edge_pub_b", "10.40.1.0/24 (Ingress)", [
    icon("alb_edge_b", "application_load_balancer", "ALB Ingress (AZ-B)"),
  ]),
  privSubnet("edge_node_b", "10.40.12.0/22 (Nodes)", [
    icon("node_edge_b", "eks", "Edge Node (Auth-Service)"),
  ]),
  privSubnet("edge_vpce_b", "10.40.21.0/24 (VPCE)", [
    icon("vpce_edge_b", "vpc_privatelink", "VPCE (ECR/Logs/eks-auth)"),
  ]),
  privSubnet("edge_tgw_sub_b", "10.40.250.16/28 (TGW)", [
    icon("tgw_att_edge_b", "transit_gateway_attachment", "TGW Attach ENI 1b"),
  ]),
]);

const edgeVpc = group("edge_vpc", "group_vpc", "Edge VPC (fabric-edge-vpc · 10.40.0.0/16)", { dir: "col", gap: 14, align: "center" }, [
  icon("edge_igw", "internet_gateway", "Internet Gateway (fabric-edge-igw)"),
  phantom("edge_azs", "", { dir: "row", gap: 20, align: "top", header: 0 }, [edgeAzA, edgeAzB]),
]);

// ---------------------------------------------------------------------------
// 2. CENTRALIZED EGRESS VPC (10.80.0.0/16)
// ---------------------------------------------------------------------------
const egressAzA = group("egress_az_a", "group_availability_zone", "AZ ap-southeast-1a", { dir: "col", gap: 12 }, [
  pubSubnet("egress_pub_a", "10.80.10.0/24 (Public)", [
    icon("nat_a", "nat_gateway", "NAT Gateway 1a"),
  ]),
  privSubnet("egress_fw_a", "10.80.1.0/28 (Firewall)", [
    icon("nfw_ep_a", "network_firewall", "Network Firewall EP 1a"),
  ]),
  privSubnet("egress_tgw_sub_a", "10.80.0.0/28 (TGW)", [
    icon("tgw_att_egress_a", "transit_gateway_attachment", "TGW Attach ENI 1a"),
  ]),
]);

const egressAzB = group("egress_az_b", "group_availability_zone", "AZ ap-southeast-1b", { dir: "col", gap: 12 }, [
  pubSubnet("egress_pub_b", "10.80.11.0/24 (Public)", [
    icon("nat_b", "nat_gateway", "NAT Gateway 1b"),
  ]),
  privSubnet("egress_fw_b", "10.80.1.16/28 (Firewall)", [
    icon("nfw_ep_b", "network_firewall", "Network Firewall EP 1b"),
  ]),
  privSubnet("egress_tgw_sub_b", "10.80.0.16/28 (TGW)", [
    icon("tgw_att_egress_b", "transit_gateway_attachment", "TGW Attach ENI 1b"),
  ]),
]);

const egressVpc = group("egress_vpc", "group_vpc", "Centralized Egress VPC (fabric-egress-vpc · 10.80.0.0/16)", { dir: "col", gap: 14, align: "center" }, [
  icon("egress_igw", "internet_gateway", "Internet Gateway (fabric-egress-igw)"),
  phantom("egress_azs", "", { dir: "row", gap: 20, align: "top", header: 0 }, [egressAzA, egressAzB]),
]);

// ---------------------------------------------------------------------------
// 3. CENTRAL TRANSIT GATEWAY HUB (ASN 64512)
// ---------------------------------------------------------------------------
const tgwHub = frame("tgw_box", "AWS Transit Gateway (fabric-tgw · ASN 64512 · Singapore)", { dir: "col", gap: 14, align: "center", fill: "#F7F4FD", stroke: "#8C4FFF" }, [
  icon("tgw_core", "transit_gateway", "fabric-tgw (Hub Router)"),
  grid("tgw_rts", null, "Segmented Route Tables (4 Domains)", { cols: 4, gap: 12, pad: 8 }, [
    box("rt_edge", "fabric-tgw-edge-rt\n0.0.0.0/0 → Inspection\n10.50.0.0/16 → Inspection", { w: 175, h: 58, fill: "#FFFFFF", stroke: "#8C4FFF", fs: 9 }),
    box("rt_core", "fabric-tgw-core-rt\n0.0.0.0/0 → Inspection\n10.40.0.0/16 → Inspection", { w: 175, h: 58, fill: "#FFFFFF", stroke: "#8C4FFF", fs: 9 }),
    box("rt_insp", "fabric-tgw-inspection-rt\n10.40.0.0/16 → Edge\n10.50.0.0/16 → Core\n0.0.0.0/0 → Egress", { w: 175, h: 58, fill: "#FFFFFF", stroke: "#8C4FFF", fs: 9 }),
    box("rt_egress", "fabric-tgw-egress-rt\n10.40.0.0/16 → Inspection\n10.50.0.0/16 → Inspection", { w: 175, h: 58, fill: "#FFFFFF", stroke: "#8C4FFF", fs: 9 }),
  ]),
]);

// ---------------------------------------------------------------------------
// 4. INSPECTION VPC (10.70.0.0/16) — GWLB + Suricata EC2
// ---------------------------------------------------------------------------
const inspAzA = group("insp_az_a", "group_availability_zone", "AZ ap-southeast-1a", { dir: "col", gap: 12 }, [
  privSubnet("insp_tgw_sub_a", "10.70.0.0/28 (TGW)", [
    icon("tgw_att_insp_a", "transit_gateway_attachment", "TGW Attach 1a (Appliance Mode)"),
  ]),
  privSubnet("insp_gwlbe_sub_a", "10.70.1.0/28 (GWLBe)", [
    icon("gwlbe_a", "endpoints", "GWLB Endpoint 1a"),
  ]),
  privSubnet("insp_fw_sub_a", "10.70.10.0/24 (Firewall)", [
    icon("suricata_a", "ec2", "Suricata EC2 IDS/IPS 1a"),
  ]),
]);

const inspAzB = group("insp_az_b", "group_availability_zone", "AZ ap-southeast-1b", { dir: "col", gap: 12 }, [
  privSubnet("insp_tgw_sub_b", "10.70.0.16/28 (TGW)", [
    icon("tgw_att_insp_b", "transit_gateway_attachment", "TGW Attach 1b (Appliance Mode)"),
  ]),
  privSubnet("insp_gwlbe_sub_b", "10.70.1.16/28 (GWLBe)", [
    icon("gwlbe_b", "endpoints", "GWLB Endpoint 1b"),
  ]),
  privSubnet("insp_fw_sub_b", "10.70.11.0/24 (Firewall)", [
    icon("suricata_b", "ec2", "Suricata EC2 IDS/IPS 1b"),
  ]),
]);

const inspVpc = group("insp_vpc", "group_vpc", "Inspection VPC (fabric-inspection-vpc · 10.70.0.0/16 · GWLB + Suricata)", { dir: "col", gap: 14, align: "center" }, [
  icon("gwlb_core", "gateway_load_balancer", "Gateway Load Balancer (fabric-gwlb · GENEVE 6081)"),
  phantom("insp_azs", "", { dir: "row", gap: 20, align: "top", header: 0 }, [inspAzA, inspAzB]),
]);

// ---------------------------------------------------------------------------
// 5. CORE EKS VPC (10.50.0.0/16) — Workload & Data Tier
// ---------------------------------------------------------------------------
const coreAzA = group("core_az_a", "group_availability_zone", "AZ ap-southeast-1a", { dir: "col", gap: 12 }, [
  privSubnet("core_node_a", "10.50.8.0/22 (Nodes)", [
    icon("node_core_a", "eks", "Core Node (Order/Inventory)"),
  ]),
  privSubnet("core_data_a", "10.50.20.0/24 (Data)", [
    icon("aurora_primary", "aurora", "Aurora PostgreSQL (Primary)"),
    icon("redis_a", "elasticache_for_redis", "ElastiCache Redis (AZ-A)"),
  ]),
  privSubnet("core_vpce_a", "10.50.30.0/24 (VPCE)", [
    icon("vpce_core_a", "vpc_privatelink", "VPCE (ECR/SQS/Logs/eks-auth)"),
  ]),
  privSubnet("core_tgw_sub_a", "10.50.250.0/28 (TGW)", [
    icon("tgw_att_core_a", "transit_gateway_attachment", "TGW Attach ENI 1a"),
  ]),
]);

const coreAzB = group("core_az_b", "group_availability_zone", "AZ ap-southeast-1b", { dir: "col", gap: 12 }, [
  privSubnet("core_node_b", "10.50.12.0/22 (Nodes)", [
    icon("node_core_b", "eks", "Core Node (Payment/Replica)"),
  ]),
  privSubnet("core_data_b", "10.50.21.0/24 (Data)", [
    icon("aurora_replica", "aurora", "Aurora PostgreSQL (Replica)"),
    icon("redis_b", "elasticache_for_redis", "ElastiCache Redis (AZ-B)"),
  ]),
  privSubnet("core_vpce_b", "10.50.31.0/24 (VPCE)", [
    icon("vpce_core_b", "vpc_privatelink", "VPCE (ECR/SQS/Logs/eks-auth)"),
  ]),
  privSubnet("core_tgw_sub_b", "10.50.250.16/28 (TGW)", [
    icon("tgw_att_core_b", "transit_gateway_attachment", "TGW Attach ENI 1b"),
  ]),
]);

const coreVpc = group("core_vpc", "group_vpc", "Core Workloads VPC (fabric-core-vpc · 10.50.0.0/16 · Zero Trust Data)", { dir: "col", gap: 14, align: "center" }, [
  phantom("core_azs", "", { dir: "row", gap: 20, align: "top", header: 0 }, [coreAzA, coreAzB]),
]);

// ---------------------------------------------------------------------------
// 6. EXTERNAL CLIENTS & EDGE INGRESS BAND
// ---------------------------------------------------------------------------
const clientsEdge = frame("client_band", "External Traffic & Edge Protection", { dir: "row", gap: 32, align: "center", fill: "#FFFFFF", stroke: "#8C4FFF" }, [
  icon("client_users", "users", "Internet Users"),
  icon("dns_route53", "route_53", "Amazon Route 53"),
  icon("waf_edge", "waf", "AWS WAF v2"),
]);

// ---------------------------------------------------------------------------
// TOPOLOGY COMPOSITION
// ---------------------------------------------------------------------------
const upperTier = phantom("upper_vpcs", "", { dir: "row", gap: 36, align: "top", header: 0 }, [edgeVpc, egressVpc]);
const lowerTier = phantom("lower_vpcs", "", { dir: "row", gap: 36, align: "top", header: 0 }, [inspVpc, coreVpc]);

const rootRegion = group("singapore_region", "group_region", "AWS Region: Singapore (ap-southeast-1)", { dir: "col", gap: 24, align: "center" }, [
  clientsEdge,
  upperTier,
  tgwHub,
  lowerTier,
]);

renderTree(d, rootRegion, [40, 70]);
d.title("AWS EKS Secure Network Fabric — Production Architecture (TGW · GWLB · Suricata · NFW · Dual EKS)");

// ---------------------------------------------------------------------------
// CONNECTIONS & TRAFFIC FLOWS
// ---------------------------------------------------------------------------
// External Ingress
d.link("client_users", "dns_route53", "HTTPS (443)");
d.link("dns_route53", "waf_edge", "DNS Query");
d.link("waf_edge", "edge_igw", "Inspected Inbound", { flow: true });
d.link("edge_igw", "alb_edge_a", "", { role: "fanout" });
d.link("edge_igw", "alb_edge_b", "", { role: "fanout" });
d.link("alb_edge_a", "node_edge_a", "Target Group");
d.link("alb_edge_b", "node_edge_b", "Target Group");

// Edge to TGW
d.link("node_edge_a", "tgw_att_edge_a", "Core / Outbound");
d.link("node_edge_b", "tgw_att_edge_b", "Core / Outbound");
d.link("tgw_att_edge_a", "tgw_core", "Attachment", { dash: true });
d.link("tgw_att_edge_b", "tgw_core", "Attachment", { dash: true });

// TGW to Inspection VPC (East-West & Outbound Inspection)
d.link("tgw_core", "tgw_att_insp_a", "Appliance Mode", { flow: true });
d.link("tgw_core", "tgw_att_insp_b", "Appliance Mode", { flow: true });
d.link("tgw_att_insp_a", "gwlbe_a", "Next Hop");
d.link("tgw_att_insp_b", "gwlbe_b", "Next Hop");
d.link("gwlbe_a", "gwlb_core", "GENEVE 6081", { dash: true });
d.link("gwlbe_b", "gwlb_core", "GENEVE 6081", { dash: true });
d.link("gwlb_core", "suricata_a", "IPS Inspection");
d.link("gwlb_core", "suricata_b", "IPS Inspection");

// TGW to Core VPC
d.link("tgw_core", "tgw_att_core_a", "Attachment", { dash: true });
d.link("tgw_core", "tgw_att_core_b", "Attachment", { dash: true });
d.link("tgw_att_core_a", "node_core_a", "Inspected E-W");
d.link("tgw_att_core_b", "node_core_b", "Inspected E-W");

// Core EKS to Data Tier (Local VPC Route)
d.link("node_core_a", "aurora_primary", "TCP 5432");
d.link("node_core_a", "redis_a", "TCP 6379");
d.link("node_core_b", "aurora_replica", "TCP 5432 (Read)");
d.link("node_core_b", "redis_b", "TCP 6379");
d.link("aurora_primary", "aurora_replica", "Replication", { dash: true });

// TGW to Egress VPC (Centralized Outbound)
d.link("tgw_core", "tgw_att_egress_a", "0.0.0.0/0", { flow: true });
d.link("tgw_core", "tgw_att_egress_b", "0.0.0.0/0", { flow: true });
d.link("tgw_att_egress_a", "nfw_ep_a", "NFW AZ-a");
d.link("tgw_att_egress_b", "nfw_ep_b", "NFW AZ-b");
d.link("nfw_ep_a", "nat_a", "Domain Filtered");
d.link("nfw_ep_b", "nat_b", "Domain Filtered");
d.link("nat_a", "egress_igw", "SNAT 0.0.0.0/0");
d.link("nat_b", "egress_igw", "SNAT 0.0.0.0/0");

// ---------------------------------------------------------------------------
// CLUSTER FRAMES (Spanning AZs)
// ---------------------------------------------------------------------------
d.clusterBox("box_edge_eks", ["node_edge_a", "node_edge_b"], "Edge EKS Cluster 1.31 (Frontend & Auth Services)", { icon: "eks", stroke: "#ED7100" });
d.clusterBox("box_core_eks", ["node_core_a", "node_core_b"], "Core EKS Cluster 1.31 (Order, Inventory, Payment Services)", { icon: "eks", stroke: "#ED7100" });
d.clusterBox("box_suricata", ["suricata_a", "suricata_b"], "Suricata IDS/IPS Appliances (Multi-AZ Cluster)", { icon: "ec2", stroke: "#ED7100" });
d.clusterBox("box_aurora", ["aurora_primary", "aurora_replica"], "Amazon Aurora PostgreSQL Serverless v2 Multi-AZ", { icon: "aurora", stroke: "#C925D1" });

// ---------------------------------------------------------------------------
// VALIDATION & FILE EMISSION
// ---------------------------------------------------------------------------
const res = d.validate();
console.log("VALIDATE:", JSON.stringify({ ok: res.ok, errors: res.errors, warnings: res.warnings, advice: res.audit.advice }));

const outDrawioPath = new URL("./full-network-fabric.drawio", import.meta.url);
writeFileSync(outDrawioPath, d.mxfile("AWS EKS Secure Network Fabric"));

// Self-check render
const __cli = (a) => process.env.DRAWIO_AI_CLI
  ? __exec(process.execPath, [process.env.DRAWIO_AI_CLI, ...a], { encoding: "utf8" })
  : __exec("drawio-ai", a, { encoding: "utf8" });
const __f = fileURLToPath(outDrawioPath);
try {
  console.log(__cli(["render", __f, "--check", "-o", __f.replace(/\.drawio$/, ".png")]).trim());
} catch (e) {
  console.error("RENDER-SKIPPED:", String(e.message).split("\n")[0]);
}
