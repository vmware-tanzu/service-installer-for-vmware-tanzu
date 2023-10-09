# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import json
import time
from http import HTTPStatus

from flask import current_app

from common.constants.alb_api_constants import AlbEndpoint, AlbPayload
from common.lib.avi.avi_base_operations import AVIBaseOperations
from common.lib.avi.avi_constants import AVIDataFiles
from common.replace_value import replaceValueSysConfig
from common.util.file_helper import FileHelper
from common.util.request_api_util import RequestApiUtil


class AVIAdminOps(AVIBaseOperations):
    """
    before doing any other operation password needs to be modified and second csrf needs to be obtained.
    class for handling all Admin operations of AVI
    """

    def __init__(self, avi_host, avi_password):
        """
        #TODO needs to be improved with spec
        :param avi_host: IP or host name of AVI
        :param avi_password: AVI password
        """
        super().__init__(avi_host, avi_password)

    def check_controller_is_up(self, only_check=True):
        """
        method to check whether avi controller is up and running or not. waits for 10 minutes
        :param only_check: code only verify controller is up and running
        :returns: UP if its running
        """
        url = AlbEndpoint.BASE_URL.format(ip=self.avi_host)
        count = 0
        payload = {}
        response_check = False
        response_login = RequestApiUtil.exec_req("GET", url, headers=self.pre_login_headers, data=payload, verify=False)
        if only_check:
            only_check_response = (
                "UP" if RequestApiUtil.verify_resp(response_login, status_code=HTTPStatus.OK) else None
            )
            return only_check_response
        # verify response for AVI controller 10 minutes
        final_elapsed_time = 0
        while not response_check and count < 150:
            count = count + 1
            elapsed_time = 0
            try:
                response_login = RequestApiUtil.exec_req(
                    "GET", url, headers=self.pre_login_headers, data=payload, verify=False
                )
                elapsed_time = RequestApiUtil.fetch_elapsed_time(response_login)
                final_elapsed_time += elapsed_time
                response_check = RequestApiUtil.verify_resp(response_login, status_code=HTTPStatus.OK)
            except Exception:
                pass
            current_app.logger.info("Waited for  " + str(count * 10 + elapsed_time) + "s, retrying.")
            time.sleep(10)
        if response_check:
            current_app.logger.info("Controller is up and running in   " + str(count * 10 + final_elapsed_time) + "s.")
            return "UP"
        else:
            current_app.logger.error(
                "Controller is not reachable even after " + str(count * 10 + final_elapsed_time) + "s wait"
            )
            return None

    def set_avi_admin_password(self):
        """
        set AVI admin password to the new password specified in user json using first csrf token
        """
        modified_payload = json.dumps(
            {
                "old_password": self.avi_default_password,
                "password": self.avi_password,
                "username": self.avi_default_username,
            },
            indent=4,
        )
        header = self._operation_headers(self.first_csrf)
        url = AlbEndpoint.USER_ACCOUNT.format(ip=self.avi_host)
        response_csrf = RequestApiUtil.exec_req("PUT", url, headers=header, data=modified_payload, verify=False)
        if not RequestApiUtil.verify_resp(response_csrf, status_code=HTTPStatus.OK):
            return None
        else:
            return "SUCCESS"

    def get_system_configuration(self):
        """
        fetch default system configuration from AVI and save them into systemConfig1.json
        """

        url = AlbEndpoint.CRUD_SYSTEM_CONFIG.format(ip=self.avi_host)
        response_csrf = RequestApiUtil.exec_req(
            "GET", url, headers=self._operation_headers(csrf=self.second_csrf), verify=False
        )
        if not RequestApiUtil.verify_resp(response_csrf, status_code=HTTPStatus.OK):
            current_app.logger.error(f"Error {response_csrf.content} in getting AVI configuration")
            return None
        FileHelper.delete_file(AVIDataFiles.SYS_CONFIG_1)
        FileHelper.dump_json(file=AVIDataFiles.SYS_CONFIG_1, json_dict=response_csrf.json())
        return "SUCCESS"

    @staticmethod
    def update_license_config(type_of_avi_license="enterprise"):
        """
        this method is currently being called only for vsphere TKGm TKGs to specify AVI license in systemconfig
        :param type_of_avi_license: enterprise/essentials
        """
        current_app.logger.info(f"setting up avi license as {type_of_avi_license}")
        if type_of_avi_license.lower() == "essentials":
            replaceValueSysConfig(AVIDataFiles.SYS_CONFIG_1, "default_license_tier", "name", "ESSENTIALS")
        else:
            replaceValueSysConfig(AVIDataFiles.SYS_CONFIG_1, "default_license_tier", "name", "ENTERPRISE")

    @staticmethod
    def update_system_config(ntp_server_ip, dns_server_ip, search_domains):
        """
        updates ntp/dns and search domains in systemconfig json
        """
        replaceValueSysConfig(AVIDataFiles.SYS_CONFIG_1, "email_configuration", "smtp_type", "SMTP_NONE")
        replaceValueSysConfig(AVIDataFiles.SYS_CONFIG_1, "dns_configuration", "false", dns_server_ip)
        replaceValueSysConfig(AVIDataFiles.SYS_CONFIG_1, "ntp_configuration", "ntp", ntp_server_ip)
        replaceValueSysConfig(AVIDataFiles.SYS_CONFIG_1, "dns_configuration", "search_domain", search_domains)

    @staticmethod
    def update_portal_config():
        """
        this method is currently being called only for vsphere TKGs to set config in systemconfig1
        """
        replaceValueSysConfig(AVIDataFiles.SYS_CONFIG_1, "portal_configuration", "allow_basic_authentication", "true")

    def set_dns_ntp_smtp_settings(self):
        """
        set dns and ntp settings for AVI
        """
        url = AlbEndpoint.CRUD_SYSTEM_CONFIG.format(ip=self.avi_host)
        json_object = FileHelper.load_json(spec_path=AVIDataFiles.SYS_CONFIG_1)
        json_object_m = json.dumps(json_object, indent=4)
        response_csrf = RequestApiUtil.exec_req(
            "PUT", url, headers=self._operation_headers(csrf=self.second_csrf), data=json_object_m, verify=False
        )
        if not RequestApiUtil.verify_resp(response_csrf, status_code=HTTPStatus.OK):
            return None
        else:
            return "SUCCESS"

    def disable_welcome_screen(self, tenant_vrf=True):
        """
        disable welcome screen for AVI deployment
        tenant_vrf False for VMC, True for non-VMC
        """
        url = AlbEndpoint.CRUD_SYSTEM_CONFIG.format(ip=self.avi_host)
        body = AlbPayload.WELCOME_SCREEN_UPDATE.format(tenant_vrf=json.dumps(tenant_vrf))
        response_csrf = RequestApiUtil.exec_req(
            "PATCH", url, headers=self._operation_headers(csrf=self.second_csrf), data=body, verify=False
        )
        if not RequestApiUtil.verify_resp(response_csrf, status_code=HTTPStatus.OK):
            return None
        else:
            return "SUCCESS"

    def get_backup_configuration(self):
        """
        get AVI backup configuration data
        """
        url = AlbEndpoint.BACKUP_CONFIG.format(ip=self.avi_host)
        response = RequestApiUtil.exec_req(
            "GET", url, headers=self._operation_headers(csrf=self.second_csrf), verify=False
        )
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        else:
            return response.json()["results"][0]["url"], HTTPStatus.OK

    def set_backup_phrase(self, url, backup_pass_phrase):
        """
        method to setup backup pass phrase for avi
        :param url: url backup from avi configuration
        :param backup_pass_phrase: backup_pass_phrase for avi configuration should be english
        """
        body = {"add": {"backup_passphrase": backup_pass_phrase}}
        json_object = json.dumps(body, indent=4)
        response = RequestApiUtil.exec_req(
            "PATCH", url, headers=self._operation_headers(csrf=self.second_csrf), data=json_object, verify=False
        )
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        else:
            return response.json()["url"], HTTPStatus.OK

    def get_avi_cluster_info(self):
        """ """
        url = AlbEndpoint.AVI_HA.format(ip=self.avi_host)
        try:
            response = RequestApiUtil.exec_req(
                "GET", url, headers=self._operation_headers(csrf=self.second_csrf), verify=False
            )
            if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                return None, response.text
            return response.json(), "SUCCESS"
        except Exception as e:
            return None, str(e)

    def form_avi_ha_cluster(self, list_of_ips):
        """
        :param list_of_ips: list AVI HA IP's, comes from json file in sequence
                            NODE-01,NODE-02,NODE-03,NODE-04 for AVI HA nodes
        """
        try:
            info, status = self.get_avi_cluster_info()
            if info is None:
                return None, "Failed to get cluster info " + str(status)
            nodes = info["nodes"]
            _list = []
            _cluster = {}
            for node in nodes:
                try:
                    _list.append(node["ip"]["addr"])
                    # first avi ip check
                    if str(node["ip"]["addr"]) == list_of_ips[0]:
                        _cluster["vm_uuid"] = node["vm_uuid"]
                        _cluster["vm_mor"] = node["vm_mor"]
                        _cluster["vm_hostname"] = node["vm_hostname"]
                except KeyError:
                    pass
            if list_of_ips[0] in _list and list_of_ips[1] in _list and list_of_ips[2] in _list:
                current_app.logger.info("AVI HA cluster is already configured")
                return "SUCCESS", "Avi HA cluster is already configured"
            current_app.logger.info("Forming Ha cluster")
            payload = AlbPayload.AVI_HA_CLUSTER.format(
                cluster_uuid=info["uuid"],
                cluster_name="Alb-Cluster",
                cluster_ip1=list_of_ips[0],
                vm_uuid_get=_cluster["vm_uuid"],
                vm_mor_get=_cluster["vm_mor"],
                vm_hostname_get=_cluster["vm_hostname"],
                cluster_ip2=list_of_ips[1],
                cluster_ip3=list_of_ips[2],
                tennat_uuid_get=info["tenant_uuid"],
                virtual_ip_get=list_of_ips[3],
            )
            url = AlbEndpoint.AVI_HA.format(ip=self.avi_host)
            response = RequestApiUtil.exec_req(
                "PUT", url, headers=self._operation_headers(csrf=self.second_csrf), data=payload, verify=False
            )
            if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                return None, response
            count = 0
            list_of_nodes = []
            # TODO improvised pooling
            while count < 180:
                try:
                    response = RequestApiUtil.exec_req(
                        "GET", url, headers=self._operation_headers(csrf=self.second_csrf), verify=False
                    )
                    if len(response.json()["nodes"]) == 3:
                        for node in response.json()["nodes"]:
                            list_of_nodes.append(node["ip"]["addr"])
                        break
                except KeyError:
                    pass
                time.sleep(10)
                current_app.logger.info("Waited " + str(count * 10) + "s for getting cluster ips, retrying")
                count = count + 1

            # if avi_ip not in list_of_nodes or avi_ip2 not in list_of_nodes or not avi_ip3 in list_of_nodes:
            if list_of_ips[0] and list_of_ips[1] and list_of_ips[2] in list_of_nodes:
                current_app.logger.info("Avi IPs available")
            else:
                return None, "Failed to form the cluster ips not found in nodes list"
            current_app.logger.info("Getting cluster runtime status")
            runtime = 0
            run_time_url = AlbEndpoint.AVI_HA_RUNTIME.format(ip=self.avi_host)
            all_up = False
            while runtime < 180:
                try:
                    response_csrf = RequestApiUtil.exec_req(
                        "GET", run_time_url, headers=self._operation_headers(csrf=self.second_csrf), verify=False
                    )
                    if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                        return None, "Failed to get cluster runtime status " + (str(response_csrf.text))
                    node_statuses = response_csrf.json()["node_states"]
                    if node_statuses is not None:
                        # print all the 3 nodes details
                        for i in range(2):
                            current_app.logger.info(
                                f'Checking node {node_statuses[i]["mgmt_ip"]} state: ' f'{node_statuses[i]["state"]}'
                            )
                        current_app.logger.info("*" * 87)
                        if (
                            node_statuses[0]["state"] == "CLUSTER_ACTIVE"
                            and node_statuses[1]["state"] == "CLUSTER_ACTIVE"
                            and node_statuses[2]["state"] == "CLUSTER_ACTIVE"
                        ):
                            all_up = True
                            break
                except KeyError:
                    pass
                except Exception:
                    pass
                runtime = runtime + 1
                time.sleep(10)
            if not all_up:
                return None, "All nodes are not in active state on waiting 30 min"
            return "SUCCESS", "Successfully formed Ha Cluster"
        except Exception as e:
            return None, str(e)
