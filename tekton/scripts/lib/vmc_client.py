#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

from pathlib import Path

import requests

from constants.api_endpoints import VMC
from model.run_config import RunConfig
from util.logger_helper import LoggerHelper, log

logger = LoggerHelper.get_logger(Path(__file__).stem)


class VmcClient:
    def __init__(self, config: RunConfig):
        self.base_url = VMC.BASE_URL
        VmcClient.validate_run_config(config)
        self.access_token = config.vmc.csp_access_token

    @staticmethod
    def validate_run_config(config):
        if not all([config.vmc, config.vmc.csp_access_token]):
            raise ValueError("Failed to initialise VmcClient. Required values not found in run config.")

    @log("Get all organizations")
    def get_all_orgs(self):
        url = f"{self.base_url}{VMC.GET_ALL_ORGS}"
        headers = {
            'Content-Type': 'application/json',
            'csp-auth-token': self.access_token
        }
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Request Headers: {headers}")
        r = requests.get(url, headers=headers)
        logger.debug(f"Response code: {r.status_code}\nResponse Body: {r.text}")
        r.raise_for_status()
        return r.json()

    @log("Search for organization by name")
    def find_org_by_name(self, org_name):
        org_list = self.get_all_orgs()
        org = next((x for x in org_list if x['display_name'] == org_name), None)
        if not org:
            raise ValueError(f"No org exists by name: {org_name}")
        return org

    @log("Get org ID from org details")
    def get_org_id(self, org):
        return org["id"]

    @log("Get all SDDCs")
    def get_all_sddcs(self, org_id):
        url = f"{self.base_url}/orgs/{org_id}{VMC.GET_ALL_SDDCS}"
        headers = {
            'Content-Type': 'application/json',
            'csp-auth-token': self.access_token
        }
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Request Headers: {headers}")
        r = requests.get(url, headers=headers)
        logger.debug(f"Response code: {r.status_code}\nResponse Body: {r.text}")
        r.raise_for_status()
        return r.json()

    @log("Search for SDDC by name")
    def find_sddc_by_name(self, org_id, sddc_name):
        sddc_list = self.get_all_sddcs(org_id)
        sddc = next((x for x in sddc_list if x['name'] == sddc_name), None)
        if not sddc:
            raise ValueError(f"No SDDC exists by name: {sddc_name}")
        return sddc

    @staticmethod
    def get_sddc_id(sddc):
        logger.info("Get SDDC ID from sddc details")
        return sddc["id"]

    @staticmethod
    def get_nsx_reverse_proxy_url(sddc):
        logger.info("Get NSX reverse proxy URL from sddc details")
        return sddc["resource_config"]["nsx_reverse_proxy_url"]

    @staticmethod
    def get_vcenter_ip(sddc):
        logger.info("Get vCenter IP from sddc details")
        return sddc["resource_config"]["vc_management_ip"]

    @staticmethod
    def get_vcenter_cloud_user(sddc):
        logger.info("Get vCenter cloud username from sddc details")
        return sddc["resource_config"]["cloud_username"]

    @staticmethod
    def get_vcenter_cloud_password(sddc):
        logger.info("Get vCenter cloud user password from sddc details")
        return sddc["resource_config"]["cloud_password"]
