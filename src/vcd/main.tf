terraform {
  required_providers {
    vcd = {
      source = "vmware/vcd"
      version = "3.8.0"
    }
  }
}



module "org" {
  source = "./org"
  org_details = local.org_configs
}

module "org-vdc" {
  #depends_on = [module.org]
  source = "./org-vdc"
  org_vdc_details = local.org_vdc_configs
}

module "nsx-alb-res" {
  source = "./nsx-alb-res"
  avi_alb_details = local.avi_alb_configs
}

module "networks" {
  #depends_on = [module.org]
  source = "./networks"
  vcd_t0_gtw_details = local.vcd_t0_gtw_configs
  vcd_t1_gtw_details = local.vcd_t1_gtw_configs
  vcd_net_details    = local.vcd_net_configs
  org_details = local.org_configs
  org_vdc_details = local.org_vdc_configs
  avi_alb_details = local.avi_alb_configs
  nsxt_manager_name = local.nsxtManagerName
  create_t1_gtw = local.create_t1_gtw
  create_vcd_rtd_net = local.create_vcd_rtd_net
}


module "catalog" {
  #depends_on = [module.org]
  source = "./catalog"
  org_details = local.org_configs
  catalog_details = local.catalog_configs
  k8s_catalog_name = local.k8s_catalog_name
}

module "cse-config" {
  source = "./cse-config"
  cse_config_details = local.cse_server_configs
}

module "vapp" {
  source = "./vapp"
  org_details = local.org_configs
  cse_server_details = local.cse_server_configs
  org_vdc_details = local.org_vdc_configs
}
