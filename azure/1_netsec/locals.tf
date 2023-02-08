# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
locals {
  tagOverride = {
    StartDate = timestamp()
  }
  tags = merge(data.azurerm_subscription.this.tags, var.additional_tags, local.tagOverride)

  vault_name                = var.vault_name != "" ? var.vault_name : data.terraform_remote_state.keeper.outputs.key_vault
  vault_resource_group_name = var.vault_resource_group_name != "" ? var.vault_resource_group_name : data.terraform_remote_state.keeper.outputs.keeper_resource_group_name
  ipAcl                     = var.ipAcl != "" ? var.ipAcl : module.myip.address
  # admin_subnet_ids          = [for subnet, item in merge(module.node_sub.subnets, module.controlplane_sub.subnets) : item.id if length(regexall("admin", lower(subnet))) > 0]
  boot_diag_sa_name  = var.boot_diag_sa_name != "" ? var.boot_diag_sa_name : "sa${var.prefix_short}diag${data.terraform_remote_state.keeper.outputs.random_seed}"
  create_nat_gateway = var.create_nat_gateway == true ? 1 : 0
}

#--------------------------------------
#  CONSOLIDATED INFO ABOUT THIS VNET
#--------------------------------------
locals {
  # Consolidated list of inputs required by the base module (i.e. spoke_base, hub_base)
  base_inputs = {
    prefix              = var.prefix
    sub_id              = var.sub_id
    resource_group_name = azurerm_resource_group.rg.name
    location            = azurerm_resource_group.rg.location
    core_address_space  = var.core_address_space
    myip                = local.ipAcl
    tags                = local.tags
    tkg_cluster_name    = var.tkg_cluster_name
    cluster_name_mgmt   = "${var.tkg_cluster_name}-management"
    cluster_name_wrk    = "${var.tkg_cluster_name}-workload"
  }

  # List of all outputs that come from the base module that will be referenced elsewhere.
  base_outputs = {
    vnet_name = module.vnet_base.vnet_name
    vnet_id   = module.vnet_base.vnet_id
  }

  # Merged list of all inputs and outputs for the base module.  This data will be used by other repos (sec) and modules (network_tier)
  local_data = merge(local.base_inputs, local.base_outputs)
}
