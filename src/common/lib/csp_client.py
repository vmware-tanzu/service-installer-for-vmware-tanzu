from flask import current_app

import requests
from requests.models import HTTPError, Response

from src.common.operation.constants import Env

# TODO: Replace with correct logger impl
#logger = logging.get_logger()


class CspClient:
    def __init__(self, config, refresh_token):
        CspClient.validate_run_config(config, refresh_token)
        self.refresh_token = refresh_token

    @staticmethod
    def validate_run_config(config, refresh_token):
        if config['DEPLOYMENT_PLATFORM'] != Env.VMC or not refresh_token:
            raise ValueError("Failed to initialise CspClient. Required values not found in run config.")

    @staticmethod
    def handle_response(response: Response):
        current_app.logger.debug(f"Response code: {response.status_code}\nResponse Body: {response.text}")
        try:
            response.raise_for_status()
        except HTTPError:
            raise Exception(f"Error while executing API: {response.text}")
        return response.json()

    def get_access_token(self):
        current_app.logger.info("Generate CSP access token using refresh token")
        url = "https://console.cloud.vmware.com/csp/gateway/am/api/auth/api-tokens/authorize"
        query_params = {
            "refresh_token": self.refresh_token
        }
        res = requests.post(url, params=query_params)
        return CspClient.handle_response(res)["access_token"]
