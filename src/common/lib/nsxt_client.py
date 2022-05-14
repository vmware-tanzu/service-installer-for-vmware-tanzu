import json
from flask import current_app

import requests
from requests.models import HTTPError, Response

from src.common.constants.nsxt_api_constants import NsxTEndpoint, NsxTPayload
from src.common.operation.constants import Env

# TODO: Replace with get_logger impl
#logger = logging.getLogger()


class NsxtClient:
    def __init__(self, config):
        if config['DEPLOYMENT_PLATFORM'] == Env.VMC:
            NsxtClient.validate_vmc_run_config(config)
            self.base_url = NsxTEndpoint.VMC_BASE_URL.format(url=config['NSX_REVERSE_PROXY_URL'].rstrip('/'),
                                                             org_id=config['ORG_ID'],
                                                             sddc_id=config['SDDC_ID'])
            self.access_token = config['access_token']
            self.headers = {
                "Content-Type": "application/json",
                "csp-auth-token": self.access_token
            }
        else:
            # TODO: Implement constructor for VCF or vSphere. They will have different base url and headers
            raise ValueError("Failed to initialise NsxtClient. Not implemented for VCF of vSphere")

    @staticmethod
    def validate_vmc_run_config(config):
        if not all([config['SDDC_ID'], config['NSX_REVERSE_PROXY_URL'], config['ORG_ID'], config['access_token']]):
            raise ValueError("Failed to initialise NsxtClient. Required values not found in run config.")

    @staticmethod
    def handle_response(response: Response):
        current_app.logger.debug(f"Response code: {response.status_code}\nResponse Body: {response.text}")
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
    def generate_segment_payload(**kwargs):
        payload = NsxTPayload.CREATE_UPDATE_SEGMENT.format(name=kwargs["segment_id"],
                                                           gateway=kwargs["gateway_cidr"],
                                                           dhcp_start=kwargs["dhcp_start"],
                                                           dhcp_end=kwargs["dhcp_end"],
                                                           dns_servers=json.dumps(kwargs["dns_servers"]))
        return payload

    @staticmethod
    def generate_group_payload(**kwargs):
        payload = NsxTPayload.CREATE_UPDATE_GROUP.format(name=kwargs["group_id"], expression=kwargs["expression"])
        return payload

    @staticmethod
    def generate_service_payload(**kwargs):
        payload = NsxTPayload.CREATE_UPDATE_SERVICE.format(service_entry_name=json.dumps(kwargs["service_entry_name"]))
        return payload

    @staticmethod
    def generate_firewall_rule_payload(**kwargs):
        payload = NsxTPayload.CREATE_UPDATE_FIREWALL_RULE.format(src_groups=json.dumps(kwargs["source"]),
                                                                 dest_groups=json.dumps(kwargs["destination"]),
                                                                 scope=json.dumps(kwargs["scope"]),
                                                                 services=json.dumps(kwargs["services"]))
        return payload

    @staticmethod
    def get_object_path(nsxt_object):
        return nsxt_object["path"]

    @staticmethod
    def get_segment_path(segment_list, segment_name):
        return next((segment['path'] for segment in segment_list if segment["display_name"] == segment_name), None)

    def list_segments(self, gateway_id):
        current_app.logger.info(f"List all NSX-T segments on {gateway_id} gateway")
        url = f"{self.base_url}{NsxTEndpoint.LIST_SEGMENTS.format(gw_id=gateway_id)}"
        current_app.logger.debug(f"Request URL: {url}")
        current_app.logger.debug(f"Request Headers: {self.headers}")
        res = requests.get(url, headers=self.headers)
        return NsxtClient.handle_response(res)["results"]

    def create_segment(self, gateway_id, segment_id, **kwargs):
        current_app.logger.info("Creating NSX-T segment")
        url = f"{self.base_url}{NsxTEndpoint.CRUD_SEGMENT.format(gw_id=gateway_id, segment_id=segment_id)}"
        body = NsxtClient.generate_segment_payload(**kwargs, segment_id=segment_id)
        current_app.logger.debug(f"Request URL: {url}")
        current_app.logger.debug(f"Request Headers: {self.headers}")
        current_app.logger.debug(f"Request Body: {body}")
        res = requests.put(url, data=body, headers=self.headers)
        return NsxtClient.handle_response(res)

    def list_groups(self, gateway_id):
        current_app.logger.info("Listing NSX-T inventory groups")
        url = f"{self.base_url}{NsxTEndpoint.LIST_GROUPS.format(gw_id=gateway_id)}"
        current_app.logger.debug(f"Request URL: {url}")
        current_app.logger.debug(f"Request Headers: {self.headers}")
        res = requests.get(url, headers=self.headers)
        return NsxtClient.handle_response(res)["results"]

    def create_group(self, gateway_id, group_id, **kwargs):
        current_app.logger.info("Creating NSX-T group")
        url = f"{self.base_url}{NsxTEndpoint.CRUD_GROUP.format(gw_id=gateway_id, group_id=group_id)}"
        body = NsxtClient.generate_group_payload(**kwargs, group_id=group_id)
        current_app.logger.debug(f"Request URL: {url}")
        current_app.logger.debug(f"Request Headers: {self.headers}")
        current_app.logger.debug(f"Request Body: {body}")
        res = requests.put(url, data=body, headers=self.headers)
        return NsxtClient.handle_response(res)

    def list_services(self):
        current_app.logger.info("Listing NSX-T inventory services")
        url = f"{self.base_url}{NsxTEndpoint.LIST_SERVICES}"
        current_app.logger.debug(f"Request URL: {url}")
        current_app.logger.debug(f"Request Headers: {self.headers}")
        res = requests.get(url, headers=self.headers)
        return NsxtClient.handle_response(res)["results"]

    def create_service(self, service_id, **kwargs):
        current_app.logger.info("Creating NSX-T service")
        url = f"{self.base_url}{NsxTEndpoint.CRUD_SERVICE.format(service_id=service_id)}"
        body = NsxtClient.generate_service_payload(**kwargs)
        current_app.logger.debug(f"Request URL: {url}")
        current_app.logger.debug(f"Request Headers: {self.headers}")
        current_app.logger.debug(f"Request Body: {body}")
        res = requests.put(url, data=body, headers=self.headers)
        return NsxtClient.handle_response(res)

    def list_gateway_firewall_rules(self, gw_id, gw_policy_id="default"):
        current_app.logger.info(f"Listing gateway firewall rules for {gw_id} gateway.")
        url = f"{self.base_url}{NsxTEndpoint.LIST_GATEWAY_FIREWALL_RULES.format(gw_id=gw_id, gw_policy_id=gw_policy_id)}"
        current_app.logger.debug(f"Request URL: {url}")
        current_app.logger.debug(f"Request Headers: {self.headers}")
        res = requests.get(url, headers=self.headers)
        return NsxtClient.handle_response(res)["results"]

    def create_gateway_firewall_rule(self, gw_id, rule_id, gw_policy_id="default", **kwargs):
        current_app.logger.info("Creating gateway firewall rule")
        api = NsxTEndpoint.CRUD_GATEWAY_FIREWALL_RULE.format(gw_id=gw_id, gw_policy_id=gw_policy_id, rule_id=rule_id)
        url = f"{self.base_url}{api}"
        body = NsxtClient.generate_firewall_rule_payload(**kwargs, rule_id=rule_id)
        current_app.logger.debug(f"Request URL: {url}")
        current_app.logger.debug(f"Request Headers: {self.headers}")
        current_app.logger.debug(f"Request Body: {body}")
        res = requests.put(url, data=body, headers=self.headers)
        return NsxtClient.handle_response(res)
