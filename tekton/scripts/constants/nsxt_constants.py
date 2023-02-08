#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

from enum import Enum

class Policy_Name:
    POLICY_NAME = "tkg-vsphere-nsxt-policy"

class VCF:
    DHCP_SERVER_NAME = "tkg-vsphere-nsxt-dhcp-server"
    ARCAS_GROUP = "arcas"
    ARCAS_BACKEND_GROUP = "arcas_backend"
    ESXI_GROUP = "tkg-vsphere-nsxt-esxi"
    ESXI_FW = "tkg-vsphere-nsxt-tkg-esxi"

class GroupNameCgw:
    DISPLAY_NAME_AVI_Management_Network_Group_CGW = "tkgvmc-avimgmt"
    DISPLAY_NAME_CLUSTER_VIP_NETWORK_Group_CGW = "tkgvmc-tkgclustervip"
    DISPLAY_NAME_TKG_Management_Network_Group_CGW = "tkgvmc-tkgmgmt"
    DISPLAY_NAME_TKG_Workload_Networks_Group_CGW = "tkgvmc-tkg-workload"
    DISPLAY_NAME_TKG_SharedService_Group_CGW = "tkgvmc-shared-service"
    DISPLAY_NAME_DNS_IPs_Group = "tkgvmc-infra-dns-ips"
    DISPLAY_NAME_NTP_IPs_Group = "tkgvmc-infra-ntp-ips"
    DISPLAY_NAME_TKG_Management_ControlPlane_IPs = "tkgvmc-tkgmgmt-controlplane-ip"
    DISPLAY_NAME_TKG_Workload_ControlPlane_IPs = "TKG-Workload-ControlPlane-IPs_automation"
    DISPLAY_NAME_TKG_Shared_Cluster_Control_Plane_IP = "tkgvmc-shared-service-controlplane-ip"
    DISPLAY_NAME_vCenter_IP_Group = "tkgvmc-infra-vcenter-ip"

    DISPLAY_NAME_VCF_AVI_Management_Network_Group_CGW = "tkg-vsphere-nsxt-avimgmt"
    DISPLAY_NAME_VCF_TKG_Management_Network_Group_CGW = "tkg-vsphere-nsxt-tkgmgmt"
    DISPLAY_NAME_VCF_CLUSTER_VIP_NETWORK_Group_CGW = "tkg-vsphere-nsxt-tkgclustervip"
    DISPLAY_NAME_VCF_TKG_SharedService_Group_CGW = "tkg-vsphere-nsxt-shared-service"
    DISPLAY_NAME_VCF_DNS_IPs_Group = "tkg-vsphere-nsxt-infra-dns-ips"
    DISPLAY_NAME_VCF_NTP_IPs_Group = "tkgvmc-vsphere-nsxt-infra-ntp-ips"
    DISPLAY_NAME_VCF_vCenter_IP_Group = "tkgvmc-vsphere-nsxt-infra-vcenter-ip"
    DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW = "tkg-vsphere-nsxt-tkg-workload"


class FirewallRuleCgw:
    DISPLAY_NAME_TKG_and_AVI_NTP = "tkgvmc-tkginfra-to-ntp"
    DISPLAY_NAME_TKG_CLUSTER_VIP_CGW = "tkgvmc-tkgcluster-vip"
    DISPLAY_NAME_TKG_and_AVI_DNS = "tkgvmc-tkg-avi-to-dns"
    DISPLAY_NAME_WORKLOAD_TKG_and_AVI_DNS = "tkgvmc-tkgworkload01-tkginfra"
    DISPLAY_NAME_TKG_and_AVI_to_vCenter = "tkgvmc-tkg-avi-to-vcenter"
    DISPLAY_NAME_TKG_WORKLOAD_to_vCenter = "tkgvmc-tkg-workload-to-vcenter"
    DISPLAY_NAME_TKG_and_AVI_to_Internet = "tkgvmc-tkg-external"
    DISPLAY_NAME_WORKLOAD_TKG_and_AVI_to_Internet = "tkgvmc-workload-tkg-external"
    DISPLAY_NAME_TKG_and_TKGtoAVIMgmt = "tkgvmc-tkg-to-avimgmt"
    DISPLAY_NAME_TKG_Shared_Service_ControlPlaneIP_VIP = "tkgvmc-tkgmgmt-to-tkgshared-service-vip"
    DISPLAY_NAME_TKG_SharedService_TKG_Mgmt_ControlPlaneIP_VIP = "tkgvmc-tkgshared-service-to-tkgmgmt-vip"

    DISPLAY_NAME_VCF_TKG_and_AVI_DNS = "tkg-vsphere-nsxt-tkg-avi-to-dns"
    DISPLAY_NAME_VCF_TKG_CLUSTER_VIP_CGW = "tkg-vsphere-nsxt-tkgcluster-vip"
    DISPLAY_NAME_VCF_TKG_and_AVI_NTP = "tkg-vsphere-nsxt-tkginfra-to-ntp"
    DISPLAY_NAME_VCF_TKG_and_AVI_to_vCenter = "tkg-vsphere-nsxt-tkg-avi-to-vcenter"
    DISPLAY_NAME_VCF_TKG_and_AVI_to_Internet = "tkg-vsphere-nsxt-tkg-external"
    DISPLAY_NAME_VCF_TKG_and_TKGtoAVIMgmt = "tkg-vsphere-nsxt-tkg-to-avimgmt"
    DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_DNS = "tkg-vsphere-nsxt-tkgworkload01-tkginfra"
    DISPLAY_NAME_VCF_TKG_WORKLOAD_to_vCenter = "tkg-vsphere-nsxt-tkgworkload01-vcenter"
    DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_to_Internet = "tkg-vsphere-nsxt-workload-tkg-external"
    DISPLAY_NAME_VCF_ARCAS_UI = "arcas-ui"
    DISPLAY_NAME_VCF_ARCAS_BACKEND = "arcas-backend"