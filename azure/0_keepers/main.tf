# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
#---------------------------------------------
#  RESOURCE GROUP
#---------------------------------------------
resource "azurerm_resource_group" "this" {
  name     = "rg-${var.prefix}"
  location = var.location

  tags = local.tags

  lifecycle {
    ignore_changes = [
      tags,
    ]
  }
}

# resource "azurerm_management_lock" "keeper_rg" {
#   count      = 1
#   name       = "lock-rg-keeper"
#   scope      = azurerm_resource_group.this.id
#   lock_level = "CanNotDelete"
#   notes      = "This resource group's contents should be protected against accidental deletion!"
# }

module "akv" {
  source = "../modules/akv"

  prefix         = var.prefix
  prefix_short   = var.prefix_short
  location       = var.location
  resource_group = azurerm_resource_group.this.name
  tenant_id      = var.tenant_id
  random_hex     = random_id.this.hex
  tags           = local.tags
  acl_ip         = module.myip.address
  acl_obj_id     = local.acl_obj_id
}

resource "random_id" "this" {
  keepers = {
    sa_id = azurerm_resource_group.this.id
  }
  byte_length = 2
}

resource "local_file" "netsec_prov" {
  content  = local.netsec_prov
  filename = "../1_netsec/provider.tf"
}

resource "local_file" "dns_prov" {
  content  = local.dns_prov
  filename = "../2_dns/provider.tf"
}

resource "local_file" "bootstrap_prov" {
  content  = local.bootstrap_prov
  filename = "../3_bootstrap/provider.tf"
}

resource "local_file" "bootstrap_data" {
  content  = local.bootstrap_data
  filename = "../3_bootstrap/data.tf"
}

resource "azurerm_storage_account" "this" {
  name                      = "sa${var.prefix_short}${random_id.this.hex}"
  resource_group_name       = azurerm_resource_group.this.name
  location                  = var.location
  account_kind              = "StorageV2"
  account_tier              = "Standard"
  account_replication_type  = "ZRS"
  enable_https_traffic_only = true
  min_tls_version           = "TLS1_2"
  allow_blob_public_access  = true
  # account_encryption_source = "Microsoft.KeyVault"

  tags = azurerm_resource_group.this.tags

  lifecycle {
    ignore_changes = [
      tags["StartDate"],
    ]
  }
}

# resource "azurerm_storage_account_network_rules" "keeper_acls" {
#   depends_on         = [null_resource.ctr_state]
#   storage_account_id = azurerm_storage_account.this.id
#   default_action     = "Deny"
#   bypass             = ["Logging", "Metrics", "AzureServices"]
#   # virtual_network_subnet_ids = [module.vnet_base.vnet_id]
#   ip_rules = [local.ipAcl]
# }

######
# Moving these resources out of Terraform and into "Config Management"
# A pipeline task to add these objects (once) must be performed immediately 
# following the 'keepers' module. For the demonstration here, I've 
# just included the step inline with a provisioner 😢
######
# resource "azurerm_storage_container" "ctr_state" {
#   name                  = "terraform-state"
#   storage_account_name  = azurerm_storage_account.this.name
#   container_access_type = "private"
# }

resource "null_resource" "ctr_state" {
  provisioner "local-exec" {
    command = "az storage container create --subscription ${var.sub_id} --account-name ${azurerm_storage_account.this.name} --auth-mode login -n terraform-state --public-access off"
  }
}

# resource "null_resource" "ctr_download" {
#   provisioner "local-exec" {
#     command = "az storage container create --subscription ${var.sub_id} --account-name ${azurerm_storage_account.this.name} -n downloads --public-access blob"
#   }
# }