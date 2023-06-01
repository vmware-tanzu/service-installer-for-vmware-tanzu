terraform {
  required_providers {
    vcd = {
      source = "vmware/vcd"
      version = "3.8.0"
    }
  }
}

resource "vcd_org_user" "org_user" {
  org = "System"

  name        = var.cse_config_details.username
  description = "cse admin"
  role        = "CSE Admin Role"
  password    = base64decode(var.cse_config_details.password)
  depends_on  = [vcd_role.cse_role]

}

resource "vcd_role" "cse_role" {
    description = "Used for administrative purposes"
    name        = "CSE Admin Role"
    org         = "System"
    rights      = [
        "API Tokens: Manage",
        "vmware:VCDKEConfig: Administrator Full access",
        "vmware:VCDKEConfig: Administrator View",
        "vmware:VCDKEConfig: Full Access",
        "vmware:VCDKEConfig: Modify",
        "vmware:VCDKEConfig: View",
        "vmware:capvcdCluster: Administrator Full access",
        "vmware:capvcdCluster: Administrator View",
        "vmware:capvcdCluster: Full Access",
        "vmware:capvcdCluster: Modify",
        "vmware:capvcdCluster: View",
    ]
}
resource "vcd_global_role" "kube_global_role" {
    description            = "Assign this role to a user to manage Kubernetes clusters"
    name                   = "Kubernetes Cluster Author"
    publish_to_all_tenants = true
    rights                 = [
        "API Tokens: Manage",
        "Access All Organization VDCs",
        "Catalog: Add vApp from My Cloud",
        "Catalog: View Private and Shared Catalogs",
        "Catalog: View Published Catalogs",
        "Certificate Library: View",
        "Organization vDC Compute Policy: View",
        "Organization vDC Gateway: Configure Load Balancer",
        "Organization vDC Gateway: Configure NAT",
        "Organization vDC Gateway: View",
        "Organization vDC Gateway: View Load Balancer",
        "Organization vDC Gateway: View NAT",
        "Organization vDC Named Disk: Create",
        "Organization vDC Named Disk: Delete",
        "Organization vDC Named Disk: Edit Properties",
        "Organization vDC Named Disk: View Encryption Status",
        "Organization vDC Named Disk: View Properties",
        "Organization vDC Network: View Properties",
        "Organization vDC Shared Named Disk: Create",
        "Organization vDC: VM-VM Affinity Edit",
        "Organization: View",
        "UI Plugins: View",
        "VAPP_VM_METADATA_TO_VCENTER",
        "vApp Template / Media: Copy",
        "vApp Template / Media: Edit",
        "vApp Template / Media: View",
        "vApp Template: Checkout",
        "vApp: Allow All Extra Config",
        "vApp: Copy",
        "vApp: Create / Reconfigure",
        "vApp: Delete",
        "vApp: Download",
        "vApp: Edit Properties",
        "vApp: Edit VM CPU",
        "vApp: Edit VM Compute Policy",
        "vApp: Edit VM Hard Disk",
        "vApp: Edit VM Memory",
        "vApp: Edit VM Network",
        "vApp: Edit VM Properties",
        "vApp: Manage VM Password Settings",
        "vApp: Power Operations",
        "vApp: Sharing",
        "vApp: Snapshot Operations",
        "vApp: Upload",
        "vApp: Use Console",
        "vApp: VM Boot Options",
        "vApp: View ACL",
        "vApp: View VM and VM's Disks Encryption Status",
        "vApp: View VM metrics",
        "vmware:capvcdCluster: Full Access",
        "vmware:capvcdCluster: Modify",
        "vmware:capvcdCluster: View",
        "vmware:tkgcluster: Full Access",
        "vmware:tkgcluster: Modify",
        "vmware:tkgcluster: View",
    ]
}
resource "vcd_rights_bundle" "kube_cluster_bundle" {
    description            = "Rights bundle with required rights for managing Kubernetes clusters"
    name                   = "Kubernetes Clusters Rights Bundle"
    publish_to_all_tenants = true
    rights                 = [
        "API Tokens: Manage",
        "Access All Organization VDCs",
        "Catalog: View Published Catalogs",
        "Certificate Library: Manage",
        "Certificate Library: View",
        "General: Administrator View",
        "Organization vDC Gateway: Configure Load Balancer",
        "Organization vDC Gateway: Configure NAT",
        "Organization vDC Gateway: View",
        "Organization vDC Gateway: View Load Balancer",
        "Organization vDC Gateway: View NAT",
        "Organization vDC Named Disk: Create",
        "Organization vDC Named Disk: Edit Properties",
        "Organization vDC Named Disk: View Properties",
        "Organization vDC Shared Named Disk: Create",
        "vApp: Allow All Extra Config",
        "vmware:capvcdCluster: Administrator Full access",
        "vmware:capvcdCluster: Administrator View",
        "vmware:capvcdCluster: Full Access",
        "vmware:capvcdCluster: Modify",
        "vmware:capvcdCluster: View",
        "vmware:tkgcluster: Administrator Full access",
        "vmware:tkgcluster: Administrator View",
        "vmware:tkgcluster: Full Access",
        "vmware:tkgcluster: Modify",
        "vmware:tkgcluster: View",
    ]
}
/*# Kubernetes Cluster Author
resource "vcd_rights_bundle" "vcdke_bundle" {
    description            = "vmware:VCDKEConfig rights bundle containing view, modify and full access rights."
    name                   = "vmware:VCDKEConfig Entitlement"
    publish_to_all_tenants = false
    rights                 = [
        "vmware:VCDKEConfig: Administrator Full access",
        "vmware:VCDKEConfig: Administrator View",
        "vmware:VCDKEConfig: Full Access",
        "vmware:VCDKEConfig: Modify",
        "vmware:VCDKEConfig: View",
    ]
}

resource "vcd_rights_bundle" "capvcd_bundle" {
    description            = "vmware:capvcdCluster rights bundle containing view, modify and full access rights."
    name                   = "vmware:capvcdCluster Entitlement"
    publish_to_all_tenants = false
    rights                 = [
        "vmware:capvcdCluster: Administrator Full access",
        "vmware:capvcdCluster: Administrator View",
        "vmware:capvcdCluster: Full Access",
        "vmware:capvcdCluster: Modify",
        "vmware:capvcdCluster: View",
    ]
}*/

