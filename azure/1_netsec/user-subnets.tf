# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
# The following subnet definitions serve as an example demonstrating an
# administrative subnet, and pairs of management and workload cluster subnets.

# Locals define the CIDR blocks while subnet_settings within respective modules
# define values for the subnets themselves. The subnet_settings 'key' represents
# the name of the subnet as seen within Azure.
#
# Azure prefers using the list type for subnet address prefixes, however this 
# may produce unpredictable results for a TKGm CAPZ cluster implementation. 
# We can support the use of lists, but at present, only a single prefix per 
# subnet is supported.

locals {
  tkgm_admin_net    = ["10.1.2.0/28"]
  tkgm_mgmtnode_net = ["10.1.2.64/26"]
  tkgm_mgmtctrl_net = ["10.1.2.192/26"]
  tkgm_wrkctrl_net  = ["10.1.2.16/28"]
  tkgm_wrknode_net  = ["10.1.2.128/26"]

  tkgm_subnets = {
    TKGM-MgmtCtrl = {
      resource_group_name                            = local.local_data.resource_group_name
      virtual_network_name                           = local.local_data.vnet_name
      address_prefixes                               = local.tkgm_mgmtctrl_net
      service_endpoints                              = []
      enforce_private_link_endpoint_network_policies = false
      enforce_private_link_service_network_policies  = false
      service_endpoint_policy_ids                    = []
      delegation_name                                = null
      service_delegation_name                        = null
      service_delegation_actions                     = []
      nsg_name                                       = "${var.tkg_cluster_name}-management-controlplane-nsg" # per docs...
      cluster_type                                   = "management"
      subnet_type                                    = "controlplane"
    }
    TKGM-MgmtNode = {
      resource_group_name                            = local.local_data.resource_group_name
      virtual_network_name                           = local.local_data.vnet_name
      address_prefixes                               = local.tkgm_mgmtnode_net
      service_endpoints                              = []
      enforce_private_link_endpoint_network_policies = false
      enforce_private_link_service_network_policies  = false
      service_endpoint_policy_ids                    = []
      delegation_name                                = null
      service_delegation_name                        = null
      service_delegation_actions                     = []
      nsg_name                                       = "${var.tkg_cluster_name}-management-node-nsg" # per docs...
      cluster_type                                   = "management"
      subnet_type                                    = "node"
    }
    TKGM-WrkCtrl = {
      resource_group_name                            = local.local_data.resource_group_name
      virtual_network_name                           = local.local_data.vnet_name
      address_prefixes                               = local.tkgm_wrkctrl_net
      service_endpoints                              = []
      enforce_private_link_endpoint_network_policies = false
      enforce_private_link_service_network_policies  = false
      service_endpoint_policy_ids                    = []
      delegation_name                                = null
      service_delegation_name                        = null
      service_delegation_actions                     = []
      nsg_name                                       = "${var.tkg_cluster_name}-workload-controlplane-nsg" # per docs...
      cluster_type                                   = "workload"
      subnet_type                                    = "controlplane"
    }
    TKGM-WrkNode = {
      resource_group_name                            = local.local_data.resource_group_name
      virtual_network_name                           = local.local_data.vnet_name
      address_prefixes                               = local.tkgm_wrknode_net
      service_endpoints                              = []
      enforce_private_link_endpoint_network_policies = false
      enforce_private_link_service_network_policies  = false
      service_endpoint_policy_ids                    = []
      delegation_name                                = null
      service_delegation_name                        = null
      service_delegation_actions                     = []
      nsg_name                                       = "${var.tkg_cluster_name}-workload-node-nsg" # per docs...
      cluster_type                                   = "workload"
      subnet_type                                    = "node"
    }
    Admin = {
      resource_group_name                            = local.local_data.resource_group_name
      virtual_network_name                           = local.local_data.vnet_name
      address_prefixes                               = local.tkgm_admin_net
      service_endpoints                              = ["Microsoft.Storage"]
      enforce_private_link_endpoint_network_policies = true
      enforce_private_link_service_network_policies  = false
      service_endpoint_policy_ids                    = []
      delegation_name                                = null
      service_delegation_name                        = null
      service_delegation_actions                     = []
      nsg_name                                       = "nsg-${var.prefix}-admin"
      cluster_type                                   = ""
      subnet_type                                    = ""
    }
  }
}

#===================
#   TKGM Management Cluster Tier
#===================
# TKG has assumptions about the NSG names depending on subnet roles.
# The ftwo modules below separate those assumptions.

# IMPORTANT! subnet names need to include keywords: mgmt, work, or admin; as appropriate for their use
# - "mgmt" includes any subnet destined for the TKG Management Cluster
# - "work" includes any subnet used for TKG Workload Clusters
# - "admin" includes the subnet (generally 1) used for administrative functions such as the bootstrap VM

# module "node_sub" {
#   source        = "../modules/node_subnet"
#   local_data    = local.local_data
#   flow_log_data = module.vnet_base.flow_log_data
#   subnet_settings = {
#     # "TKGM-MgmtNode"     = { "network" = local.tkgm_mgmtnode_net, "service_endpoints" = [], "allow_plink_endpoints" = false }
#     "TKGM-WorkloadNode" = { "network" = local.tkgm_wrknode_net, "service_endpoints" = [], "allow_plink_endpoints" = false }
#   }
# }

# module "controlplane_sub" {
#   source        = "../modules/controlplane_subnet"
#   local_data    = local.local_data
#   flow_log_data = module.vnet_base.flow_log_data
#   subnet_settings = {
#     # "TKGM-MgmtCtrl"     = { "network" = local.tkgm_mgmtctrl_net, "service_endpoints" = [], "allow_plink_endpoints" = false }
#     "TKGM-Admin"        = { "network" = local.tkgm_admin_net, "service_endpoints" = ["Microsoft.Storage"], "allow_plink_endpoints" = true }
#     "TKGM-WorkloadCtrl" = { "network" = local.tkgm_wrkctrl_net, "service_endpoints" = [], "allow_plink_endpoints" = false }
#   }
# }

# Subnet w/NSG (1:1)
module "subnet_w_nsg" {
  for_each = local.tkgm_subnets
  source   = "../modules/subnet"

  local_data      = local.local_data
  flow_log_data   = module.vnet_base.flow_log_data
  subnet_settings = { (each.key) = each.value }
}