# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
data "cloudinit_config" "this" {
  gzip          = false
  base64_encode = true

  part {
    content_type = "part-handler"
    content      = templatefile("${path.module}/part-handler.py.tftpl", local.cloud_init)
  }

  part {
    content_type = "text/cloud-config"
    content      = templatefile("${path.module}/cloud.tftpl", local.cloud_init)
  }

  part {
    content_type = "text/cloud-config"
    content = jsonencode({
      write_files = [
        {
          encoding = "gz+b64"
          content  = base64gzip(file("${path.module}/../resources/contour-data-values.yaml"))
          path     = "/home/${var.user}/tkg-install/contour-data-values.yaml"
        },
        {
          encoding = "gz+b64"
          content  = base64gzip(file("${path.module}/../resources/grafana-data-values.yaml"))
          path     = "/home/${var.user}/tkg-install/grafana-data-values.yaml"
        },
        {
          encoding = "gz+b64"
          content  = base64gzip(file("${path.module}/../resources/harbor-data-values.yaml"))
          path     = "/home/${var.user}/tkg-install/harbor-data-values.yaml"
        },
        {
          encoding = "gz+b64"
          content  = base64gzip(file("${path.module}/../resources/prometheus-data-values.yaml"))
          path     = "/home/${var.user}/tkg-install/prometheus-data-values.yaml"
        },
        {
          encoding = "gz+b64"
          content  = base64gzip(file("${path.module}/../resources/tsm-registration.yaml"))
          path     = "/home/${var.user}/tkg-install/tsm-registration.yaml"
        },
        {
          encoding = "gz+b64"
          content  = base64gzip(file("${path.module}/../resources/to-registration.yaml"))
          path     = "/home/${var.user}/tkg-install/to-registration.yaml"
        },
        {
          encoding = "gz+b64"
          content  = base64gzip(file("${path.module}/../resources/finish-install.sh"))
          path     = "/home/${var.user}/tkg-install/finish-install.sh"
        },
        {
          encoding = "gz+b64"
          content  = base64gzip(file("${path.module}/../resources/clean-up.sh"))
          path     = "/home/${var.user}/tkg-install/clean-up.sh"
        }
      ]
    })
  }

  dynamic "part" {
    for_each = local.cluster_types
    content {
      content_type = "text/tanzu"
      filename     = "${part.value}-${local.cloud_yaml["CLUSTER-NAME-${part.value}"]}.yaml"
      content = templatefile("${path.module}/config.yaml.tftpl", merge(local.cloud_yaml, {
        AZURE-CONTROL-PLANE-SUBNET-CIDR = local.cloud_yaml["AZURE-CONTROL-PLANE-SUBNET-CIDR-${part.value}"],
        AZURE-CONTROL-PLANE-SUBNET-NAME = local.cloud_yaml["AZURE-CONTROL-PLANE-SUBNET-NAME-${part.value}"],
        AZURE-NODE-SUBNET-CIDR          = local.cloud_yaml["AZURE-NODE-SUBNET-CIDR-${part.value}"],
        AZURE-NODE-SUBNET-NAME          = local.cloud_yaml["AZURE-NODE-SUBNET-NAME-${part.value}"],
        CLUSTER-NAME                    = local.cloud_yaml["CLUSTER-NAME-${part.value}"],
        AZURE-FRONTEND-PRIVATE-IP       = cidrhost(local.cloud_yaml["AZURE-CONTROL-PLANE-SUBNET-CIDR-${part.value}"], 4)
      }))
    }
  }
}

data "azurerm_key_vault_secrets" "this" {
  key_vault_id = data.azurerm_key_vault.this.id
}

data "azurerm_key_vault_secret" "this" {
  for_each = toset(data.azurerm_key_vault_secrets.this.names)

  name         = each.key
  key_vault_id = data.azurerm_key_vault.this.id
}
