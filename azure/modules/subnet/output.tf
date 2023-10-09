# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
output "subnets" {
  value       = azurerm_subnet.tier_net
  description = "A map of subnets created from this module"
}

# output "route_tables" {
#   value       = azurerm_route_table.tier_rt
#   description = "A map of route tables created from this module"
# }