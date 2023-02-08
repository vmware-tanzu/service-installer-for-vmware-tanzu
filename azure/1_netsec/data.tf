# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
data "terraform_remote_state" "keeper" {
  backend = "local"

  config = {
    path = "../0_keepers/terraform.tfstate"
  }
}

data "azurerm_subscription" "this" {
  subscription_id = var.sub_id
}

data "azurerm_storage_account" "keeper" {
  name                = data.terraform_remote_state.keeper.outputs.storage_account
  resource_group_name = data.terraform_remote_state.keeper.outputs.keeper_resource_group_name
}