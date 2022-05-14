import json

from common.constants.constants import ComponentPrefix, FirewallRulePrefix, NsxtScopes, NsxtServicePaths, \
    VmcNsxtGateways
from common.constants.nsxt_api_constants import NsxTPayload
from common.lib.nsxt_client import NsxtClient
from common.model.vmcSpec import VmcMasterSpec
from common.operation.constants import Env, SegmentsName, GroupNameCgw


class NsxtWorkflow:
    def __init__(self, spec, config, logger):
        self.run_config = config
        self.spec: VmcMasterSpec = spec
        self.nsxt_client: NsxtClient = NsxtClient(self.run_config)
        self.logger = logger

    def _get_segments_from_spec(self):
        """
        Get mapping of segment names and their config details from input config spec.
        :return: dict containing mapping of segment names to the segment spec from the input config spec.
        """
        self.logger.info("Get mapping of segment names and their config details from input config spec.")
        segments = dict()
        segments[SegmentsName.DISPLAY_NAME_AVI_MANAGEMENT] = {
            "gateway_cidr": self.spec.componentSpec.aviMgmtNetworkSpec.aviMgmtGatewayCidr,
            "dhcp_start": self.spec.componentSpec.aviMgmtNetworkSpec.aviMgmtDhcpStartRange,
            "dhcp_end": self.spec.componentSpec.aviMgmtNetworkSpec.aviMgmtDhcpEndRange
        }
        # This segment is pre-created. We just add it here so we get the object path
        segments[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName] = {
            "gateway_cidr": self.spec.componentSpec.tkgMgmtSpec.tkgMgmtGatewayCidr,
            "dhcp_start": "",
            "dhcp_end": ""
        }
        segments[SegmentsName.DISPLAY_NAME_AVI_DATA_SEGMENT] = {
            "gateway_cidr": self.spec.componentSpec.tkgMgmtDataNetworkSpec.tkgMgmtDataGatewayCidr,
            "dhcp_start": self.spec.componentSpec.tkgMgmtDataNetworkSpec.tkgMgmtDataDhcpStartRange,
            "dhcp_end": self.spec.componentSpec.tkgMgmtDataNetworkSpec.tkgMgmtDataDhcpEndRange
        }
        segments[SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment] = {
            "gateway_cidr": self.spec.componentSpec.tkgSharedServiceSpec.tkgSharedGatewayCidr,
            "dhcp_start": self.spec.componentSpec.tkgSharedServiceSpec.tkgSharedDhcpStartRange,
            "dhcp_end": self.spec.componentSpec.tkgSharedServiceSpec.tkgSharedDhcpEndRange
        }
        segments[SegmentsName.DISPLAY_NAME_CLUSTER_VIP] = {
            "gateway_cidr": self.spec.componentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkGatewayCidr,
            "dhcp_start": self.spec.componentSpec.tkgClusterVipNetwork.tkgClusterVipDhcpStartRange,
            "dhcp_end": self.spec.componentSpec.tkgClusterVipNetwork.tkgClusterVipDhcpEndRange
        }
        return segments

    def _create_segments(self):
        """
        Create required segments on NSX-T.
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
                    seg_details = self.nsxt_client.create_segment("cgw", segment_id,
                                                                  gateway_cidr=details['gateway_cidr'],
                                                                  dhcp_start=details['dhcp_start'],
                                                                  dhcp_end=details['dhcp_end'],
                                                                  dns_servers=self.spec.envVariablesSpec.dnsServersIp.split(
                                                                      ', '))
                    segment_paths[segment_id] = NsxtClient.get_object_path(seg_details)
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
            paths=json.dumps([segment_paths[SegmentsName.DISPLAY_NAME_AVI_MANAGEMENT]]))
        groups[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName] = NsxTPayload.PATH_EXPRESSION.format(
            paths=json.dumps([segment_paths[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName]]))
        groups[GroupNameCgw.DISPLAY_NAME_TKG_Management_Network_Group_CGW] = NsxTPayload.PATH_EXPRESSION.format(
            paths=json.dumps([segment_paths[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName]]))
        groups[GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW] = NsxTPayload.PATH_EXPRESSION.format(
            paths=json.dumps([segment_paths[SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment]]))
        groups[GroupNameCgw.DISPLAY_NAME_CLUSTER_VIP_NETWORK_Group_CGW] = NsxTPayload.PATH_EXPRESSION.format(
            paths=json.dumps([segment_paths[SegmentsName.DISPLAY_NAME_CLUSTER_VIP]]))
        if gateway_id == VmcNsxtGateways.CGW:
            groups[ComponentPrefix.DNS_IPS] = NsxTPayload.IP_ADDRESS_EXPRESSION.format(
                ip_addresses=json.dumps(self.spec.envVariablesSpec.dnsServersIp.split(', ')))
            groups[ComponentPrefix.NTP_IPS] = NsxTPayload.IP_ADDRESS_EXPRESSION.format(
                ip_addresses=json.dumps(self.spec.envVariablesSpec.ntpServersIp.split(', ')))
            groups[ComponentPrefix.VC_IP] = NsxTPayload.IP_ADDRESS_EXPRESSION.format(
                ip_addresses=json.dumps([self.run_config['VC_IP']]))
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
                ser_details = self.nsxt_client.create_service(service_id=service_id,
                                                              service_entry_name=ComponentPrefix.KUBE_VIP_SERVICE_ENTRY)
                service_paths[service_id] = NsxtClient.get_object_path(ser_details)
            else:
                service_paths[service_id] = NsxtClient.get_object_path(service)
                self.logger.info(f"Service [{service_id}] already exists. Skipping creation.")
        except Exception as ex:
            self.logger.error(f"Failed to create service: {ComponentPrefix.KUBE_VIP_SERVICE}")
            raise ex
        return service_paths

    def _get_firewall_rules(self, gateway_id: VmcNsxtGateways, group_paths, service_paths):
        """
        Get mapping of rule names and their configuration details
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
                "source": [grp_paths[GroupNameCgw.DISPLAY_NAME_AVI_Management_Network_Group_CGW],
                           grp_paths[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName],
                           grp_paths[GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW]],
                "destination": [grp_paths[ComponentPrefix.NTP_IPS]],
                "scope": [NsxtScopes.CGW_ALL],
                "services": [NsxtServicePaths.NTP]
            }
            rules[FirewallRulePrefix.INFRA_TO_DNS] = {
                "source": [grp_paths[GroupNameCgw.DISPLAY_NAME_AVI_Management_Network_Group_CGW],
                           grp_paths[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName],
                           grp_paths[GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW]],
                "destination": [grp_paths[ComponentPrefix.DNS_IPS]],
                "scope": [NsxtScopes.CGW_ALL],
                "services": [NsxtServicePaths.DNS, NsxtServicePaths.DNS_UDP]
            }
            rules[FirewallRulePrefix.INFRA_TO_VC] = {
                "source": [grp_paths[GroupNameCgw.DISPLAY_NAME_AVI_Management_Network_Group_CGW],
                           grp_paths[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName],
                           grp_paths[GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW]],
                "destination": [grp_paths[ComponentPrefix.VC_IP]],
                "scope": [NsxtScopes.CGW_ALL],
                "services": [NsxtServicePaths.HTTPS]
            }
            rules[FirewallRulePrefix.INFRA_TO_ANY] = {
                "source": [grp_paths[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName],
                           grp_paths[GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW]],
                "destination": ["ANY"],
                "scope": [NsxtScopes.CGW_ALL],
                "services": [NsxtServicePaths.ANY]
            }
            rules[FirewallRulePrefix.INFRA_TO_ALB] = {
                "source": [grp_paths[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName],
                           grp_paths[GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW]],
                "destination": [grp_paths[GroupNameCgw.DISPLAY_NAME_AVI_Management_Network_Group_CGW]],
                "scope": [NsxtScopes.CGW_ALL],
                "services": [NsxtServicePaths.HTTPS,NsxtServicePaths.ICMP]
            }
            rules[FirewallRulePrefix.INFRA_TO_CLUSTER_VIP] = {
                "source": [grp_paths[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName],
                           grp_paths[GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW]],
                "destination": [grp_paths[GroupNameCgw.DISPLAY_NAME_CLUSTER_VIP_NETWORK_Group_CGW]],
                "scope": [NsxtScopes.CGW_ALL],
                "services": [service_paths[ComponentPrefix.KUBE_VIP_SERVICE]]
            }
        else:
            rules[FirewallRulePrefix.INFRA_TO_VC] = {
                "source": [grp_paths[GroupNameCgw.DISPLAY_NAME_AVI_Management_Network_Group_CGW],
                           grp_paths[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName],
                           grp_paths[GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW]],
                "destination": [grp_paths[ComponentPrefix.VCENTER]],
                "scope": [NsxtScopes.MGW],
                "services": [NsxtServicePaths.HTTPS]
            }
            rules[FirewallRulePrefix.MGMT_TO_ESXI] = {
                "source": [grp_paths[self.spec.componentSpec.tkgMgmtSpec.tkgMgmtNetworkName]],
                "destination": [grp_paths[ComponentPrefix.ESXI]],
                "scope": [NsxtScopes.MGW],
                "services": [NsxtServicePaths.HTTPS]
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
                    else:
                        self.logger.info(
                            f"Firewall rule [{rule_id}] already exists on {gw_id} gateway. Skipping creation.")
            except Exception as ex:
                self.logger.error(f"Failed to create firewall rules on {gw_id} gateway")
                raise ex

    def execute_workflow(self):
        if not self.run_config['DEPLOYMENT_PLATFORM'] == Env.VMC:
            self.logger.info("Not a VMC deployment. Skipping NSX-T configurations..")
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
