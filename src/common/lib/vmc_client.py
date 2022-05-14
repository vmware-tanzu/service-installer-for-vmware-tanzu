from flask import current_app

import requests
from common.constants.vmc_api_constants import VmcEndpoint
from requests.models import HTTPError, Response

from src.common.operation.constants import Env

# TODO: Replace with correct logger impl
#logger = logging.getLogger()


class VmcClient:
    def __init__(self, config):
        self.base_url = VmcEndpoint.BASE_URL
        VmcClient.validate_run_config(config)
        self.access_token = config['access_token']
        self.headers = {
            'Content-Type': 'application/json',
            'csp-auth-token': self.access_token
        }

    @staticmethod
    def validate_run_config(config):
        if config['DEPLOYMENT_PLATFORM'] != Env.VMC or not config['access_token']:
            raise ValueError("Failed to initialise VmcClient. Required values not found in run config.")

    @staticmethod
    def handle_response(response: Response):
        current_app.logger.debug(f"Response code: {response.status_code}\nResponse Body: {response.text}")
        try:
            response.raise_for_status()
        except HTTPError:
            raise Exception(f"Error while executing API: {response.text}")
        return response.json()

    def get_all_orgs(self):
        current_app.logger.info("Get all organizations")
        url = f"{self.base_url}{VmcEndpoint.GET_ALL_ORGS}"
        current_app.logger.debug(f"Request URL: {url}")
        current_app.logger.debug(f"Request Headers: {self.headers}")
        res = requests.get(url, headers=self.headers)
        return VmcClient.handle_response(res)

    def find_org_by_name(self, org_name):
        current_app.logger.info("Search for organization by name")
        org_list = self.get_all_orgs()
        org = next((x for x in org_list if x['display_name'] == org_name), None)
        if not org:
            raise ValueError(f"No org exists by name: {org_name}")
        return org

    def get_all_sddcs(self, org_id):
        current_app.logger.info("Get all SDDCs")
        url = f"{self.base_url}/orgs/{org_id}{VmcEndpoint.GET_ALL_SDDCS}"
        current_app.logger.debug(f"Request URL: {url}")
        current_app.logger.debug(f"Request Headers: {self.headers}")
        res = requests.get(url, headers=self.headers)
        return VmcClient.handle_response(res)

    def find_sddc_by_name(self, org_id, sddc_name):
        current_app.logger.info("Search for SDDC by name")
        sddc_list = self.get_all_sddcs(org_id)
        sddc = next((x for x in sddc_list if x['name'] == sddc_name), None)
        if not sddc:
            raise ValueError(f"No SDDC exists by name: {sddc_name}")
        return sddc

    @staticmethod
    def get_org_id(org):
        current_app.logger.info("Get org ID from org details")
        return org["id"]

    @staticmethod
    def get_sddc_id(sddc):
        current_app.logger.info("Get SDDC ID from sddc details")
        return sddc["id"]

    @staticmethod
    def get_nsx_reverse_proxy_url(sddc):
        current_app.logger.info("Get NSX reverse proxy URL from sddc details")
        return sddc["resource_config"]["nsx_reverse_proxy_url"]

    @staticmethod
    def get_vcenter_ip(sddc):
        current_app.logger.info("Get vCenter IP from sddc details")
        return sddc["resource_config"]["vc_management_ip"]

    @staticmethod
    def get_vcenter_cloud_user(sddc):
        current_app.logger.info("Get vCenter cloud username from sddc details")
        return sddc["resource_config"]["cloud_username"]

    @staticmethod
    def get_vcenter_cloud_password(sddc):
        current_app.logger.info("Get vCenter cloud user password from sddc details")
        return sddc["resource_config"]["cloud_password"]
