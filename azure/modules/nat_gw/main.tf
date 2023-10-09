# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
variable "location" {}

variable "prefix" {}

variable "resource_group_name" {}

variable "subnet_id" {}

resource "azurerm_public_ip" "this" {
  name                = "pip-ngw-${var.prefix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_nat_gateway" "this" {
  name                = "ngw-${var.prefix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku_name            = "Standard"
}

resource "azurerm_nat_gateway_public_ip_association" "this" {
  nat_gateway_id       = azurerm_nat_gateway.this.id
  public_ip_address_id = azurerm_public_ip.this.id
}

resource "azurerm_subnet_nat_gateway_association" "this" {
  for_each = var.subnet_id
  subnet_id      = each.value
  nat_gateway_id = azurerm_nat_gateway.this.id
}