# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import base64
import json
import time
from pathlib import Path

import requests

from common.operation.constants import ApiUrl
from common.util.common_utils import CommonUtils

__author__ = "Abhishek Inani"


class HarborConstants:
    HARBOR_USER_NAME = "admin"
    HARBOR_PROJECT_NAME = "tanzu"
    FROM_TAR_YAML_FILE = "/opt/vmware/arcas/tools/publish-images-fromtar.yaml"
    IS_HARBOR_FILE_PATH = "/opt/vmware/arcas/tools/isharbor.txt"
    HARBOR_FQDN_PATH = "/opt/vmware/arcas/tools/harbor_fqdn.txt"
    TANZU_BINARY_EXTRACT_FOLDER = "/opt/vmware/arcas/tools/tanzu/"
    SECRECT_FILE_PATH = "/etc/.secrets/root_password"
    CER_GEN_PATH = "/opt/vmware/arcas/tools/gen.sh"


class HarborUtils:
    def __init__(self):
        self.harbor_repo_username = HarborConstants.HARBOR_USER_NAME
        self.project_name = HarborConstants.HARBOR_PROJECT_NAME
        is_harbor_file = HarborConstants.IS_HARBOR_FILE_PATH
        bool_harbor = is_harbor_file.strip("\n").strip("\r").strip()
        self.is_harbor_selected = bool(bool_harbor)
        harbor_fqdn = HarborConstants.HARBOR_FQDN_PATH
        data = Path(harbor_fqdn).read_text().strip()
        self.harbor_fqdn = data
        self.harbor_address = data + ":9443"
        data.strip("\n").strip("\r").strip()
        self.tanzu_extract_folder = HarborConstants.TANZU_BINARY_EXTRACT_FOLDER
        self.url = "https://" + self.harbor_address + "/api/v2.0/projects"
        file = HarborConstants.SECRECT_FILE_PATH
        self.harbor_repo_password = Path(file).read_text().strip("\n")
        ecod_bytes = (self.harbor_repo_username + ":" + self.harbor_repo_password).encode("ascii")
        ecod_bytes = base64.b64encode(ecod_bytes)
        ecod_string = ecod_bytes.decode("ascii")
        self.harbor_header = {
            "Authorization": ("Basic " + ecod_string),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self.common_util_obj = CommonUtils()

    def create_harbor_project(self):
        response = requests.request("GET", self.url, headers=self.harbor_header, verify=False)
        if response.status_code != 200:
            return None, response.text
        for project in response.json():
            if project["name"] == self.project_name:
                return "Success", self.project_name + " is already created"
        body = {
            "project_name": self.project_name,
            "metadata": {"public": "true"},
            "storage_limit": -1,
            "registry_id": None,
        }
        json_object = json.dumps(body, indent=4)
        response = requests.request("POST", self.url, headers=self.harbor_header, data=json_object, verify=False)
        if response.status_code != 201:
            return None, "Failed to create harbor project " + self.project_name + " " + response.text
        return "Success", self.project_name + " created"

    def check_repository_count(self):
        response = requests.request("GET", self.url, headers=self.harbor_header, verify=False)
        if response.status_code != 200:
            return None, response.text
        for project in response.json():
            if project["name"] == self.project_name:
                if project["repo_count"] == 155:
                    return "Success", "All tanzu images are present"
                elif project["repo_count"] == 0:
                    return None, "No repository present, pushing"
                else:
                    return (
                        "Partial",
                        "Repo count is less then expected , clear all repostory under  "
                        + self.project_name
                        + " and retrigger command --load_tanzu_image_to_harbor",
                    )
        return "NOT_FOUND", self.project_name + " project not found"

    def get_repo_count(self):
        if self.is_harbor_selected:
            response = requests.request("GET", self.url, headers=self.harbor_header, verify=False)
            if response.status_code != 200:
                return 0, response.text
            for project in response.json():
                if project["name"] == self.project_name:
                    return project["repo_count"], "SUCCESS"
        return 0, self.project_name + " project not found"

    def load_tanzu_image_to_harbor(self, repo_name: str, tkg_binaries: str) -> dict:
        """
        Method to load tanzu images to harbor

        :param: repo_name: Name of repo to be used to load Tanzu images
        :param: tkg_binaries: Path of TKG binaries from where binaries to be uploaded
        :return: status dict
                Response Status code of operation
        """
        print("Load_Tanzu_Image: Load Tanzu Images to Harbor")
        load_status_dict = {"status_code": 500}
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        try:
            url = ApiUrl.HARBOR_URL
            response = requests.request(
                "POST", url, headers=headers, json={"repo_name": repo_name, "tkg_binaries": tkg_binaries}, verify=False
            )
            if response.json()["STATUS_CODE"] != 200:
                print("Loading Tanzu Images to Harbor failed " + str(response.json()))
            else:
                load_status_dict["status_code"] = 200
                print("Load_Tanzu_Image: Loaded Tanzu Images to Harbor Successfully")
            return load_status_dict
        except requests.exceptions.RequestException as e:
            print("Loading Tanzu Images to Harbor failed " + str(e))
            return load_status_dict

    def get_harbor_preloading_status(self, repo_name: str) -> dict:
        """
        Method to get harbor preload status

        :param: repo_name: Name of repo to be used to load Tanzu images
        :return: status dict
                Response Status code of operation
        """
        load_status_dict = {"status_code": 500}
        try:
            file_size = 100  # fake file size
            uploaded_size = 0
            url = f"{ApiUrl.HARBOR_PRELOAD_STATUS_URL}?repo_name={repo_name}"
            while uploaded_size < file_size:
                response = requests.request("GET", url, verify=False)
                if response.json()["STATUS_CODE"] != 200:
                    print("Failed to get status of harbor preloading " + str(response.json()))
                    return load_status_dict
                uploaded_size = int(response.json()["percentage"])
                self.common_util_obj.update_progress_bar(uploaded_size, file_size)
                time.sleep(10)
            load_status_dict["status_code"] = 200
            return load_status_dict
        except requests.exceptions.RequestException as e:
            print("Failed to get status of harbor preloading " + str(e))
            return load_status_dict
