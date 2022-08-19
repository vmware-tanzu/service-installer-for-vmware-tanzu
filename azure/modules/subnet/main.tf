# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
# STAGE
variable "subnet_settings" {
  type = map(
    object({
      resource_group_name                            = string,
      virtual_network_name                           = string,
      address_prefixes                               = list(string),
      service_endpoints                              = list(string),
      enforce_private_link_endpoint_network_policies = bool,
      enforce_private_link_service_network_policies  = bool,
      service_endpoint_policy_ids                    = list(string),
      delegation_name                                = string,
      service_delegation_name                        = string,
      service_delegation_actions                     = list(string),
      nsg_name                                       = string,
    })
  )
}

#--------------------------------------------
#  SUBNET AND ROUTE CREATION
#--------------------------------------------
resource "azurerm_subnet" "tier_net" {
  for_each = var.subnet_settings

  name                                           = each.key
  address_prefixes                               = each.value.address_prefixes
  resource_group_name                            = var.local_data.resource_group_name
  virtual_network_name                           = var.local_data.vnet_name
  service_endpoints                              = each.value.service_endpoints
  enforce_private_link_endpoint_network_policies = each.value.enforce_private_link_endpoint_network_policies
  enforce_private_link_service_network_policies  = each.value.enforce_private_link_service_network_policies

  lifecycle {
    ignore_changes = [
      delegation,
      # removed service_delegation and service_endpoint
    ]
  }
}

# Example route change for default
# resource "azurerm_route" "tier_TO_internet" {
#   for_each = local.subnets

#   name                   = "Default_Route"
#   resource_group_name    = var.local_data.resource_group_name
#   route_table_name       = azurerm_route_table.tier_rt[each.key].name
#   address_prefix         = "0.0.0.0/0"
#   next_hop_type          = "VirtualAppliance"
#   next_hop_in_ip_address = VALID_TARGET_IP
# }

#      ------------- Route Table Assocation -------------
# resource "azurerm_subnet_route_table_association" "tier" {
#   for_each = local.subnets

#   subnet_id      = azurerm_subnet.tier_net[each.key].id
#   route_table_id = azurerm_route_table.tier_rt[each.key].id
# }


#---------------------------------------------
#  NSG CREATION
#---------------------------------------------
# Example rulesets including defaults
#-------------   TKGm Node Subnet NSG    -------------
resource "azurerm_network_security_group" "this" {
  name                = lookup(var.subnet_settings[(coalesce(keys(var.subnet_settings)...))], "nsg_name", "no-default")
  location            = var.local_data.location
  resource_group_name = var.local_data.resource_group_name

  tags = var.local_data.tags

  lifecycle {
    ignore_changes = [
      tags["StartDate"],
    ]
  }
}

#------------- Worker Subnet NSG Rules -------------
resource "azurerm_network_security_rule" "Worker_allow_HealthProbe_in" {
  name                        = "Allow_Azure_Healthprobes"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "*"
  source_address_prefix       = "AzureLoadBalancer"
  source_port_range           = "*"
  destination_address_prefix  = "*"
  destination_port_range      = "*"
  resource_group_name         = var.local_data.resource_group_name
  network_security_group_name = azurerm_network_security_group.this.name
}

resource "azurerm_network_security_rule" "Worker_allow_Select_in" {
  name                        = "Allow_Select"
  priority                    = 101
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "*"
  source_address_prefix       = var.local_data.myip
  source_port_range           = "*"
  destination_address_prefix  = "*"
  destination_port_range      = "*"
  resource_group_name         = var.local_data.resource_group_name
  network_security_group_name = azurerm_network_security_group.this.name
}

# ER is ExpressRoute and represents anything except Internet IPs and anything else already allowed
# resource "azurerm_network_security_rule" "Worker_allow_ER_in" {
#   name                        = "Allow_ER_Inbound"
#   priority                    = 110
#   direction                   = "Inbound"
#   access                      = "Allow"
#   protocol                    = "*"
#   source_address_prefix       = "10.0.0.0/8" # An example on-prem network CIDR
#   source_port_range           = "*"
#   destination_address_prefix  = "*"
#   destination_port_range      = "*"
#   resource_group_name         = var.local_data.resource_group_name
#   network_security_group_name = azurerm_network_security_group.this.name
# }

#------------- NSG Flow Logs -------------
resource "azurerm_network_watcher_flow_log" "tier" {
  name                      = "flg-${azurerm_network_security_group.this.name}"
  network_watcher_name      = var.flow_log_data.nw_name
  resource_group_name       = "NetworkWatcherRG"
  network_security_group_id = azurerm_network_security_group.this.id
  storage_account_id        = var.flow_log_data.flow_log_sa_id
  enabled                   = true

  retention_policy {
    enabled = true
    days    = 30
  }

  traffic_analytics {
    enabled               = true
    workspace_id          = var.flow_log_data.law_workspace_id
    workspace_region      = var.local_data.location
    workspace_resource_id = var.flow_log_data.law_id
  }

  tags = var.local_data.tags

  lifecycle {
    ignore_changes = [
      tags["StartDate"],
    ]
  }
}

#      ------------- NSG Worker Subnet Assocation -------------
resource "azurerm_subnet_network_security_group_association" "this" {
  subnet_id                 = azurerm_subnet.tier_net[coalesce(keys(azurerm_subnet.tier_net)...)].id
  network_security_group_id = azurerm_network_security_group.this.id
}