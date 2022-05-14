# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
resource "azuread_application" "this" {
  display_name            = var.disp_name
  prevent_duplicate_names = true
  logo_image              = filebase64(var.logo)
  owners                  = [data.azuread_client_config.current.object_id]
  sign_in_audience        = "AzureADMyOrg"
}

resource "azuread_service_principal" "this" {
  application_id = azuread_application.this.application_id
  use_existing   = true
}

resource "time_rotating" "this" {
  rotation_days = 60
}

resource "azuread_application_password" "this" {
  application_object_id = azuread_application.this.object_id
  rotate_when_changed = {
    rotation = time_rotating.this.id
  }
}

resource "azurerm_role_assignment" "netsec_rg" {
  scope                = data.azurerm_resource_group.netsec.id
  role_definition_name = "Network Contributor"
  principal_id         = azuread_service_principal.this.object_id
}

resource "azurerm_role_assignment" "tkg_rg" {
  scope                = data.azurerm_resource_group.tkg.id
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.this.object_id
}

output "AZURE_CLIENT_ID" {
  value = "<encoded:${base64encode(azuread_application.this.application_id)}>"
}

output "AZURE_CLIENT_SECRET" {
  value = "<encoded:${base64encode(azuread_application_password.this.value)}>"
  # value = "<encoded:${base64encode("xOE7Q~IN1i6p4xqrcFO9GNv21KGStnTFuBrnh")}>"
}

output "app_deets" {
  value = azuread_application.this
}

output "sp_deets" {
  value = azuread_service_principal.this
}