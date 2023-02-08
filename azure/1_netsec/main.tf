# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
#---------------------------------------------
#  RESOURCE GROUP
#---------------------------------------------
resource "azurerm_resource_group" "rg" {
  name     = "rg-${var.prefix}"
  location = var.location

  tags = local.tags

  lifecycle {
    ignore_changes = [
      tags,
    ]
  }
}

# resource "azurerm_storage_account_network_rules" "keeper_acls" {
#   storage_account_id         = data.azurerm_storage_account.keeper.id
#   default_action             = "Deny"
#   bypass                     = ["Logging", "Metrics", "AzureServices"]
#   virtual_network_subnet_ids = local.admin_subnet_ids

#   ip_rules = [local.ipAcl]
# }

#---------------------------------------------
#  RESOURCES
#---------------------------------------------
module "vnet_base" {
  source                 = "../modules/vnet"
  local_data             = local.base_inputs
  dns_list               = var.dns_list
  boot_diag_sa_name      = local.boot_diag_sa_name
  CreateNetworkWatcher   = var.CreateNetworkWatcher
  CreateNetworkWatcherRG = var.CreateNetworkWatcherRG
}

module "myip" {
  source  = "4ops/myip/http"
  version = "1.0.0"
}

module "nat_gw" {
  count  = local.create_nat_gateway
  source = "../modules/nat_gw"

  depends_on = [
    module.subnet_w_nsg
  ]
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  prefix              = var.prefix
  subnet_id           = { for k, v in local.tkgm_subnets : k => module.subnet_w_nsg[k].subnets[k].id }
}