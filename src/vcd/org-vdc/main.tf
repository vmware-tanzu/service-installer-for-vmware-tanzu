terraform {
  required_providers {
    vcd = {
      source = "vmware/vcd"
      version = "3.8.0"
    }
  }
}

resource "vcd_org_vdc" "org-vdc" {

  name                 = var.org_vdc_details.svcOrgVdcName
  org                  = var.org_vdc_details.svcOrgName

  allocation_model     = can(var.org_vdc_details.svcOrgVdcResourceSpec.allocationModel) ? var.org_vdc_details.svcOrgVdcResourceSpec.allocationModel : "Flex"
  network_pool_name    = var.org_vdc_details.svcOrgVdcResourceSpec.networkPoolName
  provider_vdc_name    = var.org_vdc_details.svcOrgVdcResourceSpec.providerVDC

  network_quota        = var.org_vdc_details.svcOrgVdcResourceSpec.networkQuota
  vm_quota             = var.org_vdc_details.svcOrgVdcResourceSpec.vmQuota
  cpu_speed            = can(var.org_vdc_details.svcOrgVdcResourceSpec.vcpuSpeed) ? (var.org_vdc_details.svcOrgVdcResourceSpec.vcpuSpeed*1000) :  "1000"
  memory_guaranteed    = format("0.%d", var.org_vdc_details.svcOrgVdcResourceSpec.memoryGuaranteed)
  cpu_guaranteed       = format("0.%d", var.org_vdc_details.svcOrgVdcResourceSpec.cpuGuaranteed)

  dynamic "storage_profile" {
    for_each = var.org_vdc_details.svcOrgVdcResourceSpec.storagePolicySpec.storagePolicies
    content {
      default            = var.org_vdc_details.svcOrgVdcResourceSpec.storagePolicySpec.defaultStoragePolicy == storage_profile.value.storagePolicy ? true : false
      enabled            = can(storage_profile.value.enabled) ? storage_profile.value.enabled : true
      limit              = can(storage_profile.value.storageLimit) ? (storage_profile.value.storageLimit*1024) : "204800"
      name               = storage_profile.value.storagePolicy
    }
  }
  compute_capacity {
     cpu {
          allocated = can(var.org_vdc_details.svcOrgVdcResourceSpec.cpuAllocation) ? (var.org_vdc_details.svcOrgVdcResourceSpec.cpuAllocation*1000) : "10000"
          limit     = can(var.org_vdc_details.svcOrgVdcResourceSpec.cpuLimit) ? var.org_vdc_details.svcOrgVdcResourceSpec.cpuLimit : "0"
        }

     memory {
          allocated = can(var.org_vdc_details.svcOrgVdcResourceSpec.memoryAllocation) ? (var.org_vdc_details.svcOrgVdcResourceSpec.memoryAllocation*1024) : "20480"
          limit     = can(var.org_vdc_details.svcOrgVdcResourceSpec.memoryLimit) ? var.org_vdc_details.svcOrgVdcResourceSpec.memoryLimit : "0"
        }
  }

  enable_thin_provisioning   = var.org_vdc_details.svcOrgVdcResourceSpec.thinProvisioning
  enable_fast_provisioning   = var.org_vdc_details.svcOrgVdcResourceSpec.fastProvisioning
  elasticity                 = var.org_vdc_details.svcOrgVdcResourceSpec.isElastic
  include_vm_memory_overhead = var.org_vdc_details.svcOrgVdcResourceSpec.includeMemoryOverhead

  enabled                  = can(var.org_vdc_details.svcOrgVdcResourceSpec.enabled) ? var.org_vdc_details.svcOrgVdcResourceSpec.enabled : null
  delete_force             = can(var.org_vdc_details.svcOrgVdcResourceSpec.delete_force) ? var.org_vdc_details.svcOrgVdcResourceSpec.delete_force : true
  delete_recursive         = can(var.org_vdc_details.svcOrgVdcResourceSpec.delete_recursive) ? var.org_vdc_details.svcOrgVdcResourceSpec.delete_recursive : true
  enable_vm_discovery      = can(var.org_vdc_details.svcOrgVdcResourceSpec.enable_vm_discovery) ? var.org_vdc_details.svcOrgVdcResourceSpec.enable_vm_discovery : null


  lifecycle {
    ignore_changes = all
  }

}
