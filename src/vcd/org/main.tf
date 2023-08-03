terraform {
  required_providers {
    vcd = {
      source = "vmware/vcd"
      version = "3.8.0"
    }
  }
}

resource "vcd_org" "org" {
    
  name                          = var.org_details.svcOrgName
  full_name                     = var.org_details.svcOrgFullName
  can_publish_catalogs          = can(var.org_details.publishCatalogs) ? var.org_details.publishCatalogs : "true"
  can_publish_external_catalogs = can(var.org_details.publishExternally) ? var.org_details.publishExternally: "true"
  is_enabled                    = can(var.org_details.isEnabled) ? var.org_details.isEnabled: "true"
  delete_recursive              = can(var.org_details.deleteRecursive) ? var.org_details.deleteRecursive : "true"
  delete_force                  = can(var.org_details.deleteForce) ? var.org_details.deleteForce : "true"

  vapp_lease {
    maximum_runtime_lease_in_sec          = 0 # never expires
    power_off_on_runtime_lease_expiration = false
    maximum_storage_lease_in_sec          = 0 # never expires
    delete_on_storage_lease_expiration    = false
  }
}
