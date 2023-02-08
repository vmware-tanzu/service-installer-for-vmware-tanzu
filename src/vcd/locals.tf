locals {

  all_json_configs = jsondecode(file("tf-input.json"))
  org_configs = local.all_json_configs.envSpec.cseSpec.svcOrgSpec
  org_vdc_configs = merge(local.all_json_configs.envSpec.cseSpec.svcOrgVdcSpec, local.all_json_configs.envSpec.cseSpec.svcOrgSpec)
  vcd_configs = local.all_json_configs.envSpec.vcdSpec.vcdComponentSpec

  avi_fqdn_configs = {
    deployAvi   = local.all_json_configs.envSpec.aviCtrlDeploySpec.deployAvi
  }
  avi_var = jsondecode(file("/opt/vmware/arcas/src/vcd/avi.json"))
  aviFqdn = local.avi_var.aviFqdn ###populate AVI FQDN###

  input_var = jsondecode(file("/opt/vmware/arcas/src/vcd/vars.tfvars.json"))
  avi_alb_configs = {
    import_ctrl = local.input_var.import_ctrl  ##true/false##
    import_cloud = local.input_var.import_cloud  ##true/false##
    import_seg = local.input_var.import_seg ##true/false##
    org_name = local.all_json_configs.envSpec.cseSpec.svcOrgSpec.svcOrgName
    aviVcdDisplayName = local.all_json_configs.envSpec.aviCtrlDeploySpec.aviVcdDisplayName

    aviUrl = format("%s%s","https://",local.aviFqdn)
    aviUsername = local.all_json_configs.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviUsername
    aviPasswordBase64 = local.all_json_configs.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviPasswordBase64
    aviNsxCloudName = local.all_json_configs.envSpec.aviNsxCloudSpec.aviNsxCloudName
    nsxtCloudVcdDisplayName = local.all_json_configs.envSpec.aviNsxCloudSpec.nsxtCloudVcdDisplayName
    avi_se_group_details = local.all_json_configs.envSpec.cseSpec.svcOrgVdcSpec.serviceEngineGroup

  }
  nsx = jsondecode(file("/opt/vmware/arcas/src/vcd/var_nsx.json"))
  nsxtManagerName = local.nsx.nsxManager ###populate nsxt-manager name by making an api call to vcd###

  vcd_t0_gtw_configs = local.all_json_configs.envSpec.cseSpec.svcOrgVdcSpec.svcOrgVdcGatewaySpec.tier0GatewaySpec
  vcd_t1_gtw_configs = local.all_json_configs.envSpec.cseSpec.svcOrgVdcSpec.svcOrgVdcGatewaySpec.tier1GatewaySpec
  vcd_net_configs     = local.all_json_configs.envSpec.cseSpec.svcOrgVdcSpec.svcOrgVdcNetworkSpec

  net = jsondecode(file("/opt/vmware/arcas/src/vcd/net.json"))
  create_t1_gtw = local.net.create_t1_gtw ##true/false##
  create_vcd_rtd_net = local.net.create_vcd_rtd_net ##true/false##

  k8s_catalog_name = local.all_json_configs.envSpec.cseSpec.svcOrgVdcSpec.svcOrgCatalogSpec.k8sTemplatCatalogName

  catalog = jsondecode(file("/opt/vmware/arcas/src/vcd/cseconfig.json"))
  catalog_k8 = jsondecode(file("/opt/vmware/arcas/src/vcd/kconfig.json"))
  catalog_configs = {

     cse_configs = {
       create_catalog = local.catalog.create_catalog  ##true/false##
       upload_ova    = local.catalog.upload_ova  ##true/false##
       catalog_name       = local.all_json_configs.envSpec.cseSpec.svcOrgVdcSpec.svcOrgCatalogSpec.cseOvaCatalogName
       catalog_item_name  = local.catalog.catalog_item_name ##ova_name##
       ova_path          =  local.catalog.ova_path ##path##
     }
  
     k8s_configs = {
       create_catalog = local.catalog_k8.create_catalog_k8s  ##true/false##
       upload_ova    = local.catalog_k8.upload_ova_k8s   ##true/false##
       catalog_name       = local.all_json_configs.envSpec.cseSpec.svcOrgVdcSpec.svcOrgCatalogSpec.k8sTemplatCatalogName
       catalog_item_name  = local.catalog_k8.catalog_item_name_k8s ##ova_name##
       ova_path          = local.catalog_k8.ova_path_k8s ##path##
     }
  }
  cse_server = jsondecode(file("/opt/vmware/arcas/src/vcd/cse_server.json"))
  cse_server_configs = {
    username = local.all_json_configs.envSpec.cseSpec.cseServerDeploySpec.customCseProperties.cseSvcAccountName
    password = local.all_json_configs.envSpec.cseSpec.cseServerDeploySpec.customCseProperties.cseSvcAccountPasswordBase64
    token    = local.cse_server.token  ###token-value##
    vapp_name = local.all_json_configs.envSpec.cseSpec.cseServerDeploySpec.vAppName
    vapp_vm_name = "Cse-srv-vm"
    org_network_name = local.all_json_configs.envSpec.cseSpec.svcOrgVdcSpec.svcOrgVdcNetworkSpec.networkName
    vcd_host = format("%s%s", "https://", local.vcd_configs.vcdAddress)
    catalog_name = local.all_json_configs.envSpec.cseSpec.svcOrgVdcSpec.svcOrgCatalogSpec.cseOvaCatalogName
    template_name = local.cse_server.template_name  ###uploaded_template_name###

  }
}

