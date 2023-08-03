# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
data "azuread_client_config" "current" {}

data "azurerm_resource_group" "netsec" {
  name = var.netsec_resource_group
}

data "azurerm_resource_group" "tkg" {
  name = var.tkg_resource_group
}