# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import json

import requests
from flask import current_app
from requests.models import HTTPError, Response

from common.constants.nsxt_api_constants import NsxTEndpoint, NsxTPayload, VcfPayload
from common.operation.constants import VCF, Env
from common.util.common_utils import CommonUtils


class NsxtClient:
    """
    Class Constructor
    """

    def __init__(self, config, spec=None):
        self.env = config["DEPLOYMENT_PLATFORM"]
        self.spec = spec
        if self.env == Env.VMC:
            NsxtClient._validate_vmc_run_config(config)
            self.base_url = NsxTEndpoint.VMC_BASE_URL.format(
                url=config["NSX_REVERSE_PROXY_URL"].rstrip("/"), org_id=config["ORG_ID"], sddc_id=config["SDDC_ID"]
            )
            self.access_token = config["access_token"]
            self.headers = {"Content-Type": "application/json", "csp-auth-token": self.access_token}
        elif self.env == Env.VCF:
            self.base_url = NsxTEndpoint.NSX_BASE_URL.format(url=self.spec.envSpec.vcenterDetails.nsxtAddress)
            str_enc = str(self.spec.envSpec.vcenterDetails.nsxtUserPasswordBase64)
            password = CommonUtils.decode_password(str_enc)

            ecod_string = CommonUtils.encode_password(self.spec.envSpec.vcenterDetails.nsxtUser + ":" + password)
            self.headers = {
                "Authorization": ("Basic " + ecod_string),
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        else:
            raise ValueError("Failed to initialise NsxtClient. Not implemented for VCF of vSphere")

    @staticmethod
    def _validate_vmc_run_config(config):
        """
        Validate required details needed for VMC configuration is available
        :param config: mapping of VMC details to respective values
        :return: Exception if any one the required values is not present
        """
        if not all([config["SDDC_ID"], config["NSX_REVERSE_PROXY_URL"], config["ORG_ID"], config["access_token"]]):
            raise ValueError("Failed to initialise NsxtClient. Required values not found in run config.")

    @staticmethod
    def _handle_response(response: Response):
        """
        Validate if API response is SUCCESS
        :param response: API response object
        :return: json dictionary from response object
        """
        # current_app.logger.debug(f"Response code: {response.status_code}\nResponse Body: {response.text}")
        try:
            response.raise_for_status()
        except HTTPError:
            raise Exception(f"Error while executing API: {response.text}")
        return response.json()

    @staticmethod
    def find_object(nsxt_objects, object_id):
        current_app.logger.info(f"Check if object exists with ID: {object_id}")
        return next((nsxt_object for nsxt_object in nsxt_objects if nsxt_object["id"] == object_id), None)

    @staticmethod
    def find_vcf_object(nsxt_objects, object_id):
        current_app.logger.info(f"Check if object exists with ID: {object_id}")
        return next((nsxt_object for nsxt_object in nsxt_objects if nsxt_object["display_name"] == object_id), None)

    @staticmethod
    def _generate_segment_payload(**kwargs):
        """
        Generate create segment payload for VMC environment
        :param kwargs: details needed to create segment such as gateway_id, segment name etc..
        :return: json payload
        """
        payload = NsxTPayload.CREATE_UPDATE_SEGMENT.format(
            name=kwargs["segment_id"],
            gateway=kwargs["gateway_cidr"],
            dhcp_start=kwargs["dhcp_start"],
            dhcp_end=kwargs["dhcp_end"],
            dns_servers=json.dumps(kwargs["dns_servers"]),
        )
        return payload

    @staticmethod
    def _generate_vcf_segment_payload(**kwargs):
        """
        Generate create segment payload for VCF environment
        :param kwargs: details needed to create segment such as segment name, DHCP details etc..
        :return: json payload
        """
        try:
            if kwargs["dhcp_enabled"]:
                payload = VcfPayload.CREATE_UPDATE_SEGMENT_WITH_DHCP.format(
                    name=kwargs["segment_id"],
                    gateway=kwargs["gateway_cidr"],
                    dhcp_start=kwargs["dhcp_start"],
                    dhcp_end=kwargs["dhcp_end"],
                    dns_servers=json.dumps(kwargs["dns_servers"]),
                    ntp_servers=json.dumps(kwargs["ntp_servers"]),
                    tier_path=kwargs["tier1"],
                    transport_zone=str(kwargs["transport"]),
                    network=kwargs["network"],
                )
            else:
                payload = VcfPayload.CREATE_UPDATE_SEGMENT.format(
                    name=kwargs["segment_id"],
                    gateway=kwargs["gateway_cidr"],
                    tier_path=kwargs["tier1"],
                    transport_zone=kwargs["transport"],
                )
            return payload
        except KeyError:
            raise KeyError("Required keyword missing for kwargs")

    @staticmethod
    def _generate_group_payload(**kwargs):
        """
        Generate payload needed for create Groups on NSX-T
        :param kwargs: group_id and expression
        :return: json payload
        """
        payload = NsxTPayload.CREATE_UPDATE_GROUP.format(name=kwargs["group_id"], expression=kwargs["expression"])
        return payload

    @staticmethod
    def _generate_policy_payload(**kwargs):
        """
        Generate payload needed for create policy on NSX-T
        :param kwargs: policy_id and policy_id
        :return: json payload
        """
        payload = VcfPayload.CREATE_UPDATE_POLICY.format(policy_name=kwargs["policy_id"], tier_path=kwargs["tier_path"])
        return payload

    def _generate_service_payload(self, **kwargs):
        """
        Generate payload need, ed to create services on NSX-T
        :param kwargs: env, service_entry_name, port
        :return: json payload
        """
        if self.env == Env.VMC:
            payload = NsxTPayload.CREATE_UPDATE_SERVICE.format(
                service_entry_name=json.dumps(kwargs["service_entry_name"])
            )
        else:
            payload = VcfPayload.CREATE_UPDATE_SERVICE.format(service_name=kwargs["name"], port=kwargs["port"])
        return payload

    def _generate_firewall_rule_payload(self, **kwargs):
        """
        Generate payload for create firewall rules
        :param kwargs: env, rule_id, services
        :return: json payload
        """
        if self.env == Env.VMC:
            payload = NsxTPayload.CREATE_UPDATE_FIREWALL_RULE.format(
                src_groups=json.dumps(kwargs["source"]),
                dest_groups=json.dumps(kwargs["destination"]),
                scope=json.dumps(kwargs["scope"]),
                services=json.dumps(kwargs["services"]),
            )
        else:
            payload = VcfPayload.CREATE_UPDATE_FIREWALL.format(
                rule_id=kwargs["rule_id"],
                source_groups=json.dumps(kwargs["source_groups"]),
                destination_groups=json.dumps(kwargs["destination_groups"]),
                services=json.dumps(kwargs["services"]),
                tier=kwargs["tier1"],
            )
        return payload

    @staticmethod
    def _generate_dhcp_server_payload():
        """
        Generate payload for creating DHCP server on NSX-T
        :return: json payload
        """
        payload = NsxTPayload.CREATE_DHCP_SERVER.format(
            server_name=VCF.DHCP_SERVER_NAME, server_id=VCF.DHCP_SERVER_NAME
        )
        return payload

    @staticmethod
    def get_object_path(nsxt_object):
        """
        return path for the given object
        :param nsxt_object: json object for the element
        :return: path string
        """
        return nsxt_object["path"]

    @staticmethod
    def get_segment_path(segment_list, segment_name):
        """
        Return path from json list
        :param segment_list: list of elemnts to find path
        :param segment_name: name of the object for which segment is needed
        :return: path string
        """
        return next((segment["path"] for segment in segment_list if segment["display_name"] == segment_name), None)

    @staticmethod
    def find_dhcp_object(server_list):
        """
        check DHCP server tkg-vsphere-nsxt-dhcp-server exists
        :param server_list: list from get DHCP server function
        :return: True is present, else False
        """
        current_app.logger.info(f"Checking if {VCF.DHCP_SERVER_NAME} server exists.")
        dhcp_present = False
        try:
            length = len(server_list["dhcp_config_paths"])
            if length > 0:
                dhcp_present = True
        except (KeyError, TypeError):
            pass
        if not dhcp_present:
            return next(
                (True for server_name in server_list["results"] if server_name["display_name"] == VCF.DHCP_SERVER_NAME),
                False,
            )
        else:
            return True

    def list_segments(self, gateway_id):
        """
        List all the segments from the gateway
        :param gateway_id: gateway name cgw for VMC, None for VCF
        :return: list of segments
        """
        current_app.logger.info(f"List all NSX-T segments on {gateway_id} gateway")
        url = (
            f"{self.base_url}{NsxTEndpoint.LIST_SEGMENTS[self.env].format(gw_id=gateway_id)}"
            if self.env == Env.VMC
            else f"{self.base_url}{NsxTEndpoint.LIST_SEGMENTS[self.env]}"
        )
        res = requests.get(url, headers=self.headers, verify=False)
        return NsxtClient._handle_response(res)["results"]

    def create_segment(self, gateway_id, segment_id, **kwargs):
        """
        Create NSX segment
        :param gateway_id: gateway name cgw for VMC, None fo rNSX
        :param segment_id: segment name to be created
        :return: Response JSON
        """
        current_app.logger.info("Creating NSX-T segment")
        url = f"{self.base_url}{NsxTEndpoint.CRUD_SEGMENT[self.env].format(gw_id=gateway_id, segment_id=segment_id)}"
        body = self._get_env_specific_payload(**kwargs, segment_id=segment_id)
        # body = NsxtClient.generate_segment_payload(**kwargs, segment_id=segment_id)
        res = requests.put(url, data=body, headers=self.headers, verify=False)
        return NsxtClient._handle_response(res)

    def _get_env_specific_payload(self, segment_id=None, **kwargs):
        """
        Return create segment payload for VMC or NXS env
        :param segment_id: segment name
        :return: json payload
        """
        return (
            NsxtClient._generate_segment_payload(**kwargs, segment_id=segment_id)
            if self.env == Env.VMC
            else NsxtClient._generate_vcf_segment_payload(**kwargs, segment_id=segment_id)
        )

    def list_groups(self, gateway_id):
        """
        Get list of existing groups from NSX-T
        :param gateway_id: gateway id
        :return: list of group objects from NSX-T
        """
        current_app.logger.info("Listing NSX-T inventory groups")
        url = (
            f"{self.base_url}{NsxTEndpoint.LIST_GROUPS[self.env].format(gw_id=gateway_id)}"
            if self.env == Env.VMC
            else f"{self.base_url}{NsxTEndpoint.LIST_GROUPS[self.env].format(domain_name=gateway_id)}"
        )
        res = requests.get(url, headers=self.headers, verify=False)
        return NsxtClient._handle_response(res)["results"]

    def create_group(self, gateway_id, group_id, **kwargs):
        """
        Create group on NSX-T
        :param gateway_id: name of gateway
        :param group_id: group name to be created
        :param kwargs:
        :return: return details of group created
        """
        current_app.logger.info("Creating NSX-T group")
        url = f"{self.base_url}{NsxTEndpoint.CRUD_GROUP[self.env].format(gw_id=gateway_id, group_id=group_id)}"
        body = NsxtClient._generate_group_payload(**kwargs, group_id=group_id)
        res = requests.put(url, data=body, headers=self.headers)
        return NsxtClient._handle_response(res)

    def list_services(self):
        """
        Fetch list of services from NSX-T
        :return: list of service objects
        """
        current_app.logger.info("Listing NSX-T inventory services")
        url = f"{self.base_url}{NsxTEndpoint.LIST_SERVICES}"
        res = requests.get(url, headers=self.headers, verify=False)
        return NsxtClient._handle_response(res)["results"]

    def create_service(self, service_id, **kwargs):
        """
        Create service on NSX-T
        :param service_id: name of the service to be created
        :param kwargs: service_name and port
        :return: json service object from API response
        """
        current_app.logger.info("Creating NSX-T service")
        url = f"{self.base_url}{NsxTEndpoint.CRUD_SERVICE.format(service_id=service_id)}"
        body = self._generate_service_payload(**kwargs)
        res = requests.put(url, data=body, headers=self.headers, verify=False)
        return NsxtClient._handle_response(res)

    def list_gateway_firewall_rules(self, gw_id, gw_policy_id="default"):
        """
        List gateway firewall rules from NSX-T
        :param gw_id: gateway name required for VMC
        :param gw_policy_id:  name of the policy on gateway
        :return:
        """
        current_app.logger.info("Listing gateway firewall rules")
        url = (
            f"{self.base_url}"
            f"{NsxTEndpoint.LIST_GATEWAY_FIREWALL_RULES[self.env].format(gw_id=gw_id, gw_policy_id=gw_policy_id)}"
            if self.env == Env.VMC
            else f"{self.base_url}{NsxTEndpoint.LIST_GATEWAY_FIREWALL_RULES[self.env].format(policy_name=gw_policy_id)}"
        )
        res = requests.get(url, headers=self.headers, verify=False)
        return NsxtClient._handle_response(res)["results"]

    def create_gateway_firewall_rule(self, gw_id, rule_id, gw_policy_id="default", **kwargs):
        """
        Create firewall rule on NSX-T for VMC
        :param gw_id: gateway id, needed for VMC
        :param rule_id: rule name to be created
        :param gw_policy_id: policy details
        :param kwargs:
        :return: firewall create API response
        """
        current_app.logger.info("Creating gateway firewall rule")
        api = NsxTEndpoint.CRUD_GATEWAY_FIREWALL_RULE[self.env].format(
            gw_id=gw_id, gw_policy_id=gw_policy_id, rule_id=rule_id
        )
        url = f"{self.base_url}{api}"
        body = self._generate_firewall_rule_payload(**kwargs, rule_id=rule_id)
        res = requests.put(url, data=body, headers=self.headers)
        return NsxtClient._handle_response(res)

    def create_vcf_gateway_firewall_rule(self, policy, tier, rule_id, **kwargs):
        """
        Create firewall rule on NSX-T for VCF environment
        :param policy: name of the policy
        :param tier: tier1 details
        :param rule_id: rule name to be created
        :param kwargs: source_groups, destination_groups, services and tier
        :return: API response of created firewall
        """
        current_app.logger.info("Creating gateway firewall rule")
        api = NsxTEndpoint.CRUD_GATEWAY_FIREWALL_RULE[self.env].format(policy_name=policy, rule_id=rule_id)
        url = f"{self.base_url}{api}"
        body = self._generate_firewall_rule_payload(**kwargs, rule_id=rule_id, tier1=tier)
        res = requests.put(url, data=body, headers=self.headers, verify=False)
        return NsxtClient._handle_response(res)

    def list_dhcp_servers(self):
        """
        List DHCP servers from NSX-T
        :return: list of DHCP servers on NSX-T
        """
        current_app.logger.info("Listing DHCP Servers on NSX")
        url = f"{self.base_url}{NsxTEndpoint.LIST_DHCP_SERVERS}"
        res = requests.get(url, headers=self.headers, verify=False)
        return NsxtClient._handle_response(res)

    def create_dhcp_server(self):
        """
        Create DHCP server on NSX-T
        :return: create DHCP API response
        """
        current_app.logger.info("Creating DHCP Server")
        url = f"{self.base_url}{NsxTEndpoint.CRUD_DHCP_SERVERS.format(server_name=VCF.DHCP_SERVER_NAME)}"
        body = NsxtClient._generate_dhcp_server_payload()
        # updated_header = self.headers.update({"Content-Type": "application/json", "Accept": "application/json"})
        res = requests.put(url, data=body, headers=self.headers, verify=False)
        return NsxtClient._handle_response(res)

    def get_tier1_details(self, router_display_name):
        """
        obtain tier1 details from NSX-T for given tier1 router
        :param router_display_name: tier1 router name
        :return: tier1 string
        """
        url = f"{self.base_url}{NsxTEndpoint.LIST_TIER1}"
        res = requests.get(url, headers=self.headers, verify=False)
        response = NsxtClient._handle_response(res)
        for tr in response["results"]:
            if str(tr["display_name"]).lower() == router_display_name.lower():
                return tr["path"]
        raise Exception("Failed to get Tier1 details")

    def get_transport_zone(self, transport_zone_name):
        """
        Get transport zone ffron NSX-T overlay
        :param transport_zone_name: overlay name
        :return: transport zone name
        """
        url = f"{self.base_url}{NsxTEndpoint.LIST_TRANSPORT_ZONES}"
        res = requests.get(url, headers=self.headers, verify=False)
        response = NsxtClient._handle_response(res)
        for t_zone in response["results"]:
            if str(t_zone["transport_type"]) == "OVERLAY" and str(t_zone["display_name"]) == transport_zone_name:
                return t_zone["id"]
        raise Exception("Failed to get Transport zone details details")

    def get_network_ip(self, gateway_address):
        ipNet = self.seperate_netmask_and_ip(gateway_address)
        ss = ipNet[0].split(".")
        return ss[0] + "." + ss[1] + "." + ss[2] + ".0" + "/" + ipNet[1]

    def seperate_netmask_and_ip(self, cidr):
        return str(cidr).split("/")

    def get_domain_name(self, domain_name):
        url = f"{self.base_url}{NsxTEndpoint.LIST_DOMAINS}"
        response = requests.get(url, headers=self.headers, verify=False)
        response = NsxtClient._handle_response(response)["results"]
        domain = NsxtClient.find_vcf_object(response, domain_name)
        if domain is not None:
            return domain["display_name"]
        raise Exception("Failed to get domain name")

    def create_group_vcf(self, group_name, segment_name, is_ip, ipaddresses, segment_paths, groups):
        """
        Create group on NSX-T for VCF environment
        :param group_name: name of the group to be created
        :param segment_name: segment name
        :param is_ip: True is IP is available else, False
        :param ipaddresses: list of IP addresses to be included in group
        :param segment_paths: dict mapping segment names to the segment paths
        :param groups: ict mapping group names to the group membership expression spec.
        :return: path of group created
        """
        try:
            domain_name = self.get_domain_name("default")
            # check if provided segment exists and obtain the path
            if segment_name is not None:
                if segment_name not in segment_paths:
                    raise Exception(f"Failed to find the segment {segment_name}")
                segment_path = segment_paths[segment_name]
            else:
                segment_path = None
            url = (
                f"{self.base_url}"
                f"{NsxTEndpoint.CRUD_GROUP[self.env].format(domain_name=domain_name, group_name=group_name)}"
            )
            is_present = False
            lis_ip = []
            try:
                response = requests.get(url, headers=self.headers, verify=False)
                results = NsxtClient._handle_response(response)
                revision_id = results["_revision"]
                for expression in results["expression"]:
                    if is_ip:
                        for _ip in expression["ip_addresses"]:
                            lis_ip.append(_ip)
                            if str(_ip) == str(ipaddresses):
                                is_present = True
                                break
                    else:
                        for path in expression["paths"]:
                            lis_ip.append(path)
                            if str(segment_path) == str(path):
                                is_present = True
                                break
                    if is_present:
                        break
            except Exception:
                is_present = False
            if ipaddresses is not None:
                for ip_ in ipaddresses.split(", "):
                    lis_ip.append(ip_)
            else:
                lis_ip.append(segment_path)
            group_path = NsxtClient.find_vcf_object(groups, group_name)
            # Create the group if group does not exist
            if group_path is None or not is_present:
                current_app.logger.info("Creating group " + group_name)
                url = (
                    f"{self.base_url}"
                    f"{NsxTEndpoint.CRUD_GROUP[self.env].format(domain_name=domain_name, group_name=group_name)}"
                )
                # create group creation payload based on IP address provided
                if is_ip:
                    if not is_present and group_path is not None:
                        payload = {
                            "display_name": group_name,
                            "expression": [{"resource_type": "IPAddressExpression", "ip_addresses": lis_ip}],
                            "resource_type": "Group",
                            "_revision": int(revision_id),
                        }
                    else:
                        payload = {
                            "display_name": group_name,
                            "expression": [
                                {
                                    "resource_type": "IPAddressExpression",
                                    "ip_addresses": ipaddresses.split(","),
                                }
                            ],
                            "id": group_name,
                        }
                # If IP provided in of VC, then created different payload
                elif is_ip == "vc":
                    payload = {
                        "display_name": group_name,
                        "expression": [
                            {
                                "value": ipaddresses,
                                "member_type": "VirtualMachine",
                                "key": "OSName",
                                "operator": "EQUALS",
                                "resource_type": "Condition",
                            }
                        ],
                        "id": group_name,
                    }
                else:
                    if not is_present and group_path is not None:
                        payload = {
                            "display_name": group_name,
                            "expression": [{"resource_type": "PathExpression", "paths": lis_ip}],
                            "resource_type": "Group",
                            "_revision": int(revision_id),
                        }
                    else:
                        payload = {
                            "display_name": group_name,
                            "expression": [{"resource_type": "PathExpression", "paths": [segment_path]}],
                            "id": group_name,
                        }
                payload_modified = json.dumps(payload, indent=4)
                res = requests.put(url, data=payload_modified, headers=self.headers, verify=False)
                response = NsxtClient._handle_response(res)
                msg_text = "Created group " + group_name
                path = NsxtClient.get_object_path(response)
            else:
                path = group_path
                msg_text = group_name + " group is already created."
            current_app.logger.info(msg_text)
            return path
        except Exception as e:
            raise Exception(f"Failed to create segment {e}")

    def list_policies(self):
        """
        List existing policies from NSX-T
        :return: list of policies
        """
        current_app.logger.info("Listing policies on NSX-T")
        url = f"{self.base_url}{NsxTEndpoint.LIST_POLICIES}"
        res = requests.get(url, headers=self.headers, verify=False)
        return NsxtClient._handle_response(res)["results"]

    def create_policy(self, **kwargs):
        """
        create policy on NSX-T
        :param kwargs: policy_name and tier_path
        :return: create policy API reponse
        """
        current_app.logger.info("Creating NSX-T policy")
        url = f"{self.base_url}{NsxTEndpoint.CREATE_UPDATE_POLICY}"
        body = NsxtClient._generate_policy_payload(**kwargs)
        res = requests.patch(url, data=body, headers=self.headers, verify=False)
        try:
            res.raise_for_status()
        except HTTPError:
            raise Exception(f"Error while executing API: {res.text}")
