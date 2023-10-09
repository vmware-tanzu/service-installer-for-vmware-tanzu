# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import json

from common.common_utilities import get_ip_address, getESXIips, getIpFromHost, is_ipv4
from common.constants.constants import (
    ComponentPrefix,
    FirewallRulePrefix,
    NsxtScopes,
    NsxtServicePaths,
    VmcNsxtGateways,
)
from common.constants.nsxt_api_constants import NsxTPayload, NsxWorkflows
from common.lib.nsxt_client import NsxtClient
from common.model.vcfSpec import VcfMasterSpec
from common.model.vmcSpec import VmcMasterSpec
from common.operation.constants import (
    VCF,
    Env,
    FirewallRuleCgw,
    GroupNameCgw,
    Policy_Name,
    Ports,
    SegmentsName,
    ServiceName,
)


class NsxtWorkflow:
    """Class Constructor"""

    def __init__(self, spec, config, logger):
        self.run_config = config
        if config["DEPLOYMENT_PLATFORM"] == Env.VMC:
            self.spec: VmcMasterSpec = spec
        else:
            self.spec: VcfMasterSpec = spec
        self.nsxt_client: NsxtClient = NsxtClient(self.run_config, self.spec)
        self.logger = logger

    def _get_segments_from_spec(self):
        """
        Get mapping of segment names and their config details from input config spec for VMC environment.
        :return: dict containing mapping of segment names to the segment spec from the input config spec.
        """
        self.logger.info("Get mapping of segment names and their config details from input config spec.")
        segments = dict()
        segments[SegmentsName.DISPLAY_NAME_AVI_MANAGEMENT] = {
            "gateway_cidr": self.spec.componentSpec.aviMgmtNetworkSpec.aviMgmtGatewayCidr,
            "dhcp_start": self.spec.componentSpec.aviMgmtNetworkSpec.aviMgmtDhcpStartRange,
            "dhcp_end": self.spec.componentSpec.aviMgmtNetworkSpec.aviMgmtDhcpEndRange,
        }
        # This segment is pre-created. We just add it here so we get the object path
        segments[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName] = {
            "gateway_cidr": self.spec.componentSpec.tkgMgmtSpec.tkgMgmtGatewayCidr,
            "dhcp_start": "",
            "dhcp_end": "",
        }
        segments[SegmentsName.DISPLAY_NAME_AVI_DATA_SEGMENT] = {
            "gateway_cidr": self.spec.componentSpec.tkgMgmtDataNetworkSpec.tkgMgmtDataGatewayCidr,
            "dhcp_start": self.spec.componentSpec.tkgMgmtDataNetworkSpec.tkgMgmtDataDhcpStartRange,
            "dhcp_end": self.spec.componentSpec.tkgMgmtDataNetworkSpec.tkgMgmtDataDhcpEndRange,
        }
        segments[SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment] = {
            "gateway_cidr": self.spec.componentSpec.tkgSharedServiceSpec.tkgSharedGatewayCidr,
            "dhcp_start": self.spec.componentSpec.tkgSharedServiceSpec.tkgSharedDhcpStartRange,
            "dhcp_end": self.spec.componentSpec.tkgSharedServiceSpec.tkgSharedDhcpEndRange,
        }
        segments[SegmentsName.DISPLAY_NAME_CLUSTER_VIP] = {
            "gateway_cidr": self.spec.componentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkGatewayCidr,
            "dhcp_start": self.spec.componentSpec.tkgClusterVipNetwork.tkgClusterVipDhcpStartRange,
            "dhcp_end": self.spec.componentSpec.tkgClusterVipNetwork.tkgClusterVipDhcpEndRange,
        }
        return segments

    def _get_segments_from_vcf_spec(self, workflow):
        """
        Get mapping of segment names and their config details from input config spec for VCF environment.
        :return: dict containing mapping of segment names to the segment spec from the input config spec.
        """
        self.logger.info("Get mapping of segment names and their config details from input config spec.")
        segments = dict()
        if workflow == NsxWorkflows.WORKLOAD:
            segments[self.spec.tkgWorkloadComponents.tkgWorkloadNetworkName] = {
                "gateway_cidr": self.spec.tkgWorkloadComponents.tkgWorkloadGatewayCidr,
                "dhcp_start": self.spec.tkgWorkloadComponents.tkgWorkloadDhcpStartRange,
                "dhcp_end": self.spec.tkgWorkloadComponents.tkgWorkloadDhcpEndRange,
                "dhcp_enabled": True,
            }
        # else:
        segments[self.spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedserviceNetworkName] = {
            "gateway_cidr": self.spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedserviceGatewayCidr,
            "dhcp_start": self.spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedserviceDhcpStartRange,
            "dhcp_end": self.spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedserviceDhcpEndRange,
            "dhcp_enabled": True,
        }
        # This segment is pre-created. We just add it here so we get the object path
        segments[self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtNetworkName] = {
            "gateway_cidr": self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtGatewayCidr,
            "dhcp_start": "",
            "dhcp_end": "",
        }
        segments[self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkName] = {
            "gateway_cidr": self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkGatewayCidr,
            "dhcp_start": self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipIpStartRange,
            "dhcp_end": self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipIpEndRange,
            "dhcp_enabled": False,
        }
        segments[self.spec.tkgComponentSpec.aviMgmtNetwork.aviMgmtNetworkName] = {
            "gateway_cidr": self.spec.tkgComponentSpec.aviMgmtNetwork.aviMgmtNetworkGatewayCidr,
            "dhcp_start": self.spec.tkgComponentSpec.aviMgmtNetwork.aviMgmtServiceIpStartRange,
            "dhcp_end": self.spec.tkgComponentSpec.aviMgmtNetwork.aviMgmtServiceIpEndRange,
            "dhcp_enabled": False,
        }
        return segments

    def _create_segments(self):
        """
        Create required segments on NSX-T for VMC.
        :return: dict mapping ComponentPrefix with respective segment paths
        """
        self.logger.info("Create required segments on NSX-T")
        # Get segments to create
        segments = self._get_segments_from_spec()
        nsxt_segments = self.nsxt_client.list_segments(VmcNsxtGateways.CGW)
        segment_paths = dict()
        try:
            for segment_id, details in segments.items():
                self.logger.info(f"Checking if segment exists with id: {segment_id}")
                segment = NsxtClient.find_object(nsxt_segments, segment_id)
                if not segment:
                    self.logger.info(f"Segment [{segment_id}] not found.")
                    seg_details = self.nsxt_client.create_segment(
                        "cgw",
                        segment_id,
                        gateway_cidr=details["gateway_cidr"],
                        dhcp_start=details["dhcp_start"],
                        dhcp_end=details["dhcp_end"],
                        dns_servers=self.spec.envVariablesSpec.dnsServersIp.split(", "),
                    )
                    segment_paths[segment_id] = NsxtClient.get_object_path(seg_details)
                    self.logger.info(f"Segment [{segment_id}] created successfully.")
                else:
                    segment_paths[segment_id] = NsxtClient.get_object_path(segment)
                    self.logger.info(f"Segment [{segment_id}] already exists. Skipping creation.")
        except Exception as ex:
            self.logger.error("Failed to create segments.")
            raise ex
        return segment_paths

    def _create_vcf_segments(self, workflow):
        """
        Create required segments on NSX-T for VCF.
        :return: dict mapping ComponentPrefix with respective segment paths
        """
        self.logger.info("Create required segments on NSX-T")
        # Get segments to create
        segments = self._get_segments_from_vcf_spec(workflow)
        tier1 = self.nsxt_client.get_tier1_details(self.spec.envSpec.vcenterDetails.nsxtTier1RouterDisplayName)
        transport_zone = self.nsxt_client.get_transport_zone(self.spec.envSpec.vcenterDetails.nsxtOverlay)
        nsxt_segments = self.nsxt_client.list_segments(None)
        segment_paths = dict()
        try:
            for segment_id, details in segments.items():
                self.logger.info(f"Checking if segment exists with id: {segment_id}")
                segment = NsxtClient.find_vcf_object(nsxt_segments, segment_id)
                if segment is None:
                    self.logger.info(f"Segment [{segment_id}] not found.")
                    seg_details = self.nsxt_client.create_segment(
                        None,
                        segment_id,
                        gateway_cidr=details["gateway_cidr"],
                        dhcp_start=details["dhcp_start"],
                        dhcp_end=details["dhcp_end"],
                        dhcp_enabled=details["dhcp_enabled"],
                        dns_servers=self.spec.envSpec.infraComponents.dnsServersIp.split(", "),
                        ntp_servers=self.spec.envSpec.infraComponents.ntpServers.split(","),
                        transport=transport_zone,
                        tier1=tier1,
                        network=self.nsxt_client.get_network_ip(details["gateway_cidr"]),
                    )
                    segment_paths[segment_id] = NsxtClient.get_object_path(seg_details)
                    self.logger.info(f"Segment [{segment_id}] created successfully.")
                else:
                    segment_paths[segment_id] = NsxtClient.get_object_path(segment)
                    self.logger.info(f"Segment [{segment_id}] already exists. Skipping creation.")
        except Exception as ex:
            self.logger.error("Failed to create segments.")
            raise ex
        return segment_paths

    def _get_groups(self, gateway_id: VmcNsxtGateways, segment_paths):
        """
        Get mapping of group and their config details from input config spec
        :param gateway_id: gateway ID for which the mapping is needed.
        :param segment_paths: dict mapping segment names to the segment paths
        :return: dict mapping group names to the group membership expression spec.
        """
        self.logger.info("Get mapping of group and their config details from input config spec.")
        groups = dict()
        groups[GroupNameCgw.DISPLAY_NAME_AVI_Management_Network_Group_CGW] = NsxTPayload.PATH_EXPRESSION.format(
            paths=json.dumps([segment_paths[SegmentsName.DISPLAY_NAME_AVI_MANAGEMENT]])
        )
        groups[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName] = NsxTPayload.PATH_EXPRESSION.format(
            paths=json.dumps([segment_paths[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName]])
        )
        groups[GroupNameCgw.DISPLAY_NAME_TKG_Management_Network_Group_CGW] = NsxTPayload.PATH_EXPRESSION.format(
            paths=json.dumps([segment_paths[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName]])
        )
        groups[GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW] = NsxTPayload.PATH_EXPRESSION.format(
            paths=json.dumps([segment_paths[SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment]])
        )
        groups[GroupNameCgw.DISPLAY_NAME_CLUSTER_VIP_NETWORK_Group_CGW] = NsxTPayload.PATH_EXPRESSION.format(
            paths=json.dumps([segment_paths[SegmentsName.DISPLAY_NAME_CLUSTER_VIP]])
        )
        if gateway_id == VmcNsxtGateways.CGW:
            groups[ComponentPrefix.DNS_IPS] = NsxTPayload.IP_ADDRESS_EXPRESSION.format(
                ip_addresses=json.dumps(self.spec.envVariablesSpec.dnsServersIp.split(", "))
            )
            groups[ComponentPrefix.NTP_IPS] = NsxTPayload.IP_ADDRESS_EXPRESSION.format(
                ip_addresses=json.dumps(self.spec.envVariablesSpec.ntpServersIp.split(", "))
            )
            groups[ComponentPrefix.VC_IP] = NsxTPayload.IP_ADDRESS_EXPRESSION.format(
                ip_addresses=json.dumps([self.run_config["VC_IP"]])
            )
        return groups

    def _create_groups(self, segment_paths):
        """
        Create required inventory groups on NSX-T
        :param segment_paths: dict containing mapping of segment names to the segment paths
        :return: dict mapping group names to respective object paths
        """
        self.logger.info("Create required inventory groups on NSX-T.")
        group_paths = dict()
        for gw_id in (VmcNsxtGateways.CGW, VmcNsxtGateways.MGW):
            try:
                group_paths[gw_id] = dict()
                groups = self._get_groups(gw_id, segment_paths)
                nsxt_groups = self.nsxt_client.list_groups(gw_id)
                for group_id, details in groups.items():
                    group = NsxtClient.find_object(nsxt_groups, group_id)
                    if not group:
                        self.logger.info(f"Group [{group_id}] not found.")
                        grp_details = self.nsxt_client.create_group(gw_id, group_id, expression=details)
                        group_paths[gw_id][group_id] = NsxtClient.get_object_path(grp_details)
                        self.logger.info(f"Group [{group_id}] created successfully.")
                    else:
                        group_paths[gw_id][group_id] = NsxtClient.get_object_path(group)
                        self.logger.info(f"Group [{group_id}] already exists. Skipping creation.")
            except Exception as ex:
                self.logger.error(f"Failed to create groups on {gw_id} gateway")
                raise ex
        return group_paths

    def _create_services(self):
        """
        Create required services on NSX-T
        :return: dict mapping service names to object paths
        """
        self.logger.info("Create required services on NSX-T")
        service_paths = dict()
        try:
            self.logger.info(f"Checking if {ComponentPrefix.KUBE_VIP_SERVICE} service exists.")
            services = self.nsxt_client.list_services()
            service_id = ComponentPrefix.KUBE_VIP_SERVICE
            service = NsxtClient.find_object(services, service_id)
            if not service:
                self.logger.info("Creating NSX-T service for accessing kube API on port 6443")
                ser_details = self.nsxt_client.create_service(
                    service_id=service_id, service_entry_name=ComponentPrefix.KUBE_VIP_SERVICE_ENTRY
                )
                service_paths[service_id] = NsxtClient.get_object_path(ser_details)
                self.logger.info(f"Service [{service_id}] created successfully")
            else:
                service_paths[service_id] = NsxtClient.get_object_path(service)
                self.logger.info(f"Service [{service_id}] already exists. Skipping creation.")
        except Exception as ex:
            self.logger.error(f"Failed to create service: {ComponentPrefix.KUBE_VIP_SERVICE}")
            raise ex
        return service_paths

    def _get_firewall_rules(self, gateway_id: VmcNsxtGateways, group_paths, service_paths):
        """
        Get mapping of rule names and their configuration details for VMC environment
        :param gateway_id: gateway object ID for creating the firewall rules
        :param group_paths: dict mapping group names to object paths
        :param service_paths: dict mapping service names to service paths
        :return: dict mapping rule names with configuration details
        """
        self.logger.info("Get mapping of rule names and their configuration details")
        rules = dict()
        grp_paths = group_paths[gateway_id]
        if gateway_id == VmcNsxtGateways.CGW:
            rules[FirewallRulePrefix.INFRA_TO_NTP] = {
                "source": [
                    grp_paths[GroupNameCgw.DISPLAY_NAME_AVI_Management_Network_Group_CGW],
                    grp_paths[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName],
                    grp_paths[GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW],
                ],
                "destination": [grp_paths[ComponentPrefix.NTP_IPS]],
                "scope": [NsxtScopes.CGW_ALL],
                "services": [NsxtServicePaths.NTP],
            }
            rules[FirewallRulePrefix.INFRA_TO_DNS] = {
                "source": [
                    grp_paths[GroupNameCgw.DISPLAY_NAME_AVI_Management_Network_Group_CGW],
                    grp_paths[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName],
                    grp_paths[GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW],
                ],
                "destination": [grp_paths[ComponentPrefix.DNS_IPS]],
                "scope": [NsxtScopes.CGW_ALL],
                "services": [NsxtServicePaths.DNS, NsxtServicePaths.DNS_UDP],
            }
            rules[FirewallRulePrefix.INFRA_TO_VC] = {
                "source": [
                    grp_paths[GroupNameCgw.DISPLAY_NAME_AVI_Management_Network_Group_CGW],
                    grp_paths[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName],
                    grp_paths[GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW],
                ],
                "destination": [grp_paths[ComponentPrefix.VC_IP]],
                "scope": [NsxtScopes.CGW_ALL],
                "services": [NsxtServicePaths.HTTPS],
            }
            rules[FirewallRulePrefix.INFRA_TO_ANY] = {
                "source": [
                    grp_paths[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName],
                    grp_paths[GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW],
                ],
                "destination": ["ANY"],
                "scope": [NsxtScopes.CGW_ALL],
                "services": [NsxtServicePaths.ANY],
            }
            rules[FirewallRulePrefix.INFRA_TO_ALB] = {
                "source": [
                    grp_paths[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName],
                    grp_paths[GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW],
                ],
                "destination": [grp_paths[GroupNameCgw.DISPLAY_NAME_AVI_Management_Network_Group_CGW]],
                "scope": [NsxtScopes.CGW_ALL],
                "services": [NsxtServicePaths.HTTPS, NsxtServicePaths.ICMP],
            }
            rules[FirewallRulePrefix.INFRA_TO_CLUSTER_VIP] = {
                "source": [
                    grp_paths[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName],
                    grp_paths[GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW],
                ],
                "destination": [grp_paths[GroupNameCgw.DISPLAY_NAME_CLUSTER_VIP_NETWORK_Group_CGW]],
                "scope": [NsxtScopes.CGW_ALL],
                "services": [service_paths[ComponentPrefix.KUBE_VIP_SERVICE]],
            }
        else:
            rules[FirewallRulePrefix.INFRA_TO_VC] = {
                "source": [
                    grp_paths[GroupNameCgw.DISPLAY_NAME_AVI_Management_Network_Group_CGW],
                    grp_paths[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName],
                    grp_paths[GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW],
                ],
                "destination": [grp_paths[ComponentPrefix.VCENTER]],
                "scope": [NsxtScopes.MGW],
                "services": [NsxtServicePaths.HTTPS],
            }
            rules[FirewallRulePrefix.MGMT_TO_ESXI] = {
                "source": [grp_paths[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName]],
                "destination": [grp_paths[ComponentPrefix.ESXI]],
                "scope": [NsxtScopes.MGW],
                "services": [NsxtServicePaths.HTTPS],
            }
        return rules

    def _create_gateway_firewall_rules(self, group_paths, service_paths):
        """
        Create required gateway firewall rules.
        :param group_paths: dict mapping group names to object paths
        :param service_paths: dict mapping service names to service paths
        :return: None
        """
        self.logger.info("Create required gateway firewall rules.")
        for gw_id in (VmcNsxtGateways.CGW, VmcNsxtGateways.MGW):
            try:
                rules = self._get_firewall_rules(gw_id, group_paths, service_paths)
                nsxt_rules = self.nsxt_client.list_gateway_firewall_rules(gw_id)
                for rule_id, details in rules.items():
                    if not NsxtClient.find_object(nsxt_rules, rule_id):
                        self.nsxt_client.create_gateway_firewall_rule(gw_id, rule_id, **details)
                        self.logger.info(f"Firewall rule [{rule_id}] created successfully on {gw_id} gateway.")
                    else:
                        self.logger.info(
                            f"Firewall rule [{rule_id}] already exists on {gw_id} gateway. Skipping creation."
                        )
            except Exception as ex:
                self.logger.error(f"Failed to create firewall rules on {gw_id} gateway")
                raise ex

    def _create_dhcp_server(self):
        """
        Create DHCP server on NSX Manager
        :return: dict mapping servers to object paths
        """
        self.logger.info("Create DHCP server on NSX-T")
        try:
            servers = self.nsxt_client.list_dhcp_servers()
            dhcp_present = self.nsxt_client.find_dhcp_object(servers)
            if not dhcp_present:
                self.logger.info("Creating DHCP server on NSX manager")
                servers = self.nsxt_client.create_dhcp_server()
            else:
                self.logger.info("DHCP server is already present in tier1")
        except Exception as ex:
            self.logger.error("Failed to create DHCP server in tier1")
            raise ex
        return servers

    def _get_vcf_groups(self, workflow):
        """
        Get mapping of group and their config details from input config spec for VCF environment
        :return: dict mapping group names to the group membership expression spec.
        """
        groups = dict()
        ip = get_ip_address("eth0")
        esx_ips = getESXIips()
        vcenter = self.spec.envSpec.vcenterDetails.vcenterAddress
        if not is_ipv4(vcenter):
            vcenter = getIpFromHost(vcenter)
            if vcenter is None:
                raise Exception("Failed to fetch vCenter IP address")
        if workflow == NsxWorkflows.WORKLOAD:
            groups[GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW] = {
                "segment": self.spec.tkgWorkloadComponents.tkgWorkloadNetworkName,
                "is_ip": False,
                "ip_address": None,
            }
        # Retain this to get paths for groups which were created as part of initial vcf pre-config
        groups[VCF.ARCAS_GROUP] = {"segment": None, "is_ip": True, "ip_address": ip}
        groups[GroupNameCgw.DISPLAY_NAME_VCF_AVI_Management_Network_Group_CGW] = {
            "segment": self.spec.tkgComponentSpec.aviMgmtNetwork.aviMgmtNetworkName,
            "is_ip": False,
            "ip_address": None,
        }
        groups[GroupNameCgw.DISPLAY_NAME_VCF_CLUSTER_VIP_NETWORK_Group_CGW] = {
            "segment": self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkName,
            "is_ip": False,
            "ip_address": None,
        }
        groups[GroupNameCgw.DISPLAY_NAME_VCF_TKG_SharedService_Group_CGW] = {
            "segment": self.spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedserviceNetworkName,
            "is_ip": False,
            "ip_address": None,
        }
        groups[GroupNameCgw.DISPLAY_NAME_VCF_TKG_Management_Network_Group_CGW] = {
            "segment": self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtNetworkName,
            "is_ip": False,
            "ip_address": None,
        }
        groups[GroupNameCgw.DISPLAY_NAME_VCF_TKG_Management_Network_Group_CGW] = {
            "segment": self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtNetworkName,
            "is_ip": False,
            "ip_address": None,
        }
        groups[GroupNameCgw.DISPLAY_NAME_VCF_DNS_IPs_Group] = {
            "segment": None,
            "is_ip": True,
            "ip_address": self.spec.envSpec.infraComponents.dnsServersIp,
        }
        groups[GroupNameCgw.DISPLAY_NAME_VCF_NTP_IPs_Group] = {
            "segment": None,
            "is_ip": True,
            "ip_address": self.spec.envSpec.infraComponents.ntpServers,
        }
        groups[GroupNameCgw.DISPLAY_NAME_VCF_vCenter_IP_Group] = {
            "segment": None,
            "is_ip": True,
            "ip_address": vcenter,
        }
        groups[VCF.ESXI_GROUP] = {"segment": None, "is_ip": True, "ip_address": esx_ips[0]}
        groups[VCF.NSXT_GROUP] = {
            "segment": None,
            "is_ip": True,
            "ip_address": self.spec.envSpec.vcenterDetails.nsxtAddress,
        }
        return groups

    def _get_vcf_services(self):
        """
        Get mapping of service and their config details from input config spec for VCF environment
        :return: dict mapping services names to the group membership expression spec.
        """
        services = dict()
        services[ServiceName.ARCAS_SVC] = {"port": Ports.UI}
        services[ServiceName.ARCAS_BACKEND_SVC] = {"port": Ports.BACKEND}
        services[ServiceName.KUBE_VIP_VCF_SERVICE] = {"port": Ports.KUBE_VIP}
        return services

    def _create_vcf_groups(self, segment_paths, workflow):
        """
        Create required inventory groups on NSX-T for VCF environment
        :param segment_paths: dict containing mapping of segment names to the segment paths
        :return: dict mapping group names to respective object paths
        """
        self.logger.info("Create required inventory groups on NSX-T.")
        group_paths = dict()
        try:
            groups = self._get_vcf_groups(workflow)
            domain_name = self.nsxt_client.get_domain_name("default")
            nsxt_groups = self.nsxt_client.list_groups(domain_name)
            for group_id, details in groups.items():
                group = NsxtClient.find_vcf_object(nsxt_groups, group_id)
                if group is None:
                    group_paths[group_id] = self.nsxt_client.create_group_vcf(
                        group_id,
                        details["segment"],
                        details["is_ip"],
                        details["ip_address"],
                        segment_paths,
                        nsxt_groups,
                    )
                    self.logger.info(f"Group [{group_id}] created successfully.")
                else:
                    group_paths[group_id] = NsxtClient.get_object_path(group)
                    self.logger.info(f"Group [{group_id}] already exists. Skipping creation.")
        except Exception as ex:
            self.logger.error("Failed to create group on gateway")
            raise ex
        return group_paths

    def _create_vcf_services(self):
        """
        Create required services on NSX-T for VCF environment
        :return: dict mapping service names to object paths
        """
        self.logger.info("Create required services on NSX-T")
        service_paths = dict()
        list_services = self._get_vcf_services()
        for service_id, details in list_services.items():
            try:
                self.logger.info(f"Checking if {service_id} service exists.")
                services = self.nsxt_client.list_services()
                # service_id = ComponentPrefix.KUBE_VIP_SERVICE
                service = NsxtClient.find_vcf_object(services, service_id)
                if not service:
                    self.logger.info("Creating NSX-T service for accessing kube API on port 6443")
                    ser_details = self.nsxt_client.create_service(
                        service_id=service_id, name=service_id, port=details["port"]
                    )
                    service_paths[service_id] = NsxtClient.get_object_path(ser_details)
                else:
                    service_paths[service_id] = NsxtClient.get_object_path(service)
                    self.logger.info(f"Service [{service_id}] already exists. Skipping creation.")
            except Exception as ex:
                self.logger.error(f"Failed to create service: {service_id}")
                raise ex
        return service_paths

    def _create_policy(self, tier1):
        """
        Create policy on NSX-T
        :param tier1: tier1 string for creating the policy
        :return: path of the policy created
        """
        self.logger.info("Create required policies on NSX-T")
        try:
            self.logger.info(f"Checking if {Policy_Name.POLICY_NAME} service exists.")
            policies = self.nsxt_client.list_policies()
            policy_id = Policy_Name.POLICY_NAME
            policy = NsxtClient.find_vcf_object(policies, policy_id)
            if policy is None:
                self.logger.info(f"Creating {policy_id} policy")
                self.nsxt_client.create_policy(policy_id=policy_id, tier_path=tier1)
                self.logger.info(f"{policy_id} policy created successfully")
            else:
                self.logger.info(f"Policy [{policy_id}] already exists. Skipping creation.")
        except Exception as ex:
            self.logger.error(f"Failed to create policy: {Policy_Name.POLICY_NAME}")
            raise ex

    def _get_vcf_firewall_rules(self, group_paths, workflow):
        """
        Get mapping of rule names and their configuration details for VCF environment
        :param group_paths: dict mapping group names to object paths
        :return: dict mapping rule names with configuration details
        """
        rules = dict()
        if workflow == NsxWorkflows.WORKLOAD:
            rules[FirewallRuleCgw.DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_DNS] = {
                "source_groups": [
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW],
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_TKG_Management_Network_Group_CGW],
                ],
                "destination_groups": [
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_DNS_IPs_Group],
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_NTP_IPs_Group],
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW],
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_CLUSTER_VIP_NETWORK_Group_CGW],
                ],
                "services": [
                    "/infra/services/DNS",
                    "/infra/services/DNS-UDP",
                    "/infra/services/NTP",
                    "/infra/services/" + ServiceName.KUBE_VIP_VCF_SERVICE,
                ],
            }
            rules[FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_WORKLOAD_to_vCenter] = {
                "source_groups": [
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW],
                ],
                "destination_groups": [group_paths[GroupNameCgw.DISPLAY_NAME_VCF_vCenter_IP_Group]],
                "services": ["/infra/services/HTTPS"],
            }
            rules[FirewallRuleCgw.DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_to_Internet] = {
                "source_groups": [
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW],
                ],
                "destination_groups": ["ANY"],
                "services": ["ANY"],
            }
        else:
            rules[FirewallRuleCgw.DISPLAY_NAME_VCF_ARCAS_UI] = {
                "source_groups": ["ANY"],
                "destination_groups": [group_paths[VCF.ARCAS_GROUP]],
                "services": ["/infra/services/SSH", "/infra/services/" + ServiceName.ARCAS_SVC],
            }
            rules[FirewallRuleCgw.DISPLAY_NAME_VCF_ARCAS_BACKEND] = {
                "source_groups": ["ANY"],
                "destination_groups": [group_paths[VCF.ARCAS_GROUP]],
                "services": ["/infra/services/" + ServiceName.ARCAS_BACKEND_SVC],
            }
            rules[FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_AVI_DNS] = {
                "source_groups": [
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_AVI_Management_Network_Group_CGW],
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_TKG_Management_Network_Group_CGW],
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_TKG_SharedService_Group_CGW],
                ],
                "destination_groups": [group_paths[GroupNameCgw.DISPLAY_NAME_VCF_DNS_IPs_Group]],
                "services": ["/infra/services/DNS", "/infra/services/DNS-UDP"],
            }
            rules[FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_AVI_NTP] = {
                "source_groups": [
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_AVI_Management_Network_Group_CGW],
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_TKG_Management_Network_Group_CGW],
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_TKG_SharedService_Group_CGW],
                ],
                "destination_groups": [group_paths[GroupNameCgw.DISPLAY_NAME_VCF_NTP_IPs_Group]],
                "services": ["/infra/services/NTP"],
            }
            rules[FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_AVI_to_vCenter] = {
                "source_groups": [
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_AVI_Management_Network_Group_CGW],
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_TKG_Management_Network_Group_CGW],
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_TKG_SharedService_Group_CGW],
                ],
                "destination_groups": [group_paths[GroupNameCgw.DISPLAY_NAME_VCF_vCenter_IP_Group]],
                "services": ["/infra/services/HTTPS"],
            }
            rules[VCF.ESXI_FW] = {
                "source_groups": [
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_AVI_Management_Network_Group_CGW],
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_TKG_Management_Network_Group_CGW],
                ],
                "destination_groups": [group_paths[VCF.ESXI_GROUP]],
                "services": ["/infra/services/HTTPS"],
            }
            rules[FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_AVI_to_Internet] = {
                "source_groups": [
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_TKG_Management_Network_Group_CGW],
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_TKG_SharedService_Group_CGW],
                ],
                "destination_groups": ["ANY"],
                "services": ["ANY"],
            }
            rules[FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_TKGtoAVIMgmt] = {
                "source_groups": [
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_TKG_Management_Network_Group_CGW],
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_TKG_SharedService_Group_CGW],
                ],
                "destination_groups": [group_paths[GroupNameCgw.DISPLAY_NAME_VCF_AVI_Management_Network_Group_CGW]],
                "services": ["/infra/services/HTTPS", "/infra/services/ICMP-ALL"],
            }
            rules["Alb"] = {
                "source_groups": ["ANY"],
                "destination_groups": [group_paths[GroupNameCgw.DISPLAY_NAME_VCF_AVI_Management_Network_Group_CGW]],
                "services": ["/infra/services/HTTPS"],
            }
            rules["alb-to-nsx"] = {
                "source_groups": [group_paths[GroupNameCgw.DISPLAY_NAME_VCF_AVI_Management_Network_Group_CGW]],
                "destination_groups": [group_paths[VCF.NSXT_GROUP]],
                "services": ["/infra/services/HTTPS"],
            }
            rules[FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_AVIMgmt] = {
                "source_groups": [group_paths[GroupNameCgw.DISPLAY_NAME_VCF_AVI_Management_Network_Group_CGW]],
                "destination_groups": [
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_NTP_IPs_Group],
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_DNS_IPs_Group],
                ],
                "services": ["/infra/services/DNS", "/infra/services/NTP"],
            }
            rules[FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_CLUSTER_VIP_CGW] = {
                "source_groups": [
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_TKG_Management_Network_Group_CGW],
                    group_paths[GroupNameCgw.DISPLAY_NAME_VCF_TKG_SharedService_Group_CGW],
                ],
                "destination_groups": [group_paths[GroupNameCgw.DISPLAY_NAME_VCF_CLUSTER_VIP_NETWORK_Group_CGW]],
                "services": ["/infra/services/" + ServiceName.KUBE_VIP_VCF_SERVICE],
            }
        return rules

    def _create_vcf_firewall_rules_and_policies(self, group_paths, tier1, workflow):
        """
        Create policy and firewall rules on NSX-T for VCF environment
        :param group_paths: dict mapping group names to object paths
        :param tier1: tier1 details of NSX-T
        :return: None
        """
        policy = Policy_Name.POLICY_NAME
        self.logger.info("Create required gateway firewall rules.")
        try:
            rules = self._get_vcf_firewall_rules(group_paths, workflow)
            nsxt_rules = self.nsxt_client.list_gateway_firewall_rules(None, gw_policy_id=policy)
            for rule_id, details in rules.items():
                if not NsxtClient.find_vcf_object(nsxt_rules, rule_id):
                    self.nsxt_client.create_vcf_gateway_firewall_rule(policy, tier1, rule_id, **details)
                    self.logger.info(f"Firewall rule [{rule_id}] created successfully on {tier1} gateway")
                else:
                    self.logger.info(f"Firewall rule [{rule_id}] already exists on {tier1} gateway. Skipping creation.")
        except Exception as ex:
            self.logger.error("Failed to create firewall rules on gateway")
            raise ex

    def execute_workflow(self):
        """
        Execute NSX-T Pre-configuration flow for VMC environment
        :return: Success if flow executes successfully
        """
        if not self.run_config["DEPLOYMENT_PLATFORM"] == Env.VMC:
            self.logger.info("Not a NSX based deployment. Skipping NSX-T configurations..")
            return

        # Create logical segments
        segment_paths = self._create_segments()

        # Create inventory groups
        group_paths = self._create_groups(segment_paths)

        # Include existing group paths
        mgw_groups = self.nsxt_client.list_groups(VmcNsxtGateways.MGW)
        esxi_group = NsxtClient.find_object(mgw_groups, ComponentPrefix.ESXI)
        group_paths[VmcNsxtGateways.MGW][ComponentPrefix.ESXI] = NsxtClient.get_object_path(esxi_group)

        vcenter_group = NsxtClient.find_object(mgw_groups, ComponentPrefix.VCENTER)
        group_paths[VmcNsxtGateways.MGW][ComponentPrefix.VCENTER] = NsxtClient.get_object_path(vcenter_group)

        # Create inventory services
        service_paths = self._create_services()

        # Create gateway firewall rules
        self._create_gateway_firewall_rules(group_paths, service_paths)

    def execute_workflow_vcf(self, workflow=NsxWorkflows.MANAGEMENT):
        """
        Execute NSX-T Pre-configuration flow for VCF environment
        :return: Success if flow executes successfully
        """
        if not self.run_config["DEPLOYMENT_PLATFORM"] == Env.VCF:
            self.logger.info("Not an NSX based deployment. Skipping NSX-T configurations..")
            return

        # check if tier1 details are existing
        tier1 = self.nsxt_client.get_tier1_details(self.spec.envSpec.vcenterDetails.nsxtTier1RouterDisplayName)

        # Create DHCP server for VCF env
        # self._create_dhcp_server()

        # Create logical segments
        segment_paths = self._create_vcf_segments(workflow)

        # Create inventory groups
        group_paths = self._create_vcf_groups(segment_paths, workflow)

        # Create inventory services
        self._create_vcf_services()

        # Create policy
        self._create_policy(tier1)

        # Create gateway firewall rules
        self._create_vcf_firewall_rules_and_policies(group_paths, tier1, workflow)
