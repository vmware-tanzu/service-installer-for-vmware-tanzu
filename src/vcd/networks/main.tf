terraform {
  required_providers {
    vcd = {
      source = "vmware/vcd"
      version = "3.8.0"
    }
  }
}


data "vcd_org_vdc" "org_vdc" {
  name = var.org_vdc_details.svcOrgVdcName
  org  = var.org_details.svcOrgName

}

data "vcd_nsxt_manager" "nsxt_manager" {
  name = var.nsxt_manager_name
}

data "vcd_nsxt_tier0_router" "nsxt_t0_router" {
  count           = var.vcd_t0_gtw_details.importTier0 == "true" ? 1 : 0
  name            = var.vcd_t0_gtw_details.tier0Router
  nsxt_manager_id = data.vcd_nsxt_manager.nsxt_manager.id
}

data "vcd_nsxt_alb_service_engine_group" "nsxt_alb_seg" {
  name = var.avi_alb_details.avi_se_group_details.serviceEngineGroupVcdDisplayName
}

data "vcd_external_network_v2" "ext_net" {
  count       = var.vcd_t0_gtw_details.importTier0 != "true" ? 1 : 0
  name        = var.vcd_t0_gtw_details.tier0GatewayName
}

# Creating Tier0 Router/Importing nsxt Tier0 gateway

resource "vcd_external_network_v2" "ext_net_nsxt_t0" {
  count       = var.vcd_t0_gtw_details.importTier0 == "true" ? 1 : 0
  name        = var.vcd_t0_gtw_details.tier0GatewayName

  nsxt_network {
    nsxt_manager_id      = data.vcd_nsxt_manager.nsxt_manager.id
    nsxt_tier0_router_id = data.vcd_nsxt_tier0_router.nsxt_t0_router[0].id
  }

  ip_scope {
    enabled       = true
    gateway       = split("/", var.vcd_t0_gtw_details.extNetGatewayCIDR)[0]
    prefix_length = split("/", var.vcd_t0_gtw_details.extNetGatewayCIDR)[1]

    static_ip_pool {
      start_address = var.vcd_t0_gtw_details.extNetStartIP
      end_address   = var.vcd_t0_gtw_details.extNetEndIP
    }
  }
}

resource "vcd_nsxt_edgegateway" "nsxt_edgegateway" {
  count       = var.create_t1_gtw == "true" ? 1 : 0
  org         = var.org_details.svcOrgName
  owner_id    = data.vcd_org_vdc.org_vdc.id
  name        = var.vcd_t1_gtw_details.tier1GatewayName

  external_network_id = var.vcd_t0_gtw_details.importTier0 == "true" ? vcd_external_network_v2.ext_net_nsxt_t0[0].id : data.vcd_external_network_v2.ext_net[0].id

  subnet {
    gateway       = split("/", var.vcd_t0_gtw_details.extNetGatewayCIDR)[0]
    prefix_length = split("/", var.vcd_t0_gtw_details.extNetGatewayCIDR)[1]
    primary_ip    = var.vcd_t1_gtw_details.primaryIp
    allocated_ips {
      start_address = var.vcd_t1_gtw_details.ipAllocationStartIP
      end_address   = var.vcd_t1_gtw_details.ipAllocationEndIP
    }
  }
  
  depends_on = [vcd_external_network_v2.ext_net_nsxt_t0[0]]

}

resource "vcd_network_routed" "routed_network_with_primary_dns" {

  count = (var.create_t1_gtw == "true" && var.create_vcd_rtd_net == "true" && var.vcd_net_details.secondaryDNS == "") ? 1 : 0
  org   = var.org_details.svcOrgName
  vdc   = var.org_vdc_details.svcOrgVdcName

  name         = var.vcd_net_details.networkName
  edge_gateway = var.vcd_t1_gtw_details.tier1GatewayName
  gateway      = cidrhost(var.vcd_net_details.gatewayCIDR, 1)
  dns1         = var.vcd_net_details.primaryDNS
  dns_suffix   = var.vcd_net_details.dnsSuffix

  static_ip_pool {
    start_address = var.vcd_net_details.staticIpPoolStartAddress
    end_address   = var.vcd_net_details.staticIpPoolEndAddress
  }
  depends_on = [vcd_nsxt_edgegateway.nsxt_edgegateway]
}

