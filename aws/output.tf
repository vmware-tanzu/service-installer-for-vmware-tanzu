# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
output "ssh_cmd" {
  value = "ssh ubuntu@${module.control_plane.jumpbox_dns[0]} -i ${var.jb_key_file}"
}
