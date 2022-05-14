#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import json

import requests
from pathlib import Path

from constants.api_payloads import NsxTPayload
from constants.constants import VmcNsxtGateways
from model.run_config import RunConfig
from util.logger_helper import LoggerHelper, log
from constants.api_endpoints import NSXT

logger = LoggerHelper.get_logger(Path(__file__).stem)


class NsxtClient:
    def __init__(self, config: RunConfig):
        NsxtClient.validate_run_config(config)
        self.base_url = NSXT.VMC_BASE_URL.format(url=config.vmc.nsx_reverse_proxy_url.rstrip('/'),
                                                 org_id=config.vmc.org_id,
                                                 sddc_id=config.vmc.sddc_id)
        self.access_token = config.vmc.csp_access_token
        self.headers = {
            "Content-Type": "application/json",
            "csp-auth-token": self.access_token
        }

    @staticmethod
    def validate_run_config(config):
        if not all([config.vmc, config.vmc.nsx_reverse_proxy_url, config.vmc.org_id, config.vmc.sddc_id,
                    config.vmc.csp_access_token]):
            raise ValueError("Failed to initialise NsxtClient. Required values not found in run config.")

    @staticmethod
    def find_object(nsxt_objects, object_id):
        logger.info(f"Check if object exists with ID: {object_id}")
        return next((nsxt_object for nsxt_object in nsxt_objects if nsxt_object["id"] == object_id), None)

    @staticmethod
    def _generate_segment_payload(**kwargs):
        payload = NsxTPayload.CREATE_UPDATE_SEGMENT.format(name=kwargs["segment_id"],
                                                           gateway=kwargs["segment"].gatewayCidr,
                                                           dhcp_start=kwargs["segment"].dhcpStart,
                                                           dhcp_end=kwargs["segment"].dhcpEnd,
                                                           dns_servers=json.dumps(kwargs["dns_servers"]))
        return payload

    @staticmethod
    def _generate_group_payload(**kwargs):
        payload = NsxTPayload.CREATE_UPDATE_GROUP.format(name=kwargs["group_id"], expression=kwargs["expression"])
        return payload

    @staticmethod
    def _generate_service_payload(**kwargs):
        payload = NsxTPayload.CREATE_UPDATE_SERVICE.format(service_entry_name=json.dumps(kwargs["service_entry_name"]))
        return payload

    @staticmethod
    def _generate_firewall_rule_payload(**kwargs):
        payload = NsxTPayload.CREATE_UPDATE_FIREWALL_RULE.format(src_groups=json.dumps(kwargs["source"]),
                                                                 dest_groups=json.dumps(kwargs["destination"]),
                                                                 scope=json.dumps(kwargs["scope"]),
                                                                 services=json.dumps(kwargs["services"]))
        return payload

    @staticmethod
    @log("Get path from NSX-T object details")
    def get_object_path(nsxt_object):
        return nsxt_object["path"]

    @log("Listing NSX-T segments")
    def list_segments(self, gateway_id):
        logger.info(f"List all NSX-T segments on {gateway_id} gateway")
        url = f"{self.base_url}{NSXT.LIST_SEGMENTS.format(gw_id=gateway_id)}"
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Request Headers: {self.headers}")
        r = requests.get(url, headers=self.headers)
        logger.debug(f"Response code: {r.status_code}\nResponse Body: {r.text}")
        r.raise_for_status()
        return r.json()["results"]

    @log("Creating NSX-T segment")
    def create_segment(self, gateway_id, segment_id, **kwargs):
        url = f"{self.base_url}{NSXT.CRUD_SEGMENT.format(gw_id=gateway_id, segment_id=segment_id)}"
        body = NsxtClient._generate_segment_payload(**kwargs, segment_id=segment_id)
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Request Headers: {self.headers}")
        logger.debug(f"Request Body: {body}")
        r = requests.put(url, data=body, headers=self.headers)
        logger.debug(f"Response code: {r.status_code}\nResponse Body: {r.text}")
        r.raise_for_status()
        return r.json()

    @log("Listing NSX-T inventory groups")
    def list_groups(self, gateway_id: VmcNsxtGateways):
        url = f"{self.base_url}{NSXT.LIST_GROUPS.format(gw_id=gateway_id)}"
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Request Headers: {self.headers}")
        r = requests.get(url, headers=self.headers)
        logger.debug(f"Response code: {r.status_code}\nResponse Body: {r.text}")
        r.raise_for_status()
        return r.json()["results"]

    @log("Creating NSX-T group")
    def create_group(self, gateway_id, group_id, **kwargs):
        url = f"{self.base_url}{NSXT.CRUD_GROUP.format(gw_id=gateway_id, group_id=group_id)}"
        body = NsxtClient._generate_group_payload(**kwargs, group_id=group_id)
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Request Headers: {self.headers}")
        logger.debug(f"Request Body: {body}")
        r = requests.put(url, data=body, headers=self.headers)
        logger.debug(f"Response code: {r.status_code}\nResponse Body: {r.text}")
        r.raise_for_status()
        return r.json()

    @log("Listing NSX-T inventory services")
    def list_services(self):
        url = f"{self.base_url}{NSXT.LIST_SERVICES}"
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Request Headers: {self.headers}")
        r = requests.get(url, headers=self.headers)
        logger.debug(f"Response code: {r.status_code}\nResponse Body: {r.text}")
        r.raise_for_status()
        return r.json()["results"]

    @log("Creating NSX-T service")
    def create_service(self, service_id, **kwargs):
        url = f"{self.base_url}{NSXT.CRUD_SERVICE.format(service_id=service_id)}"
        body = NsxtClient._generate_service_payload(**kwargs)
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Request Headers: {self.headers}")
        logger.debug(f"Request Body: {body}")
        r = requests.put(url, data=body, headers=self.headers)
        logger.debug(f"Response code: {r.status_code}\nResponse Body: {r.text}")
        r.raise_for_status()
        return r.json()

    def list_gateway_firewall_rules(self, gw_id, gw_policy_id="default"):
        logger.info(f"Listing gateway firewall rules for {gw_id} gateway.")
        url = f"{self.base_url}{NSXT.LIST_GATEWAY_FIREWALL_RULES.format(gw_id=gw_id, gw_policy_id=gw_policy_id)}"
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Request Headers: {self.headers}")
        r = requests.get(url, headers=self.headers)
        logger.debug(f"Response code: {r.status_code}\nResponse Body: {r.text}")
        r.raise_for_status()
        return r.json()["results"]

    @log("Creating gateway firewall rule")
    def create_gateway_firewall_rule(self, gw_id, rule_id, gw_policy_id="default", **kwargs):
        api = NSXT.CRUD_GATEWAY_FIREWALL_RULE.format(gw_id=gw_id, gw_policy_id=gw_policy_id, rule_id=rule_id)
        url = f"{self.base_url}{api}"
        body = NsxtClient._generate_firewall_rule_payload(**kwargs, rule_id=rule_id)
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Request Headers: {self.headers}")
        logger.debug(f"Request Body: {body}")
        r = requests.put(url, data=body, headers=self.headers)
        logger.debug(f"Response code: {r.status_code}\nResponse Body: {r.text}")
        r.raise_for_status()
        return r.json()
