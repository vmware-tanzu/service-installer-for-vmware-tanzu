provider "vcd" {
  user     = local.vcd_configs.vcdSysAdminUserName
  password = base64decode(local.vcd_configs.vcdSysAdminPasswordBase64)
  org      = "System"
  url      = format("%s%s%s", "https://", local.vcd_configs.vcdAddress, "/api")
  allow_unverified_ssl = true
}

