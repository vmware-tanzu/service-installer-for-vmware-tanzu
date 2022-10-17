#!/usr/local/bin/python3

#  Copyright 2022 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause
import time
import requests
import base64
import json
from util.ShellHelper import runShellCommandAndReturnOutput, runProcess, runShellCommandAndReturnOutputAsList, \
    verifyPodsAreRunning
from util.logger_helper import LoggerHelper, log
from constants.constants import RegexPattern

logger = LoggerHelper.get_logger(name='Pre Setup')


class CleanUpUtil:
    def __int__(self):
        pass

    def is_management_cluster_exists(self, mgmt_cluster: str) -> bool:
        """
        Method to check that if Tanzu management cluster exists or not

        :param: mgmt_cluster: Name of management cluster to be checked that exists or not
        :return: bool
                 True -> If management cluster exists, else
                 False
        """
        try:
            tanzu_mgmt_get_cmd = ["tanzu", "management-cluster", "get"]
            cmd_out = runShellCommandAndReturnOutput(tanzu_mgmt_get_cmd)
            if cmd_out[1] == 0:
                try:
                    if cmd_out[0].__contains__(mgmt_cluster):
                        return True
                    else:
                        return False
                except:
                    return False
            else:
                return False
        except:
            return False

    def delete_mgmt_cluster(self, mgmt_cluster):
        try:
            logger.info("Delete Management cluster - " + mgmt_cluster)
            delete_command = ["tanzu", "management-cluster", "delete", "--force", "-y"]
            runProcess(delete_command)

            deleted = False
            count = 0
            while count < 360 and not deleted:
                if self.is_management_cluster_exists(mgmt_cluster):
                    logger.debug("Management cluster is still not deleted... retrying in 10s")
                    time.sleep(10)
                    count = count + 1
                else:
                    deleted = True
                    break

            if not deleted:
                logger.error(
                    "Management cluster " + mgmt_cluster + " is not deleted even after " + str(count * 5)
                    + "s")
                return False
            else:
                return True
        except Exception as e:
            logger.error(str(e))
            return False

    def delete_cluster(self, cluster):
        try:
            logger.info("Initiating deletion of cluster - " + cluster)
            delete = ["tanzu", "cluster", "delete", cluster, "-y"]
            delete_status = runShellCommandAndReturnOutputAsList(delete)
            if delete_status[1] != 0:
                logger.error("Command to delete - " + cluster + " Failed")
                logger.debug(delete_status[0])
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed delete cluster - " + cluster,
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            cluster_running = ["tanzu", "cluster", "list"]
            command_status = runShellCommandAndReturnOutputAsList(cluster_running)
            if command_status[1] != 0:
                logger.error("Failed to run command to check status of workload cluster - " + cluster)
                return False
            deleting = True
            count = 0
            while count < 360 and deleting:
                if verifyPodsAreRunning(cluster, command_status[0], RegexPattern.deleting) or \
                        verifyPodsAreRunning(cluster, command_status[0], RegexPattern.running):
                    logger.info("Waiting for " + cluster + " deletion to complete...")
                    logger.info("Retrying in 10s...")
                    time.sleep(10)
                    count = count + 1
                    command_status = runShellCommandAndReturnOutputAsList(cluster_running)
                else:
                    deleting = False
            if not deleting:
                return True

            logger.error("waited for " + str(count * 5) + "s")
            return False
        except Exception as e:
            logger.error("Exception occurred while deleting cluster " + str(e))
            return False

    def getWCPStatus(self, cluster_id, jsonspec):
        """
        :param cluster_id:
        :return:
         False: If WCP is not enabled
        True: if WCP is enabled and any state, not necessarily running status
        """
        vcenter_ip = jsonspec['envSpec']['vcenterDetails']['vcenterAddress']
        vcenter_username = jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser']
        str_enc = jsonspec['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"]
        base64_bytes = str_enc.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        password = enc_bytes.decode('ascii').rstrip("\n")
        if not (vcenter_ip or vcenter_username or password):
            return False, "Failed to fetch VC details"

        sess = requests.post("https://" + str(vcenter_ip) + "/rest/com/vmware/cis/session",
                             auth=(vcenter_username, password), verify=False)
        if sess.status_code != 200:
            logger.error("Connection to vCenter failed")
            return False, "Connection to vCenter failed"
        else:
            vc_session = sess.json()['value']

        header = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "vmware-api-session-id": vc_session
        }
        url = "https://" + vcenter_ip + "/api/vcenter/namespace-management/clusters/" + cluster_id
        response_csrf = requests.request("GET", url, headers=header, verify=False)
        if response_csrf.status_code != 200:
            if response_csrf.status_code == 400:
                if response_csrf.json()["messages"][0][
                    "default_message"] == "Cluster with identifier " + cluster_id + " does " \
                                                                                    "not have Workloads enabled.":
                    return False, None
        else:
            return True, response_csrf.json()["config_status"]
