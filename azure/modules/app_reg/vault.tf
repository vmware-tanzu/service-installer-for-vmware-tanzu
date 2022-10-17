# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
data "azurerm_key_vault" "this" {
  name                = var.vault_name
  resource_group_name = var.vault_resource_group_name
}

resource "azurerm_key_vault_secret" "AZURE_CLIENT_ID" {
  name         = "AZURE-CLIENT-ID"
  value        = "<encoded:${base64encode(azuread_application.this.application_id)}>"
  key_vault_id = data.azurerm_key_vault.this.id
}

resource "azurerm_key_vault_secret" "AZURE_CLIENT_SECRET" {
  name         = "AZURE-CLIENT-SECRET"
  value        = "<encoded:${base64encode(azuread_application_password.this.value)}>"
  key_vault_id = data.azurerm_key_vault.this.id
}