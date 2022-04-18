# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
output "storage_account" {
  value = azurerm_storage_account.this.name
}

output "access_key" {
  value     = azurerm_storage_account.this.primary_access_key
  sensitive = true
}

output "key_vault" {
  value = module.akv.key_vault.name
}

output "keeper_resource_group_name" {
  value = azurerm_resource_group.this.name
}

output "run_me" {
  value = "~~ set environment ARM_ACCESS_KEY ~~ `terraform output -raw access_key`"
}

output "random_seed" {
  value = random_id.this.hex # you can use this elsewhere as a random seed when needed; it will keep things looking consistent. Remember that the seed is regenerated if the Keeper Resource Group is destroyed!
}

# resource "null_resource" "this" {
#   provisioner "local-exec" {
#     command = "$env:ARM_ACCESS_KEY=\"${azurerm_storage_account.this.primary_access_key}\""
#     interpreter = ["pwsh", "-NoProfile", "-Command"]
#   }
# }