resource "vcd_network_routed" "routed_network_with_secondary_dns" {

  count = (var.create_t1_gtw == "true" && var.create_vcd_rtd_net == "true" && var.vcd_net_details.secondaryDNS != "") ? 1 : 0
  org   = var.org_details.svcOrgName
  vdc   = var.org_vdc_details.svcOrgVdcName

  name         = var.vcd_net_details.networkName
  edge_gateway = var.vcd_t1_gtw_details.tier1GatewayName
  gateway      = cidrhost(var.vcd_net_details.gatewayCIDR, 1)
  dns1         = var.vcd_net_details.primaryDNS
  dns2         = var.vcd_net_details.secondaryDNS
  dns_suffix   = var.vcd_net_details.dnsSuffix

  static_ip_pool {
    start_address = var.vcd_net_details.staticIpPoolStartAddress
    end_address   = var.vcd_net_details.staticIpPoolEndAddress
  }
  depends_on = [vcd_nsxt_edgegateway.nsxt_edgegateway]
}

resource "vcd_nsxt_nat_rule" "snat" {
  count  = var.create_t1_gtw == "true" ? 1 : 0
  org    = var.org_details.svcOrgName

  edge_gateway_id = vcd_nsxt_edgegateway.nsxt_edgegateway[0].id

  name        = can(var.vcd_net_details.nat_rule_name) ? var.vcd_net_details.nat_rule_name : "SNAT rule"
  rule_type   = can(var.vcd_net_details.nat_rule_type) ? var.vcd_net_details.nat_rule_type : "SNAT"

  # Using primary_ip from edge gateway
  external_address         = var.vcd_t1_gtw_details.primaryIp 
  #internal_address         = var.vcd_net_details.gatewayCIDR
  internal_address         = join("", [join(".", concat(slice(split(".", var.vcd_net_details.gatewayCIDR), 0, 3), ["0/"], )), split("/", var.vcd_net_details.gatewayCIDR)[1]])
  logging                  = can(var.vcd_net_details.enableLogging) ? var.vcd_net_details.enableLogging : true
}


resource "vcd_nsxt_firewall" "nsxt_firewall" {
    count             = var.create_t1_gtw == "true" ? 1 : 0
    org               = var.org_details.svcOrgName
    edge_gateway_id   = vcd_nsxt_edgegateway.nsxt_edgegateway[0].id

   dynamic "rule" {
     for_each = can(var.vcd_net_details.nsxt_firewall_rules) ? var.vcd_net_details.nsxt_firewall_rules : ["true"]
     content {
      action          = can(rule.value.action) ? rule.value.action : "ALLOW"
      name            = can(rule.value.name) ? rule.value.name : "default_rule"
      direction       = can(rule.value.direction) ? rule.value.direction : "IN_OUT"
      ip_protocol     = can(rule.value.ip_protocol) ? rule.value.ip_protocol : "IPV4_IPV6"
     }

  }  
}


resource "vcd_nsxt_alb_settings" "org1" {
  count           = var.create_t1_gtw == "true" ? 1 : 0
  org             = var.org_details.svcOrgName

  edge_gateway_id = vcd_nsxt_edgegateway.nsxt_edgegateway[0].id
  is_active       = can(var.vcd_net_details.enableALB) ? var.vcd_net_details.enableALB : true 
  supported_feature_set = can(var.vcd_net_details.supportedFeatureSet) ? var.vcd_net_details.supportedFeatureSet : "PREMIUM"
}


resource "vcd_nsxt_alb_edgegateway_service_engine_group" "nsxt_alb_seg" {
  count                   = var.create_t1_gtw == "true" ? 1 : 0
  edge_gateway_id         = vcd_nsxt_edgegateway.nsxt_edgegateway[0].id
  service_engine_group_id = data.vcd_nsxt_alb_service_engine_group.nsxt_alb_seg.id

}
