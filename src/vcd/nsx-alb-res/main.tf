terraform {
  required_providers {
    vcd = {
      source = "vmware/vcd"
      version = "3.8.0"
    }
  }
}


data "vcd_nsxt_alb_controller" "nsxt_alb_controller_tf" {
    count = var.avi_alb_details.import_ctrl != "true" ? 1 : 0
    name = var.avi_alb_details.aviVcdDisplayName
    depends_on = [vcd_nsxt_alb_controller.nsxt_alb_controller[0]]
}

data "vcd_nsxt_alb_importable_cloud" "nsxt_alb_importable_cloud_tf" {
   count         = (var.avi_alb_details.import_cloud == "true" && var.avi_alb_details.import_ctrl == "true") ? 1 : 0
   name          = var.avi_alb_details.aviNsxCloudName
   controller_id = vcd_nsxt_alb_controller.nsxt_alb_controller[0].id
   depends_on = [vcd_nsxt_alb_controller.nsxt_alb_controller[0]]
}


data "vcd_nsxt_alb_controller" "nsxt_alb_controller_ui" {
    count = var.avi_alb_details.import_ctrl != "true" ? 1 : 0
    name = var.avi_alb_details.aviVcdDisplayName
}

data "vcd_nsxt_alb_importable_cloud" "nsxt_alb_importable_cloud_ui" {
   count         = (var.avi_alb_details.import_cloud == "true" && var.avi_alb_details.import_ctrl != "true") ? 1 : 0
   name          = var.avi_alb_details.aviNsxCloudName
   controller_id = data.vcd_nsxt_alb_controller.nsxt_alb_controller_ui[0].id
}

resource "vcd_nsxt_alb_controller" "nsxt_alb_controller" {
  count        = var.avi_alb_details.import_ctrl == "true" ? 1 : 0
  name         = var.avi_alb_details.aviVcdDisplayName
  url          = var.avi_alb_details.aviUrl
  username     = var.avi_alb_details.aviUsername
  password     = base64decode(var.avi_alb_details.aviPasswordBase64)
  license_type = can(var.avi_alb_details.aviLicenseType) ? var.avi_alb_details.aviLicenseType : "ENTERPRISE"
  lifecycle {
    ignore_changes = all
  }
}



resource "vcd_nsxt_alb_cloud" "nsxt_alb_cloud_ui" {
  count               = (var.avi_alb_details.import_cloud == "true"  && var.avi_alb_details.import_ctrl == "false") ? 1 : 0
  name                = var.avi_alb_details.nsxtCloudVcdDisplayName

  controller_id       = data.vcd_nsxt_alb_controller.nsxt_alb_controller_ui[0].id 
  importable_cloud_id = data.vcd_nsxt_alb_importable_cloud.nsxt_alb_importable_cloud_ui[0].id
  network_pool_id     = data.vcd_nsxt_alb_importable_cloud.nsxt_alb_importable_cloud_ui[0].network_pool_id

  depends_on = [ data.vcd_nsxt_alb_controller.nsxt_alb_controller_ui[0] ]
  lifecycle {
    ignore_changes = all
  }
}

resource "vcd_nsxt_alb_cloud" "nsxt_alb_cloud_tf" {
  count               = (var.avi_alb_details.import_cloud == "true"  && var.avi_alb_details.import_ctrl == "true") ? 1 : 0
  name                = var.avi_alb_details.nsxtCloudVcdDisplayName

  controller_id       = vcd_nsxt_alb_controller.nsxt_alb_controller[0].id
  importable_cloud_id = data.vcd_nsxt_alb_importable_cloud.nsxt_alb_importable_cloud_tf[0].id
  network_pool_id     = data.vcd_nsxt_alb_importable_cloud.nsxt_alb_importable_cloud_tf[0].network_pool_id

  depends_on = [ vcd_nsxt_alb_controller.nsxt_alb_controller[0] ]
  lifecycle {
    ignore_changes = all
  }
}


resource "vcd_nsxt_alb_service_engine_group" "nsxt_alb_service_engine_group_ui" {
  count                                = (var.avi_alb_details.import_cloud == "true"  && var.avi_alb_details.import_ctrl == "false") ? 1 : 0
  name                                 = var.avi_alb_details.avi_se_group_details.serviceEngineGroupVcdDisplayName
  alb_cloud_id                         = vcd_nsxt_alb_cloud.nsxt_alb_cloud_ui[0].id
  importable_service_engine_group_name = var.avi_alb_details.avi_se_group_details.serviceEngineGroupName
  reservation_model                    = var.avi_alb_details.avi_se_group_details.reservationType
  sync_on_refresh                      = can(var.avi_alb_details.avi_se_group_details.syncOnRefresh) ? var.avi_alb_details.avi_se_group_details.syncOnRefresh : null
  supported_feature_set                = can(var.avi_alb_details.avi_se_group_details.supportedFeatureSet) ? var.avi_alb_details.avi_se_group_details.supportedFeatureSet : "PREMIUM"

  depends_on = [vcd_nsxt_alb_cloud.nsxt_alb_cloud_ui[0]]
  lifecycle {
    ignore_changes = all
  }
}

resource "vcd_nsxt_alb_service_engine_group" "nsxt_alb_service_engine_group_tf" {
  count                                = (var.avi_alb_details.import_cloud == "true"  && var.avi_alb_details.import_ctrl == "true") ? 1 : 0
  name                                 = var.avi_alb_details.avi_se_group_details.serviceEngineGroupVcdDisplayName
  alb_cloud_id                         = vcd_nsxt_alb_cloud.nsxt_alb_cloud_tf[0].id
  importable_service_engine_group_name = var.avi_alb_details.avi_se_group_details.serviceEngineGroupName
  reservation_model                    = var.avi_alb_details.avi_se_group_details.reservationType
  sync_on_refresh                      = can(var.avi_alb_details.avi_se_group_details.syncOnRefresh) ? var.avi_alb_details.avi_se_group_details.syncOnRefresh : null
  supported_feature_set                = can(var.avi_alb_details.avi_se_group_details.supportedFeatureSet) ? var.avi_alb_details.avi_se_group_details.supportedFeatureSet : "PREMIUM"

  depends_on = [vcd_nsxt_alb_cloud.nsxt_alb_cloud_tf[0]]
  lifecycle {
    ignore_changes = all
  }
}
