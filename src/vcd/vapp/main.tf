terraform {
  required_providers {
    vcd = {
      source = "vmware/vcd"
      version = "3.8.0"
    }
  }
}


data "vcd_catalog" "my-catalog" {
  org  = var.org_details.svcOrgName
  name = var.cse_server_details.catalog_name
}


data "vcd_catalog_vapp_template" "cse-ova" {
  org        = var.org_details.svcOrgName
  catalog_id = data.vcd_catalog.my-catalog.id
  name       = var.cse_server_details.template_name
}

resource "vcd_vapp" "vapp" {
    name        = var.cse_server_details.vapp_name
    org         = var.org_details.svcOrgName
    vdc         = var.org_vdc_details.svcOrgVdcName
}

resource "vcd_vapp_org_network" "routed-net" {
  org         = var.org_details.svcOrgName
  vdc         = var.org_vdc_details.svcOrgVdcName
  vapp_name        = vcd_vapp.vapp.name
  org_network_name = var.cse_server_details.org_network_name
}

resource "vcd_vapp_vm" "vapp_vm" {
    depends_on        = [vcd_vapp.vapp]
    #computer_name                  = "csesrv"
    vapp_template_id  = data.vcd_catalog_vapp_template.cse-ova.id
    guest_properties               = {
        "userOrg"     = "system"
        "vAppOrg"     = var.org_details.svcOrgName
        "vcdHost"     = var.cse_server_details.vcd_host
        "vcdUsername" = var.cse_server_details.username
        "vcdRefreshToken" = var.cse_server_details.token
    }
    name                           = var.cse_server_details.vapp_vm_name
    org                            =  var.org_details.svcOrgName
    #os_type                        = "vmwarePhoton64Guest"
    #storage_profile                = "vSAN Default Storage Policy"
    vapp_name                      = var.cse_server_details.vapp_name
    vdc                            = var.org_vdc_details.svcOrgVdcName

    network {
        name               = vcd_vapp_org_network.routed-net.org_network_name
        type               = "org"
        ip_allocation_mode = "POOL"

    }

}
