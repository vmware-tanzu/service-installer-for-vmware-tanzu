terraform {
  required_providers {
    vcd = {
      source = "vmware/vcd"
      version = "3.8.0"
    }
  }
}

resource "vcd_catalog" "catalog" {
  for_each         = { for entry in var.catalog_details : "${entry.catalog_name}" => entry if entry.create_catalog == "true" }
  org              = var.org_details.svcOrgName

  name             = each.value.catalog_name
  delete_recursive = can(each.value.delete_recursive) ? each.value.delete_recursive : true
  delete_force     = can(each.value.delete_force) ? each.value.delete_force : true
#  publish_enabled  = can(each.value.publish_enabled) ? each.value.publish_enabled : true

}

resource "vcd_catalog_access_control" "AC-global" {
  depends_on = [vcd_catalog.catalog[0], vcd_catalog.catalog[1]]
  org  =  var.org_details.svcOrgName
  for_each         = { for entry in var.catalog_details : "${entry.catalog_name}" => entry if entry.create_catalog == "true" }
  catalog_id = vcd_catalog.catalog[each.value.catalog_name].id
  shared_with_everyone  = true
  everyone_access_level = "ReadOnly"
}

resource "vcd_catalog_item" "catalog_item" {
  depends_on           = [vcd_catalog.catalog]
  for_each             = { for entry in var.catalog_details : "${entry.catalog_item_name}" => entry if entry.upload_ova == "true" }
  org                  = var.org_details.svcOrgName
  catalog              = each.value.catalog_name

  name                 = each.value.catalog_item_name
  ova_path             = each.value.ova_path
  upload_piece_size    = can(each.value.upload_piece_size) ? each.value.upload_piece_size : 10
  show_upload_progress = can(each.value.show_upload_progress) ? each.value.show_upload_progress : true

}

