# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause


__author__ = "Tasmiya Bano"

import base64
import json
import os
import time
from http import HTTPStatus

import requests
import yaml
from flask import current_app
from tqdm import tqdm

from common.common_utilities import waitForProcessWithStatus
from common.constants.constants import KubectlCommands
from common.constants.tmc_api_constants import TmcConstants, TmcPayloads
from common.lib.govc.govc_client import GOVClient
from common.lib.vcenter.vcenter_endpoints_operations import VCEndpointOperations
from common.operation.constants import SAS, Env, RegexPattern
from common.operation.ShellHelper import grabPipeOutput, runShellCommandAndReturnOutputAsList
from common.util.common_utils import CommonUtils
from common.util.file_helper import FileHelper
from common.util.kubectl_util import KubectlUtil
from common.util.local_cmd_helper import LocalCmdHelper
from common.util.request_api_util import RequestApiUtil
from common.util.tanzu_util import TanzuUtil
from common.util.tkgs_util import TkgsUtil


class SaaSUtil:
    tmc_header = {}

    def __init__(self, env, spec):
        self.spec = spec
        self.env = env
        self.kubectl_util = KubectlUtil()

        if self.env == Env.VMC:
            self.tmc_refresh_token = self.spec.saasEndpoints.tmcDetails.tmcRefreshToken
            self.to_url = self.spec.saasEndpoints.tanzuObservabilityDetails.tanzuObservabilityUrl
            self.to_token = self.spec.saasEndpoints.tanzuObservabilityDetails.tanzuObservabilityRefreshToken
            self.tmc_availability = str(self.spec.saasEndpoints.tmcDetails.tmcAvailability)
            self.tmc_url = self.spec.saasEndpoints.tmcDetails.tmcInstanceURL
        else:
            self.tkgs_util: TkgsUtil = TkgsUtil(self.spec)
            self.tmc_refresh_token = self.spec.envSpec.saasEndpoints.tmcDetails.tmcRefreshToken
            self.tmc_availability = str(self.spec.envSpec.saasEndpoints.tmcDetails.tmcAvailability)
            self.tmc_url = self.spec.envSpec.saasEndpoints.tmcDetails.tmcInstanceURL
            if not TkgsUtil.is_env_tkgs_wcp(self.spec, self.env):
                self.to_url = self.spec.envSpec.saasEndpoints.tanzuObservabilityDetails.tanzuObservabilityUrl
                self.to_token = self.spec.envSpec.saasEndpoints.tanzuObservabilityDetails.tanzuObservabilityRefreshToken

        SaaSUtil.tmc_header = self.fetch_tmc_header()

    @staticmethod
    def get_tmc_header_static(tmc_refresh_token):
        login_response = RequestApiUtil.exec_req(
            "POST",
            TmcConstants.TMC_LOGIN_API.format(refresh_token=tmc_refresh_token),
            headers={},
            data={},
            verify=False,
        )

        if not RequestApiUtil.verify_resp(login_response, status_code=HTTPStatus.OK):
            raise Exception(f"Error while logging into TMC using provided refresh token: {login_response}")

        access_token = login_response.json()["access_token"]

        header = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": access_token,
        }
        return header

    def fetch_tmc_header(self):
        """
        Create TMC header by fecthing access token from TMC
        :return: header dictionary
        """
        if self.check_tmc_enabled():
            return SaaSUtil.get_tmc_header_static(self.tmc_refresh_token)
        else:
            return {}

    def register_management_cluster_tmc(self, management_cluster, is_proxy, type, cluster_group):
        if not self.check_tmc_Register(management_cluster, True):
            proxy_cred_state = self.create_tkgm_tmc_proxy_credentials(
                cluster_name=management_cluster, is_proxy=is_proxy, type=type, register=True
            )
            if proxy_cred_state[1] != 200:
                return str(proxy_cred_state[0]), 500
            proxy_name = TmcConstants.TMC_PROXY_NAME.format(cluster_name=management_cluster)

            if str(is_proxy).lower() == "true":
                current_app.logger.info("Registering to TMC with proxy")
                proxy_name = TmcConstants.TMC_PROXY_NAME.format(cluster_name=management_cluster)
                register_payload = TmcPayloads.TKGM_MGMT_CLUSTER_REGISTER_PROXY.format(
                    management_cluster=management_cluster, cluster_group=cluster_group, proxy_name=proxy_name
                )
                management_url = TmcConstants.REGISTER_TMC_MGMT_CLUSTER.format(tmc_url=self.tmc_url)
            else:
                current_app.logger.info("Registering to TMC")
                register_payload = TmcPayloads.TKGM_MGMT_CLUSTER_REGISTER.format(
                    management_cluster=management_cluster, cluster_group=cluster_group
                )
                management_url = TmcConstants.REGISTER_TMC_MGMT_CLUSTER.format(tmc_url=self.tmc_url)

            current_app.logger.info("Fetching Manifest for management cluster registration with TMC")
            response = RequestApiUtil.exec_req(
                "POST", management_url, headers=self.tmc_header, data=register_payload, verify=False
            )
            if response.status_code == 409:
                return None, "Management cluster exist on TMC, but in disconnected state. Please try deleting and retry"
            if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                return None, response.text
            time.sleep(5)

            mgmt_manifest_url = TmcConstants.TMC_MGMT_MANIFEST.format(
                tmc_url=self.tmc_url, management_cluster=management_cluster
            )
            response = RequestApiUtil.exec_req(
                "GET", mgmt_manifest_url, headers=self.tmc_header, data=register_payload, verify=False
            )
            data = response.json()["manifest"]
            FileHelper.write_to_file(data, TmcConstants.TKGM_REGISTRAION_FILE)

            """
            Applying yaml from registration link and wait for registration to complete
            """
            current_app.logger.info("Applying registration yaml")
            command = KubectlCommands.APPLY_YAML.format(file_name=TmcConstants.TKGM_REGISTRAION_FILE)
            create_output = runShellCommandAndReturnOutputAsList(command)
            if create_output[1] != 0:
                return None, str(create_output[0])
            current_app.logger.info("Registered to TMC")
            current_app.logger.info("Waiting for 5 min for health status = ready…")
            for i in tqdm(range(300), desc="Waiting for health status…", ascii=False, ncols=75):
                time.sleep(1)
            state = SaaSUtil.check_cluster_state_on_tmc(self.tmc_url, self.tmc_refresh_token, management_cluster, True)
            if state[0] == "SUCCESS":
                current_app.logger.info("Registered to TMC successfully")
                return "SUCCESS", 200
            else:
                return None, "Failed to register management cluster with TMC"
        else:
            current_app.logger.info("Management cluster is already registered with TMC")
            return "SUCCESS", 200

    def check_tmc_Register(self, cluster, is_management):
        try:
            tmc_clusters_res = self.list_tmc_clusters(is_management)
            if not tmc_clusters_res[0]:
                return False
            tmc_cluster_list = tmc_clusters_res[1]
            for clster in tmc_cluster_list:
                if cluster == clster["fullName"]["name"]:
                    state = SaaSUtil.check_cluster_state_on_tmc(
                        self.tmc_url, self.tmc_refresh_token, cluster, is_management
                    )
                    if state[0] == "SUCCESS":
                        return True
                    else:
                        return False
            return False
        except Exception as ex:
            current_app.logger.error(str(ex))
            return False

    @staticmethod
    def return_list_of_mgmt_clusters(tmc_url, tmc_refresh_token):
        try:
            mgmt_cluster_list = []
            tmc_header = SaaSUtil.get_tmc_header_static(tmc_refresh_token)
            get_cluster_url = TmcConstants.LIST_TMC_MGMT_CLUSTERS.format(tmc_url=tmc_url)
            response = RequestApiUtil.exec_req("GET", get_cluster_url, headers=tmc_header, data={}, verify=False)
            if RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                res_json = response.json()
                for clster in res_json["managementClusters"]:
                    mgmt_cluster_list.append(clster["fullName"]["name"])
                return True, mgmt_cluster_list
            else:
                return False, []
        except Exception as ex:
            current_app.logger.error(str(ex))
            return False, []

    @staticmethod
    def return_list_of_tmc_clusters(tmc_url, tmc_refresh_token, cluster):
        cluster_list = []
        get_cluster_url = TmcConstants.LIST_TMC_CLUSTERS.format(tmc_url=tmc_url)
        tmc_header = SaaSUtil.get_tmc_header_static(tmc_refresh_token)
        response = RequestApiUtil.exec_req("GET", get_cluster_url, headers=tmc_header, data={}, verify=False)
        if RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            res_json = response.json()
            for clstrs in res_json["clusters"]:
                if cluster == clstrs["fullName"]["name"]:
                    cluster_list.append(clstrs["fullName"]["name"])
                    cluster_list.append(clstrs["fullName"]["managementClusterName"])
                    cluster_list.append(clstrs["fullName"]["provisionerName"])
        return cluster_list

    @staticmethod
    def check_cluster_state_on_tmc(tmc_url, tmc_refresh_token, cluster, is_management):
        try:
            tmc_header = SaaSUtil.get_tmc_header_static(tmc_refresh_token)
            if is_management:
                try:
                    management_cluster_url = TmcConstants.FETCH_TMC_MGMT_CLUSTER.format(
                        tmc_url=tmc_url, management_cluster=cluster
                    )
                    response = RequestApiUtil.exec_req(
                        "GET", management_cluster_url, headers=tmc_header, data={}, verify=False
                    )
                    if RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                        json_ = response.json()
                        phase = json_["managementCluster"]["status"]["phase"]
                        health = json_["managementCluster"]["status"]["health"]
                        message = json_["managementCluster"]["status"]["conditions"]["READY"]["message"]
                        if (
                            phase == "READY"
                            and health == "HEALTHY"
                            and message == "management cluster is connected to TMC and healthy"
                        ):
                            return "SUCCESS", 200
                    else:
                        return "Failed", 500

                except Exception:
                    return "Failed", 500
            else:
                cluster_details = []
                cluster_details = SaaSUtil.return_list_of_tmc_clusters(tmc_url, tmc_refresh_token, cluster)
                cluster_url = TmcConstants.GET_WORKLOAD_CLUSTER_STATUS.format(
                    tmc_url=tmc_url,
                    cluster_name=cluster_details[0],
                    management_cluster=cluster_details[1],
                    provisioner=cluster_details[2],
                )
                response = RequestApiUtil.exec_req("GET", cluster_url, headers=tmc_header, data={}, verify=False)
                if RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                    json_ = response.json()
                    phase = json_["cluster"]["status"]["phase"]
                    health = json_["cluster"]["status"]["health"]
                    message = json_["cluster"]["status"]["conditions"]["Agent-READY"]["message"]
                    if (
                        phase == "READY"
                        and health == "HEALTHY"
                        and message == "cluster is connected to TMC and healthy"
                    ):
                        return "SUCCESS", 200
                else:
                    return "Failed", 500
        except Exception as e:
            return None, str(e)

    def create_tkgm_tmc_proxy_credentials(self, cluster_name, is_proxy, type, register=True):
        """
        Create proxy credentials on TMC before registering clusters
        :param cluster_name: workload cluster name
        :param is_proxy: True if proxy is enabled, else False
        :param type: workload, shared or management
        :param register: True or False
        :return: 200 on success else 500
        """
        try:
            if register and type != "management":
                file = TmcConstants.WORKLOAD_KUBE_CONFIG_FILE
                os.system("rm -rf " + file)
            """
            Obtain kube config for the cluster
            """
            if register and type != "management":
                current_app.logger.info("Fetching Kube config for workload cluster " + cluster_name)
                cluster_url = TmcConstants.GET_WORKLOAD_CLUSTER_KUBECONFIG.format(cluster_name=cluster_name)
                response = RequestApiUtil.exec_req("GET", cluster_url, headers=self.tmc_header, data={}, verify=False)
                if RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                    current_app.logger.info("Fetched kubeconfig successfully")

            """
            If Proxy is set to true, fetch proxy details and parse the strings
            """
            if str(is_proxy).lower() == "true":
                current_app.logger.info("Creating TMC Proxy credentials...")
                proxy_credential_name = TmcConstants.TMC_PROXY_NAME.format(cluster_name=cluster_name)

                if type == "workload":
                    http_proxy = str(self.spec.envSpec.proxySpec.tkgWorkload.httpProxy)
                    https_proxy = str(self.spec.envSpec.proxySpec.tkgWorkload.httpsProxy)
                    no_proxy = str(self.spec.envSpec.proxySpec.tkgWorkload.noProxy)

                elif type == "shared":
                    http_proxy = str(self.spec.envSpec.proxySpec.tkgSharedservice.httpProxy)
                    https_proxy = str(self.spec.envSpec.proxySpec.tkgSharedservice.httpsProxy)
                    no_proxy = str(self.spec.envSpec.proxySpec.tkgSharedservice.noProxy)

                elif type == "management":
                    http_proxy = str(self.spec.envSpec.proxySpec.tkgMgmt.httpProxy)
                    https_proxy = str(self.spec.envSpec.proxySpec.tkgMgmt.httpsProxy)
                    no_proxy = str(self.spec.envSpec.proxySpec.tkgMgmt.noProxy)

                status, message = self.create_tmc_proxy_credential(
                    http_proxy, https_proxy, no_proxy, proxy_credential_name
                )
                if status is None:
                    return message + message, 500
                current_app.logger.info("Successfully created credentials for TMC Proxy")
                return proxy_credential_name, 200
            current_app.logger.info("Proxy credential configuration not required")
            return "Proxy credential configuration not required", 200
        except Exception as e:
            return "Proxy credential creation on TMC failed for cluster " + cluster_name + " " + str(e), 500

    def wait_for_supervisor_tmc_registration(self, super_cls):
        """
        Wait for supervisor cluster TMC registration to complete
        :param super_cls: supervisor cluster name
        :return: 200 if success else, 500
        """
        registered = False
        count = 0
        management_cluster_url = TmcConstants.FETCH_TMC_MGMT_CLUSTER.format(
            tmc_url=self.tmc_url, management_cluster=super_cls
        )
        response = RequestApiUtil.exec_req(
            "GET", management_cluster_url, headers=SaaSUtil.tmc_header, data={}, verify=False
        )
        if RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            json_ = response.json()
            try:
                phase = json_["managementCluster"]["status"]["phase"]
                health = json_["managementCluster"]["status"]["health"]
                message = json_["managementCluster"]["status"]["conditions"]["READY"]["message"]
                if (
                    phase == "READY"
                    and health == "HEALTHY"
                    and message == "management cluster is connected to TMC and healthy"
                ):
                    registered = True
                    return "SUCCESS", 200
            except KeyError:
                current_app.logger.info("TMC Registration is is still in progress, retrying...")
        else:
            return "Failed to obtain register status for TMC", 500
        while not registered and count < 30:
            response = RequestApiUtil.exec_req(
                "GET", management_cluster_url, headers=SaaSUtil.tmc_header, data={}, verify=False
            )
            if RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                json_ = response.json()
                try:
                    phase = json_["managementCluster"]["status"]["phase"]
                    health = json_["managementCluster"]["status"]["health"]
                    message = json_["managementCluster"]["status"]["conditions"]["READY"]["message"]
                    if (
                        phase == "READY"
                        and health == "HEALTHY"
                        and message == "management cluster is connected to TMC and healthy"
                    ):
                        registered = True
                        return "SUCCESS", 200
                    else:
                        current_app.logger.info("Waited for  " + str(count * 30) + "s, retrying.")
                        count = count + 1
                        time.sleep(30)
                except KeyError:
                    current_app.logger.info("TMC Registration in progress...")
                    current_app.logger.info("Waited for  " + str(count * 30) + "s, retrying.")
                    count = count + 1
                    time.sleep(30)
        if not registered:
            current_app.logger.error("TMC registration still not completed " + str(count * 30))
            return "TMC registration still not completed " + str(count * 30), 500
        else:
            return "TMC Registration successful", 200

    def check_os_flavor_for_tmc(self, is_shared, is_workload):
        """
        Validate photon OS is selected for TMC integration
        :param is_shared: True, if shared cluster else False
        :param is_workload: True if workload cluster else, False
        :return: 200 if success else, 500
        """

        os_flavor = CommonUtils.get_os_flavor(self.env, self.spec)
        if os_flavor[0] is None:
            return os_flavor[1], 500

        if (
            (os_flavor[0] == "photon")
            and (not is_shared or os_flavor[2] == "photon")
            and (not is_workload or os_flavor[1] == "photon")
        ):
            return "Successfully validated Kubernetes OVA images are photon", 200
        else:
            return "Only photon images are supported with TMC", 500

    def get_network_Path_tmc(self, network_name, vcenter_ip, vcenter_username, password):
        govc_client: GOVClient = GOVClient(vcenter_ip, vcenter_username, password, None, None, None, LocalCmdHelper())
        count = 0
        net = ""
        while count < 120:
            output = govc_client.find_objects_by_name(network_name)
            if network_name in str(output) and "/network" in str(output):
                if isinstance(output, list):
                    for o in output:
                        if "/network" in str(o):
                            net = o
                            break
                else:
                    net = output
                if net:
                    current_app.logger.info("Network is available " + str(net))
                    return net
            time.sleep(5)
            count = count + 1
        return None

    def register_supervisor_cluster_tmc(
        self, management_cluster, vcenter, vcenter_user, vcenter_password, proxy_enabled
    ):
        """
        Register TKGs Supervisor cluster to TMC
        :param management_cluster: supervisor cluster name
        :param vcenter: vcenter IP/FQDN
        :param vcenter_user: vcenter username
        :param vcenter_password: vcenter password
        :return: SUCCESS is registered successfully else None
        """
        try:
            """
            Check if supervisor cluster is already registered to TMC
            """
            is_management_registered = False
            headers = SaaSUtil.tmc_header
            body = {}
            try:
                management_cluster_url = TmcConstants.FETCH_TMC_MGMT_CLUSTER.format(
                    tmc_url=self.tmc_url, management_cluster=management_cluster
                )
                response = RequestApiUtil.exec_req(
                    "GET", management_cluster_url, headers=headers, data={}, verify=False
                )
                if RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                    json_ = response.json()
                    phase = json_["managementCluster"]["status"]["phase"]
                    health = json_["managementCluster"]["status"]["health"]
                    message = json_["managementCluster"]["status"]["conditions"]["READY"]["message"]
                    if (
                        phase == "READY"
                        and health == "HEALTHY"
                        and message == "management cluster is connected to TMC and healthy"
                    ):
                        return "SUCCESS", "Management cluster is already registered to tmc"
                else:
                    is_management_registered = False
            except Exception:
                is_management_registered = False
            """
            If not registered, initiate the registration by running TMC APIs
            """
            if not is_management_registered:
                cluster_group = self.spec.envSpec.saasEndpoints.tmcDetails.tmcSupervisorClusterGroupName
                if not cluster_group:
                    cluster_group = "default"
                if proxy_enabled:
                    proxy_name = TmcConstants.TMC_PROXY_NAME.format(cluster_name=management_cluster)
                    register_payload = TmcPayloads.SUPERVISOR_CLUSTER_REGISTER_PROXY.format(
                        management_cluster=management_cluster, cluster_group=cluster_group, proxy_name=proxy_name
                    )
                    management_url = TmcConstants.REGISTER_TMC_MGMT_CLUSTER.format(tmc_url=self.tmc_url)
                    import json

                    response = RequestApiUtil.exec_req(
                        "POST", management_url, headers=headers, data=register_payload, verify=False
                    )
                    if response.status_code == 409:
                        return (
                            None,
                            "Supervisor cluster exist on TMC, but in disconnected state. Please try deleting and retry",
                        )
                    if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                        return None, response.text

                    management_manifest_url = TmcConstants.TMC_MGMT_MANIFEST.format(
                        tmc_url=self.tmc_url, management_cluster=management_cluster
                    )
                    response = RequestApiUtil.exec_req(
                        "GET", management_manifest_url, headers=headers, data=body, verify=False
                    )
                    if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                        return None, response.text

                    """
                    Fetch manifest and registration link details from the API response
                    """
                    manifest = response.json()["manifest"]
                    t = manifest.split("\n")
                    count = 0
                    bots_trap_token = ""
                    reg_link = ""
                    for d in t:
                        count = count + 1
                        if "tmc.cloud.vmware.com/bootstrap-token:" in d:
                            bots_trap_token = d.split("tmc.cloud.vmware.com/bootstrap-token:")[1].strip()
                            bots_trap_token = bots_trap_token.strip().replace('"', "")
                        if "registrationLink:" in d:
                            reg_link = d.split("registrationLink:")[1]
                            reg_link = reg_link.strip().replace('"', "")
                        if bots_trap_token and reg_link:
                            break
                    if not bots_trap_token and not reg_link:
                        return None, "Failed to get boots trap token and reg link from manifest"
                    main_command = ["kubectl", "get", "ns"]
                    sub_command = ["grep", "svc-tmc"]
                    command_cert = grabPipeOutput(main_command, sub_command)
                    if command_cert[1] != 0:
                        return None, "Failed to get namespace details"
                    tmc_namespace = command_cert[0].split("\\s")[0].strip().split()[0]
                    data = TmcPayloads.SUPERVISOR_AGENT_INSTALLER_YAML_PROXY.format(
                        tmc_namespace=tmc_namespace, bots_trap_token=bots_trap_token, reg_link=str(reg_link)
                    )
                    data = json.dumps(data)
                    data = json.loads(json.loads(data.replace("'", "")))
                    FileHelper.dump_yaml(data, TmcConstants.TKGS_REGISTRAION_FILE)

                else:
                    register_payload = TmcPayloads.SUPERVISOR_CLUSTER_REGISTER.format(
                        management_cluster=management_cluster, cluster_group=cluster_group
                    )
                    management_url = TmcConstants.REGISTER_TMC_MGMT_CLUSTER.format(tmc_url=self.tmc_url)
                    import json

                    response = RequestApiUtil.exec_req(
                        "POST", management_url, headers=headers, data=register_payload, verify=False
                    )
                    if response.status_code == 409:
                        return (
                            None,
                            "Supervisor cluster exist on TMC, but in disconnected state. Please try deleting and retry",
                        )
                    if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                        return None, response.text
                    time.sleep(5)
                    registrationUrl = response.json()["managementCluster"]["status"]["registrationUrl"]
                    management_manifest_url = TmcConstants.TMC_MGMT_MANIFEST.format(
                        tmc_url=self.tmc_url, management_cluster=management_cluster
                    )
                    response = RequestApiUtil.exec_req(
                        "GET", management_manifest_url, headers=self.tmc_header, data={}, verify=False
                    )
                    if response.status_code != 200:
                        return None, response.text
                    main_command = ["kubectl", "get", "ns"]
                    sub_command = ["grep", "svc-tmc"]
                    command_cert = grabPipeOutput(main_command, sub_command)
                    if command_cert[1] != 0:
                        return None, "Failed to get namespace details"
                    tmc_namespace = command_cert[0].split("\\s")[0].strip().split()[0]
                    data = TmcPayloads.SUPERVISOR_AGENT_INSTALLER_YAML.format(
                        tmc_namespace=tmc_namespace, reg_link=str(registrationUrl)
                    )

                    data = json.dumps(data)
                    data = json.loads(json.loads(data.replace("'", "")))
                    data = yaml.dump(data)
                    data = yaml.safe_load(data)
                    FileHelper.dump_yaml(data, TmcConstants.TKGS_REGISTRAION_FILE)

                """
                Fetch cluster endpoint/workload IP address
                """
                vc_operation: VCEndpointOperations = VCEndpointOperations(vcenter, vcenter_user, vcenter_password)
                session = vc_operation.get_session()
                if session[1] != 200:
                    return None, "Failed to fetch session ID for vCenter - " + vcenter

                session_id = session[0]

                header = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "vmware-api-session-id": session_id,
                }
                cluster_name = self.spec.envSpec.vcenterDetails.vcenterCluster

                cluster_endpoint, status_code = self.tkgs_util.get_cluster_end_point(cluster_name, header)
                if status_code != HTTPStatus.OK:
                    return None, status_code
                supervisor_tmc = self.tkgs_util.supervisor_tmc(cluster_endpoint)
                if supervisor_tmc[1] != HTTPStatus.OK:
                    return None, supervisor_tmc[0]

                """
                Apply yaml with registration link and wait for registration to complete
                """
                command = KubectlCommands.APPLY_YAML.format(file_name=TmcConstants.TKGS_REGISTRAION_FILE)
                create_output = runShellCommandAndReturnOutputAsList(command)
                if create_output[1] != 0:
                    return None, str(create_output[0])
                current_app.logger.info("Registered to TMC")
                count = 0
                while count < 60:
                    try:
                        management_cluster_url = TmcConstants.FETCH_TMC_MGMT_CLUSTER.format(
                            tmc_url=self.tmc_url, management_cluster=management_cluster
                        )
                        response = RequestApiUtil.exec_req(
                            "GET", management_cluster_url, headers=headers, data=body, verify=False
                        )
                        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                            return None, response.text
                        json = response.json()
                        phase = json["managementCluster"]["status"]["phase"]
                        health = json["managementCluster"]["status"]["health"]
                        message = json["managementCluster"]["status"]["conditions"]["READY"]["message"]
                        if (
                            phase == "READY"
                            and health == "HEALTHY"
                            and message == "management cluster is connected to TMC and healthy"
                        ):
                            return "SUCCESS", "Management cluster registered to tmc Successfully"
                        else:
                            current_app.logger.info(
                                "Supervisor cluster state : " + phase + " " + health + " " + message
                            )
                    except Exception:
                        pass
                    time.sleep(30)
                    count = count + 1
                    current_app.logger.info(
                        "Waited for " + str(count * 30) + "s, retrying to check management cluster status on TMC"
                    )
                return None, "Supervisor cluster not registered on waiting " + str(count * 30) + "s"
        except Exception as e:
            return None, str(e)

    # TODO: move function body to tmc constant file
    def payload_tmc_cluster_creation(
        self,
        management_cluster_name,
        provisioner_name,
        cluster_name,
        cluster_group,
        pod_cidr,
        service_cidr,
        ssh_key,
        vcenter_server,
        cpu,
        disk_gib,
        memory_mib,
        worker_node_count,
        labels,
        version,
        datacenter,
        datastore,
        folder,
        network,
        resourcepool,
        os_type,
        os_version,
        os_arch,
        template_path,
        proxy_name,
        control_plane_node_count,
    ):
        """
        Return payload for workload cluster registration with TMC
        :param management_cluster_name: Management cluster name
        :param provisioner_name: Provisioner name
        :param cluster_name: workload cluster name
        :param cluster_group: Cluster group on TMC
        :param pod_cidr: POD CIDR
        :param service_cidr: Service CIDR
        :param ssh_key: SSH Key
        :param vcenter_server: vcenter IP
        :param cpu: CPU limit
        :param disk_gib: disk in GB
        :param memory_mib: Memory in MB
        :param worker_node_count: worker node count
        :param labels: labels for TMC
        :param version: kubernetes OVA version
        :param datacenter: datacenter
        :param datastore: Datastore name
        :param folder: Folder
        :param network: network port
        :param resourcepool: resource pool
        :param os_type: OS type
        :param os_version: OS version
        :param os_arch: OS arch ex: amd64
        :param template_path: Template path
        :param proxy_name: proxy name
        :param control_plane_node_count: control plave count
        :return: 200 if success else, 500
        """
        if not proxy_name:
            body = {
                "tanzuKubernetesCluster": {
                    "fullName": {
                        "managementClusterName": management_cluster_name,
                        "provisionerName": provisioner_name,
                        "name": cluster_name,
                    },
                    "meta": {"labels": {"type": labels}},
                    "spec": {
                        "clusterGroupName": cluster_group,
                        "tmcManaged": True,
                        "topology": {
                            "version": version,
                            "clusterClass": "tkg-vsphere-default-v1.1.1",
                            "controlPlane": {
                                "replicas": control_plane_node_count,
                                "metadata": {},
                                "osImage": {"name": os_type, "version": os_version, "arch": os_arch},
                            },
                            "nodePools": [
                                {
                                    "spec": {
                                        "class": "tkg-worker",
                                        "replicas": worker_node_count,
                                        "metadata": {},
                                        "osImage": {"name": os_type, "version": os_version, "arch": os_arch},
                                    },
                                    "info": {"name": "md-0"},
                                }
                            ],
                            "variables": [
                                {
                                    "name": "vcenter",
                                    "value": {
                                        "server": vcenter_server,
                                        "datacenter": datacenter,
                                        "resourcePool": resourcepool,
                                        "folder": folder,
                                        "network": network,
                                        "datastore": datastore,
                                        "template": template_path,
                                        "cloneMode": "fullClone",
                                    },
                                },
                                {
                                    "name": "identityRef",
                                    "value": {"kind": "VSphereClusterIdentity", "name": "tkg-vc-default"},
                                },
                                {"name": "user", "value": {"sshAuthorizedKeys": [ssh_key]}},
                                {"name": "aviAPIServerHAProvider", "value": True},
                                {"name": "vipNetworkInterface", "value": "eth0"},
                                {"name": "cni", "value": "antrea"},
                                {
                                    "name": "worker",
                                    "value": {
                                        "machine": {
                                            "diskGiB": int(disk_gib),
                                            "memoryMiB": int(memory_mib),
                                            "numCPUs": int(cpu),
                                        },
                                        "network": {"nameservers": [], "searchDomains": []},
                                    },
                                },
                                {
                                    "name": "controlPlane",
                                    "value": {
                                        "machine": {
                                            "diskGiB": int(disk_gib),
                                            "memoryMiB": int(memory_mib),
                                            "numCPUs": int(cpu),
                                        },
                                        "network": {"nameservers": [], "searchDomains": []},
                                        "nodeLabels": [],
                                    },
                                },
                            ],
                            "network": {"pods": {"cidrBlocks": [pod_cidr]}, "services": {"cidrBlocks": [service_cidr]}},
                        },
                    },
                }
            }
        else:
            body = {
                "tanzuKubernetesCluster": {
                    "fullName": {
                        "managementClusterName": management_cluster_name,
                        "provisionerName": provisioner_name,
                        "name": cluster_name,
                    },
                    "meta": {"labels": {"type": labels}},
                    "spec": {
                        "clusterGroupName": cluster_group,
                        "tmcManaged": True,
                        "proxyName": proxy_name,
                        "topology": {
                            "version": version,
                            "clusterClass": "tkg-vsphere-default-v1.1.1",
                            "controlPlane": {
                                "replicas": control_plane_node_count,
                                "metadata": {},
                                "osImage": {"name": os_type, "version": os_version, "arch": os_arch},
                            },
                            "nodePools": [
                                {
                                    "spec": {
                                        "class": "tkg-worker",
                                        "replicas": worker_node_count,
                                        "metadata": {},
                                        "osImage": {"name": os_type, "version": os_version, "arch": os_arch},
                                    },
                                    "info": {"name": "md-0"},
                                }
                            ],
                            "variables": [
                                {
                                    "name": "vcenter",
                                    "value": {
                                        "server": vcenter_server,
                                        "datacenter": datacenter,
                                        "resourcePool": resourcepool,
                                        "folder": folder,
                                        "network": network,
                                        "datastore": datastore,
                                        "template": template_path,
                                        "cloneMode": "fullClone",
                                    },
                                },
                                {
                                    "name": "identityRef",
                                    "value": {"kind": "VSphereClusterIdentity", "name": "tkg-vc-default"},
                                },
                                {"name": "user", "value": {"sshAuthorizedKeys": [ssh_key]}},
                                {"name": "aviAPIServerHAProvider", "value": True},
                                {"name": "vipNetworkInterface", "value": "eth0"},
                                {"name": "cni", "value": "antrea"},
                                {
                                    "name": "worker",
                                    "value": {
                                        "machine": {
                                            "diskGiB": int(disk_gib),
                                            "memoryMiB": int(memory_mib),
                                            "numCPUs": int(cpu),
                                        },
                                        "network": {"nameservers": [], "searchDomains": []},
                                    },
                                },
                                {
                                    "name": "controlPlane",
                                    "value": {
                                        "machine": {
                                            "diskGiB": int(disk_gib),
                                            "memoryMiB": int(memory_mib),
                                            "numCPUs": int(cpu),
                                        },
                                        "network": {"nameservers": [], "searchDomains": []},
                                        "nodeLabels": [],
                                    },
                                },
                            ],
                            "network": {"pods": {"cidrBlocks": [pod_cidr]}, "services": {"cidrBlocks": [service_cidr]}},
                        },
                    },
                }
            }
        return body

    # TODO: move function body to tmc constant file
    def tkgs_payload_tmc_cluster_creation(
        self,
        supervisor_cluster_name,
        name_space,
        cluster_name,
        cluster_group,
        pod_cidr,
        service_cidr,
        version,
        node_storage_class,
        allowed_storage_class,
        default_storage_class,
        worker_vm_class,
        control_plane_vm_class,
        worker_node_count,
        proxy_name,
        high_availability,
        control_plane_volume_payload,
        worker_volume_payload,
    ):
        """
        Return payload for workload cluster registration with TMC
        :param supervisor_cluster_name: Management cluster name
        :param name_space: Provisioner name
        :param cluster_name: workload cluster name
        :param cluster_group: Cluster group on TMC
        :param pod_cidr: POD CIDR
        :param service_cidr: Service CIDR
        :param version: kubernetes OVA version
        :param node_storage_class: Node storage class
        :param allowed_storage_class: Allowed storage classes
        :param default_storage_class: Default storage class
        :param worker_vm_class: Worker VM class
        :param control_plane_vm_class: Control plane vm classes
        :param worker_node_count: Worker node count
        :param proxy_name: Proxy Name
        :return: 200 if success else, 500
        """

        body = {
            "cluster": {
                "fullName": {
                    "managementClusterName": supervisor_cluster_name,
                    "provisionerName": name_space,
                    "name": cluster_name,
                },
                "meta": {},
                "spec": {
                    "clusterGroupName": cluster_group,
                    "tkgServiceVsphere": {
                        "settings": {
                            "network": {"pods": {"cidrBlocks": [pod_cidr]}, "services": {"cidrBlocks": [service_cidr]}},
                            "storage": {
                                "classes": [allowed_storage_class],
                                "defaultClass": default_storage_class,
                            },
                        },
                        "distribution": {"version": version[1:]},
                        "topology": {
                            "controlPlane": {"class": control_plane_vm_class, "storageClass": allowed_storage_class},
                            "nodePools": [
                                {
                                    "spec": {
                                        "workerNodeCount": worker_node_count,
                                        "tkgServiceVsphere": {
                                            "class": worker_vm_class,
                                            "storageClass": node_storage_class,
                                        },
                                    },
                                    "info": {"name": "md-0"},
                                }
                            ],
                        },
                    },
                },
            }
        }

        if proxy_name:
            body["cluster"]["spec"]["proxyName"] = proxy_name
        if high_availability:
            body["cluster"]["spec"]["tkgServiceVsphere"]["topology"]["controlPlane"]["highAvailability"] = True
        if control_plane_volume_payload:
            body["cluster"]["spec"]["tkgServiceVsphere"]["topology"]["controlPlane"]["volumes"].append(
                control_plane_volume_payload
            )
        if worker_volume_payload:
            body["cluster"]["spec"]["tkgServiceVsphere"]["topology"]["nodePools"][0]["tkgServiceVsphere"][
                "volumes"
            ].append(worker_volume_payload)
        return body

    def create_tmc_proxy_credential(self, http_proxy, https_proxy, no_proxy, proxy_credential_name):
        """
        Create Proxy credentails for TKGs clusters registration
        :return: None if failure else, Success
        """
        is_cred_created = False
        try:
            headers = SaaSUtil.tmc_header
            current_app.logger.info("Getting current proxy credentials")
            """
            Check if proxy credentails are already created
            """
            try:
                url = TmcConstants.FETCH_PROXY_CREDENTIAL.format(
                    tmc_url=self.tmc_url, credential_name=proxy_credential_name
                )
                response = RequestApiUtil.exec_req("GET", url, headers=headers, data={}, verify=False)
                if RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                    phase = response.json()["credential"]["status"]["phase"]
                    status = response.json()["credential"]["status"]["conditions"]["Ready"]["status"]
                    http_added = response.json()["credential"]["meta"]["annotations"]["httpProxy"]
                    https_added = response.json()["credential"]["meta"]["annotations"]["httpsProxy"]
                    if "@" in http_proxy:
                        http_url_string = http_proxy.split("@")
                        http_url = http_url_string[0].split("//")[0] + "//" + http_url_string[1]
                    else:
                        http_url = http_proxy
                    if "@" in https_proxy:
                        https_url_string = https_proxy.split("@")
                        https_url = https_url_string[0].split("//")[0] + "//" + https_url_string[1]
                    else:
                        https_url = https_proxy
                    if phase == "CREATED" and status == "TRUE":
                        if http_added == http_url and https_added == https_url:
                            is_cred_created = True
                        else:
                            current_app.logger.error(
                                "Credential with name "
                                + proxy_credential_name
                                + " already exist with different proxy details. Please delete and retry"
                            )
                            current_app.logger.error("Existing HTTP: " + http_added)
                            current_app.logger.error("Existing HTTPS: " + https_added)
                            return None, "Failed"
                    else:
                        return None, "Credential state : " + phase + " " + status
                else:
                    current_app.logger.info("Credentials doesn't exist, creating now...")
            except Exception as e:
                current_app.logger.info(str(e))
            """
            Create the credentails if not created
            """
            if not is_cred_created:
                proxy_info = self.parse_proxy_strings(http_proxy, https_proxy)
                if proxy_info[0] is None:
                    return None, proxy_info[1]
                proxy_info = proxy_info[0]

                url = TmcConstants.CREATE_PROXY_CREDENTIAL.format(tmc_url=self.tmc_url)
                body = TmcPayloads.TKGS_PROXY_CREDENTIAL.format(
                    proxy_name=proxy_credential_name,
                    http_url=proxy_info["http_url"],
                    https_url=proxy_info["https_url"],
                    no_proxy=no_proxy,
                    http_user=proxy_info["http_user"],
                    http_password=proxy_info["http_password"],
                    https_user=proxy_info["https_user"],
                    https_password=proxy_info["https_password"],
                )
                response = RequestApiUtil.exec_req("POST", url, headers=headers, data=body, verify=False)
                if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                    current_app.logger.error(response.text)
                    return None, response.text
                current_app.logger.info("Proxy credentials created successfully")
            else:
                current_app.logger.info("Credential " + proxy_credential_name + " already created")
            return "Success", "Credential created"
        except Exception as e:
            return None, str(e)

    def parse_proxy_strings(self, http_proxy_, https_proxy_):
        """
        Parse http and https URLs and fetch username and password if present in URL
        :param http_proxy_: http proxy URL
        :param https_proxy_: https proxy url
        :return: dictionary of values if success else, None
        """
        try:
            proxy_details = {}
            if "@" in http_proxy_:
                http_proxy = http_proxy_.split(":")
                http_user = http_proxy[1].replace("//", "")
                http_user = requests.utils.unquote(http_user)
                _base64_bytes = http_user.encode("ascii")
                _enc_bytes = base64.b64encode(_base64_bytes)
                http_user = _enc_bytes.decode("ascii")

                http_url_string = http_proxy_.split("@")
                http_url = http_url_string[0].split("//")[0] + "//" + http_url_string[1]

                http_password = http_proxy[2].split("@")[0]
                http_password = requests.utils.unquote(http_password)
                _base64_bytes = http_password.encode("ascii")
                _enc_bytes = base64.b64encode(_base64_bytes)
                http_password = _enc_bytes.decode("ascii")
            else:
                http_user = ""
                http_password = ""
                http_url = http_proxy_

            if "@" in https_proxy_:
                https_proxy = https_proxy_.split(":")
                https_user = https_proxy[1].replace("//", "")
                https_user = requests.utils.unquote(https_user)
                _base64_bytes = https_user.encode("ascii")
                _enc_bytes = base64.b64encode(_base64_bytes)
                https_user = _enc_bytes.decode("ascii")

                https_url_string = https_proxy_.split("@")
                https_url = https_url_string[0].split("//")[0] + "//" + https_url_string[1]

                https_password = https_proxy[2].split("@")[0]
                https_password = requests.utils.unquote(https_password)
                _base64_bytes = https_password.encode("ascii")
                _enc_bytes = base64.b64encode(_base64_bytes)
                https_password = _enc_bytes.decode("ascii")
            else:
                https_user = ""
                https_password = ""
                https_url = https_proxy_

            proxy_details["http_url"] = http_url
            proxy_details["http_user"] = http_user
            proxy_details["http_password"] = http_password
            proxy_details["https_url"] = https_url
            proxy_details["https_user"] = https_user
            proxy_details["https_password"] = https_password

            return proxy_details, "Obtained proxy details successfully"

        except Exception:
            return (
                None,
                "Proxy url must be in the format http://<Proxy_User>:<URI_EncodedProxy_Password>@<Proxy_IP>:"
                "<Proxy_Port> or http://<Proxy_IP>:<Proxy_Port>",
            )

    def register_tanzu_observability(self, cluster_name, size):
        """
        Integrate workload cluster with Tanzu Observability
        :param cluster_name: workload cluster name
        :param size: cluster size fetched from deployment json file
        :return: 200 if successful else, 500
        """
        try:
            if self.check_to_enabled():
                if self.env != Env.VMC and TkgsUtil.is_env_tkgs_ns(self.spec, self.env):
                    if int(size) < 3:
                        return (
                            "Minimum required number of worker nodes to SaaS integrations "
                            "is 3 and recommended size is medium and above",
                            500,
                        )
                else:
                    if size.lower() == "medium" or size.lower() == "small":
                        current_app.logger.debug(
                            "Recommended to use large/extra-large for Tanzu Observability integration"
                        )
                st = self.integrate_saas(cluster_name, SAS.TO)
                return st[0], st[1]
            else:
                return "Tanzu observability is deactivated", 200
        except Exception as e:
            return "Failed to register tanzu Observability " + str(e), 500

    def generate_to_json_file(self, management_cluster, provisioner_name, to_url, to_secrets):
        """
        Create JSON file to_json.json for TO integration
        :param management_cluster: management cluster name
        :param provisioner_name: provisioner name
        :param cluster_name: workload cluster name
        :param to_url: TO URL
        :param to_secrets: TO secrets
        :return: Nonw
        """
        to_json = TmcPayloads.TO_PAYLOAD.format(
            provisioner_name=provisioner_name,
            management_cluster=management_cluster,
            to_url=to_url,
            to_secrets=to_secrets,
        )
        return to_json

    def check_to_enabled(self):
        """
        Check if TO integration in enabled in input JSON file
        :return: True if enabled else, False
        """
        try:
            to = False
            if self.env == Env.VMC:
                to = self.spec.saasEndpoints.tanzuObservabilityDetails.tanzuObservabilityAvailability
            elif self.env == Env.VSPHERE or self.env == Env.VCF:
                to = self.spec.envSpec.saasEndpoints.tanzuObservabilityDetails.tanzuObservabilityAvailability
            if str(to).lower() == "true":
                return True
            else:
                return False
        except Exception:
            return False

    def validate_cluster_size_for_to_and_tsm(self):
        """
        validate the cluster provided in input json file is compatible for Tanzu Observability
        and Tanzu Service Mesh integration
        :return: 200 if valid, else 500
        """
        current_app.logger.info(
            "Recommend to use Tanzu Observability and Tanzu Service "
            "Mesh integration with cluster size large or extra-large"
        )
        is_to = self.check_to_enabled()
        is_tsm = self.check_tsm_enabled()
        if is_to or is_tsm:
            if not self.check_tmc_enabled():
                return "TMC is not enabled, for SaaS integration TMC must be enabled", 500
            if self.env == Env.VMC:
                size = str(self.spec.componentSpec.tkgWorkloadSpec.tkgWorkloadSize)
            elif self.env == Env.VSPHERE or self.env == Env.VCF:
                size = str(self.spec.tkgWorkloadComponents.tkgWorkloadSize)
            if size.lower() == "medium" or size.lower() == "small":
                return "Recommend to use TO and TSM integration with cluster size large or extra-large", 500
            return "Cluster size verified", 200
        else:
            if is_to:
                msg_text = "Tanzu Observability integration is activated"
            elif is_tsm:
                msg_text = "Tanzu Service Mesh integration is activated"
            else:
                msg_text = "Both Tanzu Service Mesh and Tanzu Observability integration is deactivated"
            return msg_text, 200

    def check_tmc_enabled(self):
        """
        Check if TMC/SaaS integration is enabled input JSON
        :return: True is enabled, else False
        """
        if self.tmc_availability == "true":
            return True
        else:
            return False

    def register_tsm(self, cluster_name, size):
        """
        Register workload Cluster with Tanzu Service Mesh
        :param cluster_name: workload cluster name
        :param size: size of workload cluster
        :return: 200 if successfully integrated else, False
        """
        try:
            if self.check_tsm_enabled():
                if self.env != Env.VMC and TkgsUtil.is_env_tkgs_ns(self.spec, self.env):
                    if int(size) < 3:
                        return (
                            "Minimum required number of worker nodes to SaaS integrations is "
                            "3 and recommended size is medium and above",
                            500,
                        )
                else:
                    if size.lower() == "medium" or size.lower() == "small":
                        current_app.logger.debug(
                            "Recommended to use large/extra-large for Tanzu service mesh " "integration"
                        )
                st = self.integrate_saas(cluster_name, SAS.TSM)
                return st[0], st[1]
            else:
                return "Tanzu Service Mesh is deactivated", 200
        except Exception as e:
            return "Failed to register Tanzu Service Mesh " + str(e), 500

    def integrate_saas(self, cluster_name, ssas_type):
        """
        Perform TO and TSM integrations
        :param cluster_name: workload cluster name
        :param ssas_type: to or tsm SaaS type
        :return: 200 if successfully integrated else, False
        """
        if self.env != Env.VMC and TkgsUtil.is_env_tkgs_ns(self.spec, self.env):
            cluster = self.spec.envSpec.vcenterDetails.vcenterCluster
            cluster_status = self.tkgs_util.is_cluster_running(cluster, cluster_name)
            if cluster_status[1] != 200:
                return cluster_status[0], cluster_status[1]

            get_cluster_url = TmcConstants.LIST_TMC_MGMT_CLUSTERS.format(tmc_url=self.tmc_url)
            response = RequestApiUtil.exec_req("GET", get_cluster_url, headers=self.tmc_header, data={}, verify=False)
            if RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                res_json = response.json()
                for mgmt_clstrs in res_json["managementClusters"]:
                    if cluster == mgmt_clstrs["fullName"]["name"]:
                        return "Tanzu " + ssas_type + " registration is not supported on management cluster", 500
            else:
                return "Failed to fetch management cluster list", 500

            context = self.tkgs_util.connect_to_workload(cluster, cluster_name)
            if context[0] is None:
                return context[1], 500
        else:
            context = TanzuUtil().switch_to_context(cluster_name)
            if context[1] != 200:
                return context[0].json["msg"], context[1]
        cluster_details = SaaSUtil.return_list_of_tmc_clusters(self.tmc_url, self.tmc_refresh_token, cluster_name)
        if not self.is_saas_registered(cluster_name, cluster_details[1], cluster_details[2], False, ssas_type):
            current_app.logger.info("Registering to tanzu " + ssas_type)
            if not self.check_tmc_enabled():
                return "TMC is not enabled, tmc must be enabled to register tanzu " + ssas_type, 500
            verify_cluster = True if self.env == Env.VMC or not TkgsUtil.is_env_tkgs_ns(self.spec, self.env) else False
            if verify_cluster:
                if not TanzuUtil.verify_cluster(cluster_name):
                    return (
                        cluster_name + " is not registered to TMC, cluster must be "
                        "registered to TMC first to register tanzu " + ssas_type,
                        500,
                    )
                if TanzuUtil.get_management_cluster() == cluster_name:
                    return "Tanzu " + ssas_type + " registration is not supported on management cluster", 500

            if ssas_type == SAS.TO:
                integrate_payload = self.generate_to_json_file(
                    cluster_details[1], cluster_details[2], self.to_url, self.to_token
                )
            elif ssas_type == SAS.TSM:
                exact, partial = self.get_tsm_details()
                integrate_payload = self.generate_tsm_json_file(cluster_details[1], cluster_details[2], exact, partial)
            integrate_saas_url = TmcConstants.INTEGRATE_SAAS.format(tmc_url=self.tmc_url, cluster_name=cluster_name)
            response = RequestApiUtil.exec_req(
                "POST", integrate_saas_url, headers=self.tmc_header, data=integrate_payload, verify=False
            )
            if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                current_app.logger.debug(response.text)
                return "Failed to obtain Intergation status for TMC", 500
            if ssas_type == SAS.TO:
                pods = TmcConstants.TO_PODS
                command_kube = KubectlCommands.LIST_PODS.format(namespace=TmcConstants.TO_NAMESPACE)
            elif ssas_type == SAS.TSM:
                pods = TmcConstants.TSM_PODS
                command_kube = KubectlCommands.LIST_PODS.format(namespace=TmcConstants.TSM_NAMESPACE)
            for pod in pods:
                st = waitForProcessWithStatus(command_kube, pod, RegexPattern.RUNNING)
                if st[1] != 200:
                    return st[0].json["msg"], st[1]
            count = 0
            registered = False
            while count < 180:
                if self.is_saas_registered(cluster_name, cluster_details[1], cluster_details[2], False, ssas_type):
                    registered = True
                    break
                time.sleep(10)
                count = count + 1
                current_app.logger.info("waited for " + str(count * 10) + "s for registration to complete... retrying")
            if not registered:
                return "Failed to register tanzu " + ssas_type + " to " + cluster_name, 500
            return "Tanzu " + ssas_type + " is integrated successfully to cluster " + cluster_name, 200
        else:
            return "Tanzu " + ssas_type + " is already registered to " + cluster_name, 200

    def get_tsm_details(self):
        """
        Fetch TSM namespace exclusion details from deployment JSON file
        :return: exact and partial namespace exclusion strings
        """
        if self.env == Env.VMC:
            exact = self.spec.componentSpec.tkgWorkloadSpec.namespaceExclusions.exactName
            partial = self.spec.componentSpec.tkgWorkloadSpec.namespaceExclusions.startsWith
        elif self.env == Env.VSPHERE or self.env == Env.VCF:
            if TkgsUtil.is_env_tkgs_ns(self.spec, self.env):
                exact = (
                    self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.namespaceExclusions.exactName
                )
                partial = (
                    self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.namespaceExclusions.startsWith
                )
            else:
                exact = self.spec.tkgWorkloadComponents.namespaceExclusions.exactName
                partial = self.spec.tkgWorkloadComponents.namespaceExclusions.startsWith
        return exact, partial

    def generate_tsm_json_file(self, management_cluster, provisioner_name, exact, partial):
        """
        Generate tsm_json.json file for TSM integration
        :param management_cluster: management cluster name
        :param provisioner_name: provisioner name
        :param cluster_name: workload cluster name
        :param exact: exact string of namespace exclusion
        :param partial: partial string of namespace exclusion
        :return: None
        """
        tsm_json = TmcPayloads.TSM_PAYLOAD.format(
            provisioner_name=provisioner_name, management_cluster=management_cluster
        )
        if not (exact and partial):
            configurations = {"enableNamespaceExclusions": False}
        else:
            configurations = {"enableNamespaceExclusions": True}
            configurations.update({"namespaceExclusions": []})
            if exact:
                configurations["namespaceExclusions"].append({"match": exact, "type": "EXACT"})
            if partial:
                configurations["namespaceExclusions"].append({"match": partial, "type": "START_WITH"})
        tsm_json = json.loads(tsm_json)
        tsm_json["integration"]["spec"]["configurations"] = configurations
        tsm_json = json.dumps(tsm_json)
        return tsm_json

    def is_saas_registered(self, cluster_name, management, provisioner, pr, saas_type):
        """
        validate is TSM or TO is already integrated with provided workload cluster
        :param cluster_name: workload cluster name
        :param management: management cluster name
        :param provisioner: provisioner name
        :param pr: True or False
        :param saas_type: TSM or TO
        :return: True if already integrated else, False
        """
        try:
            saas = TmcConstants.TO if saas_type == SAS.TO else TmcConstants.TSM
            get_saas_url = TmcConstants.GET_SAAS_INTEGRATE_STATUS.format(
                tmc_url=self.tmc_url,
                cluster_name=cluster_name,
                saas_type=saas,
                management_cluster=management,
                provisioner=provisioner,
            )
            response = RequestApiUtil.exec_req("GET", get_saas_url, headers=self.tmc_header, data={}, verify=False)
            if RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                if pr:
                    current_app.logger.error(response[0])
                    return False
                load_result = response.json()["integration"]
                if load_result["fullName"]["name"] == saas:
                    integration = load_result["status"]["integrationWorkload"]
                    if integration != "OK":
                        current_app.logger.info("integrationWorkload status " + integration)
                        return False
                    else:
                        current_app.logger.info("integrationWorkload status " + integration)
                    tmcAdapter = load_result["status"]["tmcAdapter"]
                    if tmcAdapter != "OK":
                        current_app.logger.info("tmcAdapter status " + tmcAdapter)
                        return False
                    else:
                        current_app.logger.info("tmcAdapter status " + tmcAdapter)
                    return True
                return False
            else:
                current_app.logger.info(saas + " is not integrated")
                return False
        except Exception as e:
            if pr:
                current_app.logger.error(str(e))
                return False

    def check_tsm_enabled(self):
        """
        Check if TSM is enabled for activation in input JSON file
        :return: True if enabled else False
        """
        try:
            if self.env == Env.VMC:
                is_tsm = str(self.spec.componentSpec.tkgWorkloadSpec.tkgWorkloadTsmIntegration)
            elif self.env == Env.VSPHERE or self.env == Env.VCF:
                if TkgsUtil.is_env_tkgs_ns(self.spec, self.env):
                    is_tsm = str(
                        self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgWorkloadTsmIntegration
                    )
                else:
                    is_tsm = str(self.spec.tkgWorkloadComponents.tkgWorkloadTsmIntegration)
            if is_tsm.lower() == "true":
                return True
            else:
                return False
        except Exception:
            return False

    def validate_node_count_for_tsm(self):
        """
        Validate is node count provided in input json matches the TSM and TO requirement
        :return: True if correct number of node count provided else, False
        """
        if self.check_tsm_enabled():
            try:
                if self.env == Env.VMC:
                    machine_count_workload = self.spec.componentSpec.tkgWorkloadSpec.tkgWorkloadWorkerMachineCount
                elif self.env == Env.VSPHERE or self.env == Env.VCF:
                    machine_count_workload = self.spec.tkgWorkloadComponents.tkgWorkloadWorkerMachineCount
                if int(machine_count_workload) < 3:
                    return (
                        "Tanzu Service Mesh integration is not supported "
                        "for machine count less then 3  for workload cluster",
                        500,
                    )
            except Exception as e:
                return "Not found key " + str(e), 500
            return "Tanzu Service Mesh cluster size verified", 200
        else:
            return "Tanzu Service Mesh integration is deactivated", 200

    def register_tmc_tkgs(self, vcenter, vcenter_username, vcenter_password):
        """
        Register supervisor cluster to TMC
        :param vcenter: vCenter IP or FQDN
        :param vcenter_username: vCenter username
        :param vcenter_password: vCenter password
        :return: HTTPStatus.OK on success else HTTPStatus.INTERNAL_SERVER_ERROR
        """
        if self.tkgs_util.check_tkgs_proxy_enabled():
            http_proxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.httpProxy
            https_proxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.httpsProxy
            no_proxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.noProxy
            mgmt = self.spec.envSpec.saasEndpoints.tmcDetails.tmcSupervisorClusterName
            proxy_credential_name = TmcConstants.TMC_PROXY_NAME.format(cluster_name=mgmt)
            status, message = self.create_tmc_proxy_credential(http_proxy, https_proxy, no_proxy, proxy_credential_name)
            if status is None:
                return None, message

            status, message = self.register_supervisor_cluster_tmc(
                mgmt, vcenter, vcenter_username, vcenter_password, True
            )
            if status is None:
                return None, message
            else:
                return message, HTTPStatus.OK
        else:
            try:
                vc_operation: VCEndpointOperations = VCEndpointOperations(vcenter, vcenter_username, vcenter_password)
                sess, status_code = vc_operation.get_session()
                if status_code != HTTPStatus.OK:
                    return sess, status_code
                header = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "vmware-api-session-id": sess,
                }
                cluster_name = self.spec.envSpec.vcenterDetails.vcenterCluster
                mgmt = self.spec.envSpec.saasEndpoints.tmcDetails.tmcSupervisorClusterName
                cluster_endpoint = self.tkgs_util.get_cluster_endpoint(cluster_name, header)

                configure_kubectl = self.kubectl_util.configure_kubectl(cluster_endpoint)
                if configure_kubectl[1] != HTTPStatus.OK:
                    return configure_kubectl[0], HTTPStatus.INTERNAL_SERVER_ERROR

                supervisor_tmc = self.tkgs_util.supervisor_tmc(cluster_endpoint)
                if supervisor_tmc[1] != HTTPStatus.OK:
                    return supervisor_tmc[0], HTTPStatus.INTERNAL_SERVER_ERROR

                supervisor_cluster = self.spec.envSpec.saasEndpoints.tmcDetails.tmcSupervisorClusterName
                if self.check_tmc_Register(supervisor_cluster, True):
                    current_app.logger.info(supervisor_cluster + " is already registered")
                else:
                    cluster_group = self.spec.envSpec.saasEndpoints.tmcDetails.tmcSupervisorClusterGroupName
                    if not cluster_group:
                        cluster_group = "default"
                    status, message = self.register_supervisor_cluster_tmc(
                        mgmt, vcenter, vcenter_username, vcenter_password, False
                    )
                    if status is None:
                        return None, message
                    current_app.logger.info("Waiting for TMC registration to complete... ")
                    time.sleep(300)
                    wait_status = self.wait_for_supervisor_tmc_registration(supervisor_cluster)
                    if wait_status[1] != HTTPStatus.OK:
                        current_app.logger.error(wait_status[0])
                        return wait_status[0], HTTPStatus.INTERNAL_SERVER_ERROR
                return "TMC Register Successful", HTTPStatus.OK

            except Exception as e:
                current_app.logger.error(e)
        response = RequestApiUtil.create_json_object(
            "Failed to Register Supervisor Cluster to TMC", "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
        )
        return response, HTTPStatus.INTERNAL_SERVER_ERROR

    def create_tkgs_workload_cluster_on_tmc(self, cluster_name, cluster_version):
        """
        Create TKGs workload cluster on TMC
        :param cluster_version: Cluster version
        :param cluster_name: workload network name
        :return: None if failure, else success
        """
        current_app.logger.info("Creating TKGs workload cluster on TMC...")

        supervisor_cluster = self.spec.envSpec.saasEndpoints.tmcDetails.tmcSupervisorClusterName
        name_space = (
            self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereNamespaceName
        )

        registration_payload = self.get_tmc_payload_tkgs_workload_cluster(
            supervisor_cluster, name_space, cluster_name, cluster_version
        )
        if registration_payload[0] is None:
            return None, registration_payload[1]

        create_url = TmcConstants.CREATE_TKGS_WORKLOAD_CLUSTER.format(tmc_url=self.tmc_url)
        modified_payload = json.dumps(registration_payload[0], ensure_ascii=True, sort_keys=True, indent=4)
        response = RequestApiUtil.exec_req(
            "POST", create_url, headers=self.tmc_header, data=modified_payload, verify=False
        )
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            current_app.logger.error("Failed to run command to create workload cluster " + str(response.text))
            return False, "Failed to run command to create workload cluster " + str(response.text)
        current_app.logger.info("Waiting for 2 mins for checking status == ready")
        time.sleep(120)
        get_workload_url = TmcConstants.GET_WORKLOAD_CLUSTER_STATUS.format(
            tmc_url=self.tmc_url,
            cluster_name=cluster_name,
            management_cluster=supervisor_cluster,
            provisioner=name_space,
        )
        count = 0
        found = False
        while count < 135:
            response = RequestApiUtil.exec_req("GET", get_workload_url, headers=self.tmc_header, data={}, verify=False)
            if RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                try:
                    json_ = response.json()
                    phase = json_["cluster"]["status"]["phase"]
                    health = json_["cluster"]["status"]["health"]
                    wcm_status = json_["cluster"]["status"]["conditions"]["WCM-Ready"]["status"]
                    if phase == "READY" and health == "HEALTHY" and wcm_status == "TRUE":
                        found = True
                        current_app.logger.info(
                            "Phase status " + phase + " wcm status " + wcm_status + " Health status " + health
                        )
                        break
                    current_app.logger.info(
                        "Phase status " + phase + " wcm status " + wcm_status + " Health status " + health
                    )
                except Exception:
                    pass
            time.sleep(20)
            current_app.logger.info("Waited for " + str(count * 20) + "s, retrying")
            count = count + 1
        if not found:
            return None, "Cluster not in ready state"
        return "SUCCESS", "Cluster created successfully on TMC"

    def get_tmc_payload_tkgs_workload_cluster(self, supervisor_cluster, name_space, workload_name, version):
        """
        Build TMC command for creating TKGs Workload cluster
        :param supervisor_cluster: supervisor cluster name on TMC
        :param name_space: Namespace name
        :param workload_name: workload cluster name to be created
        :param version: Workload cluster version
        :return: None on Failure, else command
        """
        pod_cidr = self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.podCidrBlocks
        service_cidr = (
            self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.serviceCidrBlocks
        )
        worker_node_count = (
            self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.workerNodeCount
        )
        enable_ha = (
            self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.enableControlPlaneHa
        )
        cluster_group = (
            self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsWorkloadClusterGroupName
        )
        worker_vm_class = (
            self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.workerVmClass
        )
        control_plane_vm_class = (
            self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.controlPlaneVmClass
        )
        node_storage_class_input = (
            self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.nodeStorageClass
        )
        default_storage_class = (
            self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.defaultStorageClass
        )

        default_class = self.tkgs_util.get_storage_alias_details(default_storage_class)
        if default_class[0] is None:
            return None, default_class[1]

        default_class = default_class[0]

        node_storage_class = self.tkgs_util.get_storage_alias_details(node_storage_class_input)
        if node_storage_class[0] is None:
            return None, node_storage_class[1]
        node_storage_class = node_storage_class[0]

        if not cluster_group:
            cluster_group = "default"

        allowed_storage = (
            self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.allowedStorageClasses
        )
        allowed = ""
        classes = allowed_storage

        for c in classes:
            allowed_ = self.tkgs_util.get_storage_alias_details(c)
            if allowed_[0] is None:
                return None, allowed_[1]
            allowed += str(allowed_[0]) + ","
        if not allowed:
            current_app.logger.error("Failed to get allowed classes")
            return None, "Failed to get allowed classes"
        high_availability = False
        if str(enable_ha).lower() == "true":
            high_availability = True
        proxy_credential_name = ""
        if self.tkgs_util.check_tkgs_proxy_enabled():
            http_proxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.httpProxy
            https_proxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.httpsProxy
            no_proxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.noProxy
            proxy_credential_name = TmcConstants.TMC_PROXY_NAME.format(cluster_name=workload_name)
            proxy_cred_response = self.create_tmc_proxy_credential(
                http_proxy, https_proxy, no_proxy, proxy_credential_name
            )
            if proxy_cred_response[0] is None:
                return None, proxy_cred_response[1]
        allowed = allowed.strip(",")
        control_plane_volume_payload = ""
        worker_volume_payload = ""
        try:
            control_plane_volumes = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.controlPlaneVolumes
            )
            control_plane_volumes_list = []
            for control_plane_volume in control_plane_volumes:
                if control_plane_volume["storageClass"]:
                    storageClass = control_plane_volume["storageClass"]
                else:
                    storageClass = default_class
                control_plane_volumes_list.append(
                    {
                        "name": control_plane_volume["name"],
                        "storageClass": storageClass,
                        "mountPath": control_plane_volume["mountPath"],
                        "capacity": control_plane_volume["storage"],
                    }
                )
                control_plane_volume_payload = {"name": "controlPlaneVolumes", "value": control_plane_volumes_list}
        except Exception:
            control_plane_volume_payload = ""
        try:
            worker_volumes = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.workerVolumes
            )
            worker_volumes_list = []
            for worker_volume in worker_volumes:
                if worker_volume["storageClass"]:
                    storageClass = worker_volume["storageClass"]
                else:
                    storageClass = default_class
                worker_volumes_list.append(
                    {
                        "name": worker_volume["name"],
                        "storageClass": storageClass,
                        "mountPath": worker_volume["mountPath"],
                        "capacity": worker_volume["storage"],
                    }
                )
                worker_volume_payload = {"name": "nodePoolVolumes", "value": worker_volumes_list}
        except Exception:
            worker_volume_payload = ""

        """
        Creating tmc tkgs workload payload
        """
        register_payload = self.tkgs_payload_tmc_cluster_creation(
            supervisor_cluster_name=supervisor_cluster,
            name_space=name_space,
            cluster_name=workload_name,
            cluster_group=cluster_group,
            pod_cidr=pod_cidr,
            service_cidr=service_cidr,
            version=version,
            node_storage_class=node_storage_class,
            allowed_storage_class=allowed,
            default_storage_class=default_class,
            worker_vm_class=worker_vm_class,
            control_plane_vm_class=control_plane_vm_class,
            worker_node_count=worker_node_count,
            proxy_name=proxy_credential_name,
            high_availability=high_availability,
            control_plane_volume_payload=control_plane_volume_payload,
            worker_volume_payload=worker_volume_payload,
        )
        return register_payload, "TMC payload created successfully"

    def create_tkgm_workload_cluster_on_tmc(self, register_payload, management_cluster, provisioner):
        """
        Create TKGm Workload Cluster on TMC
        :param register_payload: TMC payload to create workload cluster
        :param management_cluster: Management Cluster name
        :param provisioner: Provisioner name
        :return: True if created else False
        """
        current_app.logger.info("Deploying workload cluster on tmc...")
        create_url = TmcConstants.CREATE_TKGM_WORKLOAD_CLUSTER.format(
            tmc_url=self.tmc_url, management_cluster=management_cluster, provisioner=provisioner
        )
        modified_payload = json.dumps(register_payload, ensure_ascii=True, sort_keys=True, indent=4)
        response = RequestApiUtil.exec_req(
            "POST", create_url, headers=SaaSUtil.tmc_header, data=modified_payload, verify=False
        )
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            current_app.logger.error("Failed to run command to create workload cluster " + str(response.text))
            return False, "Failed to run command to create workload cluster " + str(response.text)
        # checking cluster state on TMC with a loop for 2700 seconds
        json_object = json.loads(modified_payload)
        cluster_name = json_object["tanzuKubernetesCluster"]["fullName"]["name"]
        counter = 0
        while counter < 135:
            if (
                SaaSUtil.check_cluster_state_on_tmc(self.tmc_url, self.tmc_refresh_token, cluster_name, False)[0]
                == "SUCCESS"
            ):
                break
            current_app.logger.info(f"waited {counter * 20} secs for cluster on TMC to comes in ready state")
            time.sleep(20)
            counter += 1
        else:
            return False, "Cluster on TMC is not in healthy state " + cluster_name
        return True, "Successfully created cluster on TMC"

    def list_tmc_clusters(self, is_mgmt):
        """
        List Workload Cluster on TMC
        :return: True if list fetched successfully else False
        """
        cluster_list = []
        if is_mgmt:
            json_path = TmcConstants.MGMT_CLUSTERS
            get_cluster_url = TmcConstants.LIST_TMC_MGMT_CLUSTERS.format(tmc_url=self.tmc_url)
        else:
            json_path = TmcConstants.CLUSTERS
            get_cluster_url = TmcConstants.LIST_TMC_CLUSTERS.format(tmc_url=self.tmc_url)
        response = RequestApiUtil.exec_req("GET", get_cluster_url, headers=SaaSUtil.tmc_header, data={}, verify=False)
        time.sleep(10)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            current_app.logger.error("Failed to run command to check list workload clusters")
            return False, []
        cluster_list = response.json()[json_path]
        return True, cluster_list

    def delete_tmc_cluster(self, cluster_name, is_mgmt, management_cluster=None, provisioner=None):
        cluster_url = TmcConstants.FETCH_TMC_MGMT_CLUSTER.format(tmc_url=self.tmc_url, management_cluster=cluster_name)
        if not is_mgmt:
            cluster_url = TmcConstants.DELETE_TKGM_WORKLOAD_CLUSTER.format(
                tmc_url=self.tmc_url,
                management_cluster=management_cluster,
                provisioner=provisioner,
                cluster=cluster_name,
            )
        cluster_url = cluster_url + "?force=true"
        response = RequestApiUtil.exec_req("DELETE", cluster_url, headers=SaaSUtil.tmc_header, data={}, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            current_app.logger.error("Failed to un-register cluster - " + cluster_name + " from TMC")
            return False
        current_app.logger.info(cluster_name + " un-registered from TMC successfully")
        return True
