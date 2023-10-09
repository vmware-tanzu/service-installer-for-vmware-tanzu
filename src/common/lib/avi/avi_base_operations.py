# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import json
from http import HTTPStatus

from common.constants.alb_api_constants import AlbEndpoint
from common.lib.avi.avi_constants import AVIConfig
from common.util.request_api_util import RequestApiUtil


class AVIBaseOperations:
    def __init__(self, avi_host, avi_password):
        self.avi_host = avi_host
        self.pre_login_headers = {"Content-Type": "application/json"}
        self.post_login_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": "cookies_to_update",
            "referer": "endpoint_url_to_update",
            "x-avi-version": "avi_version_to_update",
            "x-csrftoken": "token_to_update",
        }
        self.avi_default_password = AVIConfig.DEFAULT_PASSWORD
        self.avi_default_username = AVIConfig.DEFAULT_USERNAME
        self.avi_password = avi_password
        self.avi_version = None
        self.second_csrf = None
        self.first_csrf = None

    def _operation_headers(self, csrf):
        """
        method to setup default headers for the AVI endpoints request
        """
        headers_copy = self.post_login_headers
        headers_copy["Cookie"] = csrf[1]
        headers_copy["referer"] = AlbEndpoint.LOGIN.format(ip=self.avi_host)
        headers_copy["x-avi-version"] = self.avi_version
        headers_copy["x-csrftoken"] = csrf[0]
        return headers_copy

    def fetch_csrf(self, password):
        """
        fetch csrf with specified password, helper method to obtain first and second csrf
        """
        url = AlbEndpoint.LOGIN.format(ip=self.avi_host)
        modified_payload = json.dumps({"username": self.avi_default_username, "password": password}, indent=4)
        response_csrf = RequestApiUtil.exec_req(
            "POST", url, headers=self.pre_login_headers, data=modified_payload, verify=False
        )
        if not RequestApiUtil.verify_resp(resp=response_csrf, status_code=HTTPStatus.OK):
            if "Invalid credentials" in str(response_csrf.text):
                return "SUCCESS", "Already set"
            else:
                return None, "Failed"
        cookies_dict = RequestApiUtil.fetch_cookies(response=response_csrf)
        cookies_string = ""
        for key, value in cookies_dict.items():
            cookies_string += key + "=" + value + "; "
        return cookies_dict["csrftoken"], cookies_string

    def obtain_first_csrf(self):
        """
        fetch first csrf using AVI default password
        """
        csrf = self.fetch_csrf(password=self.avi_default_password)
        # save token to object when its not None
        self.first_csrf = csrf
        return csrf

    def obtain_second_csrf(self):
        """
        fetch second csrf using AVI password specified in user json
        """
        csrf = self.fetch_csrf(password=self.avi_password)
        # save token to object when it's not None
        self.second_csrf = csrf
        return csrf

    def obtain_avi_version(self):
        """
        fetch avi version from deployed AVI using AVI endpoints
        """
        url = AlbEndpoint.LOGIN.format(ip=self.avi_host)
        modified_payload = json.dumps({"username": "admin", "password": self.avi_password}, indent=4)
        response_avi = RequestApiUtil.exec_req(
            "POST", url, headers=self.pre_login_headers, data=modified_payload, verify=False
        )
        # verify version with default password
        if not RequestApiUtil.verify_resp(resp=response_avi, status_code=HTTPStatus.OK):
            modified_payload = json.dumps(
                {"username": self.avi_default_username, "password": self.avi_default_password}, indent=4
            )
            response_avi = RequestApiUtil.exec_req(
                "POST", url, headers=self.pre_login_headers, data=modified_payload, verify=False
            )
            if not RequestApiUtil.verify_resp(resp=response_avi, status_code=HTTPStatus.OK):
                return None, response_avi.text
        a_version = response_avi.json()["version"]["Version"]
        self.avi_version = a_version
        return a_version, HTTPStatus.OK
