# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
import json
from http import HTTPStatus

import requests

__author__ = "Abhishek Inani"


class RequestApiUtil:
    def __init__(self):
        pass

    @staticmethod
    def exec_req(req_type: str, api_url: str, headers: dict = None, data=None, verify=False, timeout=None):
        """
        Method to execute Request API
        :
        """
        try:
            response = requests.request(
                method=req_type, url=api_url, headers=headers, data=data, verify=verify, timeout=timeout
            )
            return response
        except requests.exceptions.ConnectionError:
            return False

    @staticmethod
    def verify_resp(resp, key_verify: str = "STATUS_CODE", status_code: int = HTTPStatus.OK):
        """
        Method to verify response
        :param: key_verify: Key to obe verified in response
        :status_code: status code value to be verified
        """
        if isinstance(resp, requests.models.Response) and hasattr(resp, "status_code"):
            return resp.status_code == status_code
        # check has been include to handle arcas response as arcas return status code as part of the response body.
        elif isinstance(resp, requests.models.Response) and resp.json()[key_verify] == status_code:
            return True
        return False

    @staticmethod
    def create_json_object(message, response_type="SUCCESS", status_code=HTTPStatus.OK):
        """
        Method to create json response
        :param response_type: response type, either SUCCESS or ERROR
        :param status_code: status code
        :param message: message for the response
        :return: json dictionary
        """
        json_dictionary = {"responseType": str(response_type), "msg": str(message), "STATUS_CODE": status_code}
        return json.dumps(json_dictionary, indent=4)

    @staticmethod
    def send_error(message):
        """
        Method to send json response errro
        :param message: message for the response
        :return: json dictionary
        """
        return RequestApiUtil.create_json_object(
            message=message, response_type="ERROR", status_code=HTTPStatus.INTERNAL_SERVER_ERROR
        )

    @staticmethod
    def send_ok(message):
        """
        Method to send json response error
        :param message: message for the response
        :return: json dictionary
        """
        return RequestApiUtil.create_json_object(message=message, response_type="SUCCESS", status_code=HTTPStatus.OK)

    @staticmethod
    def fetch_cookies(response):
        """
        fetch cookies from request response
        """
        return requests.utils.dict_from_cookiejar(response.cookies)

    @staticmethod
    def fetch_elapsed_time(response):
        """
        fetch the elapsed time,
        elapsed time, provides the time delta between the Request was sent and the Response was received.
        :returns: rounded off time
        """
        return round(response.elapsed.total_seconds())
