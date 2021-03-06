# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
/* Global Values */
variable "sub_id" {
  description = "The subscription ID where these resources should be built."
}

variable "prefix" {
  default     = "vmw-use2-netsec"
  description = "The prefix used for all infrastructure objects.  i.e. '<prefix>-vnet' or '<prefix>-web-nsg' "
}

variable "prefix_short" {
  default     = "vmwuse2netsec"
  description = "This prefix is an abbreviated version of 'prefix' but designed for lower max character names. The short prefix should be a maximum of 8 chars (alpha-numeric)"
}

variable "location" {
  default     = "eastus2"
  description = "The region/location where these resources will be deployed."
}

/* VNet settings */

variable "core_address_space" {
  default     = "10.1.2.0/24"
  description = "Transit subnet range.  Range for small subnets used transit networks (generally to FWs)"
}

variable "boot_diag_sa_name" {
  default     = "" # handled in locals unless specified here
  description = "The storage account name to be created for holding boot diag data for firewalls as well as NSG Flow logs."
}

variable "additional_tags" {
  default = {
    ServiceName  = "TKGm Reference Architecture"
    OwnerEmail   = "tanzu@vmware.com"
    BusinessUnit = "MAPBU"
    Environment  = "Testing"
  }
}

variable "dns_list" {
  type        = list(string)
  default     = []
  description = "A list of IP addresses which, if needed, should probably match an on-prem or cloud-based target of DNS servers or load balancer(s) to allow for on-prem resolution."
}

variable "vault_resource_group_name" {
  default = ""
}

variable "vault_name" {
  default = ""
}

variable "CreateNetworkWatcher" {
  type        = number
  default     = 0
  description = "Affects the creation of a Network Watcher for the VNet.  0 = No, 1 = Yes"
}

variable "CreateNetworkWatcherRG" {
  type        = number
  default     = 0
  description = "Affects the creation of a Network Watcher Resource Group for the VNet.  0 = No, 1 = Yes"
}

variable "tkg_cluster_name" {
  default = "vmw-use2-tkgm"
}

variable "ipAcl" {
  default     = ""
  description = "The IP/CIDR to be used for the Storage Account and KeyVault.  If left blank, the local executor's IP address will be used."
}

variable "create_nat_gateway" {
  default     = true
  description = "This boolean controls whether a NAT Gateway is configured and attached to all the subnets of this VNET. It is necessary if this is a private cluster TKG install, as well as if there is no proxy or routing established to redirect Internet traffic."
  type        = bool
}
