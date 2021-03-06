# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
output "bindvms" {
  value = { for n in range(var.bindvms) : module.bindvm[n].vm.name => module.bindvm[n].vnic.private_ip_address }
}