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
from yaml import SafeLoader

from common.common_utilities import waitForProcessWithStatus
from common.constants.constants import KubectlCommands
from common.constants.tmc_api_constants import TmcCommands, TmcConstants, TmcPayloads
from common.lib.govc.govc_client import GOVClient
from common.lib.vcenter.vcenter_endpoints_operations import VCEndpointOperations
from common.operation.constants import SAS, Env, Paths, RegexPattern, Tkgs_Extension_Details, TmcUser
from common.operation.ShellHelper import (
    grabPipeOutput,
    runProcess,
    runProcessTmcMgmt,
    runShellCommandAndReturnOutput,
    runShellCommandAndReturnOutputAsList,
)
from common.session.session_acquire import login
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

        login()

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
            if not self.tkgs_util.is_env_tkgs_wcp(self.env):
                self.to_url = self.spec.envSpec.saasEndpoints.tanzuObservabilityDetails.tanzuObservabilityUrl
                self.to_token = self.spec.envSpec.saasEndpoints.tanzuObservabilityDetails.tanzuObservabilityRefreshToken

        SaaSUtil.tmc_header = self.fetch_tmc_header()

    def fetch_tmc_header(self):
        """
        Create TMC header by fecthing access token from TMC
        :return: header dictionary
        """
        if self.check_tmc_enabled():
            login_response = RequestApiUtil.exec_req(
                "POST",
                TmcConstants.TMC_LOGIN_API.format(refresh_token=self.tmc_refresh_token),
                headers={},
                data={},
                verify=False,
            )

            if not RequestApiUtil.verify_resp(login_response, status_code=HTTPStatus.OK):
                raise Exception(f"Error while logging into TMC using provided refresh token: {login_response.text}")

            access_token = login_response.json()["access_token"]

            header = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": access_token,
            }
            return header
        else:
            return {}

    def register_management_cluster_tmc(self, management_cluster, is_proxy, type, cluster_group):
        if not SaaSUtil.check_tmc_Register(management_cluster, True):
            proxy_cred_state = self.create_proxy_credentials_tmc(
                cluster_name=management_cluster, is_proxy=is_proxy, type=type, register=True
            )
            if proxy_cred_state[1] != 200:
                return str(proxy_cred_state[0]), 500
            proxy_name = TmcConstants.TMC_PROXY_NAME.format(cluster_name=management_cluster)

            if str(is_proxy).lower() == "true":
                current_app.logger.info("Registering to TMC with proxy")
                register_command = TmcCommands.REGISTER_TMC_PROXY_MGMT.format(
                    management_cluster=management_cluster,
                    cluster_group=cluster_group,
                    proxy_name=proxy_name,
                    kubeconfig_yaml="kubeconfig.yaml",
                )
            else:
                current_app.logger.info("Registering to TMC")
                register_command = TmcCommands.REGISTER_TMC_MGMT.format(
                    management_cluster=management_cluster,
                    cluster_group=cluster_group,
                    kubeconfig_yaml="kubeconfig.yaml",
                )

            register_output = runProcessTmcMgmt(register_command)
            if register_output == "FAIL":
                current_app.logger.error("Failed to register Management Cluster with TMC")
                current_app.logger.info(
                    "Continuing registration to apply the Tanzu Mission "
                    "Control resource manifest to complete registration"
                )
                register_command.concat("--continue-bootstrap")
                runProcess(register_command)

            current_app.logger.info("Registered to TMC")
            current_app.logger.info("Waiting for 5 min for health status = ready…")
            for i in tqdm(range(300), desc="Waiting for health status…", ascii=False, ncols=75):
                time.sleep(1)
            state = SaaSUtil.check_cluster_state_on_tmc(management_cluster, True)
            if state[0] == "SUCCESS":
                current_app.logger.info("Registered to TMC successfully")
                return "SUCCESS", 200
            else:
                return None, state[1]
        else:
            current_app.logger.info("Management cluster is already registered with TMC")
            return "SUCCESS", 200

    @staticmethod
    def check_tmc_Register(cluster, is_management):
        try:
            list_command = TmcCommands.LIST_TMC_CLUSTERS_MGMT if is_management else TmcCommands.LIST_TMC_CLUSTERS
            o = runShellCommandAndReturnOutput(list_command)
            if cluster in o[0]:
                state = SaaSUtil.check_cluster_state_on_tmc(cluster, is_management)
                if state[0] == "SUCCESS":
                    return True
                else:
                    return False
            else:
                return False
        except Exception:
            return False

    @staticmethod
    def return_list_of_tmc_clusters(cluster):
        output = runShellCommandAndReturnOutputAsList(TmcCommands.LIST_TMC_CLUSTERS)
        cluster_list = []
        for s_ in output[0]:
            if cluster in str(s_):
                for list1 in s_.split(" "):
                    if list1:
                        cluster_list.append(list1)
        return cluster_list

    @staticmethod
    def check_cluster_state_on_tmc(cluster, is_management):
        try:
            if is_management:
                get_status_command = TmcCommands.GET_CLUSTER_STATUS_MGMT.format(mgmt_cluster=cluster)
            else:
                cluster_details = SaaSUtil.return_list_of_tmc_clusters(cluster)
                get_status_command = TmcCommands.GET_CLUSTER_STATUS.format(
                    cluster=cluster_details[0], mgmt_cluster=cluster_details[1], provisioner=cluster_details[2]
                )
            o = runShellCommandAndReturnOutput(get_status_command)
            if o[1] == 0:
                load_result = yaml.safe_load(o[0])
                try:
                    status = str(load_result["status"]["conditions"]["Agent-READY"]["status"])
                except Exception:
                    status = str(load_result["status"]["conditions"]["READY"]["status"])
                try:
                    type = str(load_result["status"]["conditions"]["Agent-READY"]["type"])
                except Exception:
                    type = str(load_result["status"]["conditions"]["READY"]["type"])
                health = str(load_result["status"]["health"])
                if status == "TRUE":
                    current_app.logger.info("Management cluster status " + status)
                else:
                    current_app.logger.error("Management cluster status " + status)
                    return "Failed", 500
                if type == "READY":
                    current_app.logger.info("Management cluster type " + type)
                else:
                    current_app.logger.error("Management cluster type " + type)
                    return "Failed", 500
                if health == "HEALTHY":
                    current_app.logger.info("Management cluster health " + health)
                else:
                    current_app.logger.error("Management cluster health " + health)
                    return "Failed", 500
                return "SUCCESS", 200
            else:
                return None, o[0]
        except Exception as e:
            return None, str(e)

    def create_proxy_credentials_tmc(self, cluster_name, is_proxy, type, register=True):
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
            os.putenv("TMC_API_TOKEN", self.tmc_refresh_token)
            user = TmcUser.USER if self.env == Env.VMC else TmcUser.USER_VSPHERE
            tmc_login = TmcCommands.TMC_LOGIN.format(user=user)
            runProcess(tmc_login)
            """
            Obtain kube config for the cluster
            """
            if register and type != "management":
                current_app.logger.info("Fetching Kube config for workload cluster " + cluster_name)
                tmc_command = TmcCommands.GET_KUBE_CONFIG.format(cluster_name=cluster_name, file=file)
                runProcess(tmc_command)
                current_app.logger.info("Fetched kubeconfig successfully")

            """
            If Proxy is set to true, fetch proxy details and parse the strings
            """
            if str(is_proxy).lower() == "true":
                current_app.logger.info("Creating TMC Proxy credentials...")
                name = TmcConstants.TMC_PROXY_NAME.format(cluster_name=cluster_name)

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

                no_proxy = no_proxy.strip("\n").strip(" ").strip("\r")

                proxy_info = self.parse_proxy_strings(http_proxy, https_proxy)
                if proxy_info[0] is None:
                    return proxy_info[1], 500

                proxy_info = proxy_info[0]

                self.generate_tmc_proxy_yaml(
                    name,
                    proxy_info["http_url"],
                    proxy_info["https_url"],
                    no_proxy,
                    proxy_info["http_user"],
                    proxy_info["http_password"],
                    proxy_info["https_user"],
                    proxy_info["https_password"],
                )
                """
                Create proxy credentials using TMC API
                """
                credential = TmcCommands.CREATE_TMC_CREDENTIAL.format(tmc_proxy_yaml=TmcConstants.PROXY_YAML)
                state_cred = runShellCommandAndReturnOutput(credential)
                if state_cred[1] != 0:
                    if "AlreadyExists" in str(state_cred[0]):
                        current_app.logger.info("TMC credential " + name + " is already created")
                    else:
                        current_app.logger.error("Failed to run create credential" + str(state_cred[0]))
                        return "Failed to run create credential " + str(state_cred[0]), 500
                current_app.logger.info("Successfully created credentials for TMC Proxy")
                return name, 200
            current_app.logger.info("Proxy credential configuration not required")
            return "Proxy credential configuration not required", 200
        except Exception as e:
            return "Proxy credential creation on TMC failed for cluster " + cluster_name + " " + str(e), 500

    def register_workload_cluster_tmc(self, cluster_name, is_proxy, type):
        """
        Register cluster to TMC using TMC CLI
        :param cluster_name: name of cluster to be registered
        :param is_proxy: True if proxy is set else, False
        :param type: cluster type - workload, shared or management
        :return: 200 on Success else, 500
        """
        try:
            if not SaaSUtil.check_tmc_Register(cluster_name, False):
                file = TmcConstants.WORKLOAD_KUBE_CONFIG_FILE
                proxy_cred_state = self.create_proxy_credentials_tmc(
                    cluster_name=cluster_name, is_proxy=is_proxy, type=type, register=True
                )
                if proxy_cred_state[1] != 200:
                    return proxy_cred_state[0], 500

                name = TmcConstants.TMC_PROXY_NAME.format(cluster_name=cluster_name)

                current_app.logger.info("Attaching cluster to TMC")
                if str(is_proxy).lower() == "true":
                    register_command = TmcCommands.REGISTER_TMC_PROXY.format(
                        cluster_name=cluster_name, file=file, proxy_name=name
                    )
                else:
                    register_command = TmcCommands.REGISTER_TMC.format(cluster_name=cluster_name, file=file)
                try:
                    runProcess(register_command)
                except Exception:
                    return "Failed to attach " + cluster_name + "  to TMC", 500
                return cluster_name + " cluster attached to TMC successfully", 200
            else:
                return cluster_name + " Cluster is already attached to TMC", 200
        except Exception as e:
            return "TMC registration failed on cluster " + cluster_name + " " + str(e), 200

    def generate_tmc_proxy_yaml(
        self,
        proxy_name,
        http_proxy_,
        https_proxy_,
        no_proxy_list_,
        http_username_,
        http_password_,
        https_username_,
        https_password_,
    ):
        """
        Generate YAML file needed for proxy credentials creation
        :param proxy_name: Name of the proxy
        :param http_proxy_: HTTP proxy link
        :param https_proxy_: HTTPs proxy link
        :param no_proxy_list_: No proxy list
        :param http_username_: HTTP proxy username
        :param http_password_: HTTP proxy password
        :param https_username_: HTTPS proxy username
        :param https_password_: HTTPS proxy password
        :return: None
        """
        if http_username_ and http_password_ and https_username_ and https_password_:
            FileHelper.delete_file(TmcConstants.PROXY_YAML)
            data = dict(
                fullName=dict(
                    name=proxy_name,
                ),
                meta=dict(
                    dict(
                        annotations=dict(
                            httpProxy=http_proxy_,
                            httpsProxy=https_proxy_,
                            noProxyList=no_proxy_list_,
                            proxyDescription="tmc_proxy",
                        )
                    )
                ),
                spec=dict(
                    capability="PROXY_CONFIG",
                    data=dict(
                        keyValue=dict(
                            data=dict(
                                httpPassword=http_password_,
                                httpUserName=http_username_,
                                httpsPassword=https_password_,
                                httpsUserName=https_username_,
                            )
                        )
                    ),
                ),
                type=dict(
                    kind="Credential", package="vmware.tanzu.manage.v1alpha1.account.credential", version="v1alpha1"
                ),
            )
        else:
            FileHelper.delete_file(TmcConstants.PROXY_YAML)
            data = dict(
                fullName=dict(
                    name=proxy_name,
                ),
                meta=dict(
                    dict(
                        annotations=dict(
                            httpProxy=http_proxy_,
                            httpsProxy=https_proxy_,
                            noProxyList=no_proxy_list_,
                            proxyDescription="tmc_proxy",
                        )
                    )
                ),
                spec=dict(capability="PROXY_CONFIG", data=dict(keyValue=dict(data=dict()))),
                type=dict(
                    kind="Credential", package="vmware.tanzu.manage.v1alpha1.account.credential", version="v1alpha1"
                ),
            )

        FileHelper.dump_yaml(data, TmcConstants.PROXY_YAML)

    @staticmethod
    def wait_for_supervisor_tmc_registration(super_cls):
        """
        Wait for supervisor cluster TMC registration to complete
        :param super_cls: supervisor cluster name
        :return: 200 if success else, 500
        """
        registered = False
        count = 0
        register_status_command = TmcCommands.GET_CLUSTER_STATUS_MGMT.format(mgmt_cluster=super_cls)
        register_status = runShellCommandAndReturnOutput(register_status_command)
        if register_status[1] != 0:
            return "Failed to obtain register status for TMC", 500
        else:
            try:
                yaml_ouptput = yaml.load(register_status[0], Loader=SafeLoader)
                if (
                    yaml_ouptput["status"]["health"] == "HEALTHY"
                    and yaml_ouptput["status"]["conditions"]["READY"]["status"].lower() == "true"
                ):
                    registered = True
            except KeyError:
                current_app.logger.info("TMC Registration is is still in progress, retrying...")

        while not registered and count < 30:
            register_status = runShellCommandAndReturnOutput(register_status_command)
            if register_status[1] != 0:
                return "Failed to obtain register status for TMC", 500
            else:
                try:
                    yaml_ouptput = yaml.load(register_status[0], Loader=SafeLoader)
                    if (
                        yaml_ouptput["status"]["health"] == "HEALTHY"
                        and yaml_ouptput["status"]["conditions"]["READY"]["status"].lower() == "true"
                    ):
                        registered = True
                        break
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

    def register_supervisor_cluster_tmc(self, management_cluster, vcenter, vcenter_user, vcenter_password):
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
                proxy_name = Tkgs_Extension_Details.TKGS_PROXY_CREDENTIAL_NAME
                cluster_group = self.spec.envSpec.saasEndpoints.tmcDetails.tmcSupervisorClusterGroupName
                if not cluster_group:
                    cluster_group = "default"
                register_payload = TmcPayloads.SUPERVISOR_CLUSTER_REGISTER.format(
                    management_cluster=management_cluster, cluster_group=cluster_group, proxy_name=proxy_name
                )
                management_url = TmcConstants.REGISTER_TMC_MGMT_CLUSTER.format(tmc_url=self.tmc_url)
                import json

                modified_payload = json.dumps(register_payload, indent=4)
                response = RequestApiUtil.exec_req(
                    "POST", management_url, headers=headers, data=modified_payload, verify=False
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
                boots = {"tmc.cloud.vmware.com/bootstrap-token": str(bots_trap_token)}
                main_command = ["kubectl", "get", "ns"]
                sub_command = ["grep", "svc-tmc"]
                command_cert = grabPipeOutput(main_command, sub_command)
                if command_cert[1] != 0:
                    return None, "Failed to get namespace details"
                tmc_namespace = command_cert[0].split("\\s")[0].strip().split()[0]
                data = TmcPayloads.SUPERVISOR_REGISTER_YAML.format(
                    tmc_namespace=tmc_namespace, boots=boots, reg_link=str(reg_link)
                )
                FileHelper.dump_yaml(data, TmcConstants.TKGS_REGISTRAION_FILE)

                current_app.logger.info("Switching context to supervisor cluster")

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
                current_app.logger.info("Applying registration yaml")
                command = KubectlCommands.APPLY_YAML.format(file_name=TmcConstants.TKGS_REGISTRAION_FILE)
                create_output = runShellCommandAndReturnOutputAsList(command)
                if create_output[1] != 0:
                    return None, str(create_output[0])
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
                                "Management cluster state : " + phase + " " + health + " " + message
                            )
                    except Exception:
                        pass
                    time.sleep(30)
                    count = count + 1
                    current_app.logger.info(
                        "Waited for " + str(count * 30) + "s, retrying to check management cluster status on TMC"
                    )
                return None, "Management cluster not registered on waiting " + str(count * 30) + "s"
        except Exception as e:
            return None, str(e)

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
                            "clusterClass": "tkg-vsphere-default-v1.1.0",
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
                            "clusterClass": "tkg-vsphere-default-v1.1.0",
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

    def create_tkgs_proxy_credential(self):
        """
        Create Proxy credentails for TKGs clusters registration
        :return: None if failure else, Success
        """
        is_cred_created = False
        try:
            headers = SaaSUtil.tmc_header
            http_proxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.httpProxy
            https_proxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.httpsProxy
            no_proxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.noProxy
            current_app.logger.info("Getting current proxy credentials")
            """
            Check if roxy credentails are already created
            """
            try:
                url = TmcConstants.FETCH_PROXY_CREDENTIAL.format(
                    tmc_url=self.tmc_url, credential_name=Tkgs_Extension_Details.TKGS_PROXY_CREDENTIAL_NAME
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
                                + Tkgs_Extension_Details.TKGS_PROXY_CREDENTIAL_NAME
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
                    proxy_name=Tkgs_Extension_Details.TKGS_PROXY_CREDENTIAL_NAME,
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
                current_app.logger.info(
                    "Credential " + Tkgs_Extension_Details.TKGS_PROXY_CREDENTIAL_NAME + " already created"
                )
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
                if self.env != Env.VMC and self.tkgs_util.is_env_tkgs_ns(self.env):
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

    def generate_to_json_file(self, management_cluster, provisioner_name, cluster_name, to_url, to_secrets):
        """
        Create JSON file to_json.json for TO integration
        :param management_cluster: management cluster name
        :param provisioner_name: provisioner name
        :param cluster_name: workload cluster name
        :param to_url: TO URL
        :param to_secrets: TO secrets
        :return: Nonw
        """
        file_name = TmcConstants.TO_JSON
        to_json = TmcPayloads.TO_PAYLOAD.format(
            provisioner_name=provisioner_name,
            cluster_name=cluster_name,
            management_cluster=management_cluster,
            to_url=to_url,
            to_secrets=to_secrets,
        )

        FileHelper.delete_file(file_name)
        # Remove escape and \n characters from json string
        to_json = json.dumps(to_json)
        to_json = json.loads(json.loads(to_json.replace("'", "")))
        FileHelper.dump_json(file_name, to_json)

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
                if self.env != Env.VMC and self.tkgs_util.is_env_tkgs_ns(self.env):
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
        if self.env != Env.VMC and self.tkgs_util.is_env_tkgs_ns(self.env):
            cluster = self.spec.envSpec.vcenterDetails.vcenterCluster
            cluster_status = self.tkgs_util.is_cluster_running(cluster, cluster_name)
            if cluster_status[1] != 200:
                return cluster_status[0], cluster_status[1]

            command = TmcCommands.LIST_TMC_CLUSTERS_MGMT
            output = runShellCommandAndReturnOutputAsList(command)
            if output[1] != 0:
                return "Failed to fetch management cluster list", 500
            if cluster_name in output[0]:
                return "Tanzu " + ssas_type + " registration is not supported on management cluster", 500
            context = self.tkgs_util.connect_to_workload(cluster, cluster_name)
            if context[0] is None:
                return context[1], 500
        else:
            context = TanzuUtil().switch_to_context(cluster_name)
            if context[1] != 200:
                return context[0].json["msg"], context[1]
        cluster_details = SaaSUtil.return_list_of_tmc_clusters(cluster_name)
        if not self.is_saas_registered(cluster_name, cluster_details[1], cluster_details[2], False, ssas_type):
            current_app.logger.info("Registering to tanzu " + ssas_type)
            if not self.check_tmc_enabled():
                return "TMC is not enabled, tmc must be enabled to register tanzu " + ssas_type, 500
            verify_cluster = True if self.env == Env.VMC or not self.tkgs_util.is_env_tkgs_ns(self.env) else False
            if verify_cluster:
                if not TanzuUtil.verify_cluster(cluster_name):
                    return (
                        cluster_name + " is not registered to TMC, cluster must be "
                        "registered to TMC first to register tanzu " + ssas_type,
                        500,
                    )
                if TanzuUtil.get_management_cluster() == cluster_name:
                    return "Tanzu " + ssas_type + " registration is not supported on management cluster", 500
            if SaaSUtil.check_cluster_state_on_tmc(cluster_name, False) is None:
                return "Cluster on TMC is not in healthy state " + cluster_name, 500
            if ssas_type == SAS.TO:
                file_name = TmcConstants.TO_JSON
                self.generate_to_json_file(
                    cluster_details[1], cluster_details[2], cluster_name, self.to_url, self.to_token
                )
            elif ssas_type == SAS.TSM:
                file_name = TmcConstants.TSM_JSON
                exact, partial = self.get_tsm_details()
                self.generate_tsm_json_file(cluster_details[1], cluster_details[2], cluster_name, exact, partial)
            command_create = TmcCommands.INTEGRATE_SAAS.format(file_name=file_name)
            state = runShellCommandAndReturnOutput(command_create)
            if state[1] != 0:
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
            if self.tkgs_util.is_env_tkgs_ns(self.env):
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

    def generate_tsm_json_file(self, management_cluster, provisioner_name, cluster_name, exact, partial):
        """
        Generate tsm_json.json file for TSM integration
        :param management_cluster: management cluster name
        :param provisioner_name: provisioner name
        :param cluster_name: workload cluster name
        :param exact: exact string of namespace exclusion
        :param partial: partial string of namespace exclusion
        :return: None
        """
        file_name = TmcConstants.TSM_JSON
        tsm_json = TmcPayloads.TSM_PAYLOAD.format(
            provisioner_name=provisioner_name, management_cluster=management_cluster, cluster_name=cluster_name
        )
        tsm_json = json.dumps(tsm_json)
        tsm_json = json.loads(json.loads(tsm_json.replace("'", "")))
        if not (exact and partial):
            configurations = {"enableNamespaceExclusions": False}
        else:
            configurations = {"enableNamespaceExclusions": True}
            configurations.update({"namespaceExclusions": []})
            if exact:
                configurations["namespaceExclusions"].append({"match": exact, "type": "EXACT"})
            if partial:
                configurations["namespaceExclusions"].append({"match": partial, "type": "START_WITH"})
        tsm_json["spec"].update({"configurations": configurations})

        FileHelper.delete_file(file_name)
        FileHelper.dump_json(file_name, tsm_json)

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
            command = TmcCommands.GET_SAAS_STATUS.format(
                saas_type=saas, cluster_name=cluster_name, mgmt_cluster=management, provisioner=provisioner
            )
            response = runShellCommandAndReturnOutput(command)
            if "NotFound" in str(response[0]):
                current_app.logger.info(saas + " is not integrated")
                return False
            else:
                if pr:
                    current_app.logger.error(response[0])
                    return False
            load_result = yaml.safe_load(response[0])
            integration = str(load_result["status"]["integrationWorkload"])
            if integration != "OK":
                current_app.logger.info("integrationWorkload status " + integration)
                return False
            else:
                current_app.logger.info("integrationWorkload status " + integration)
            tmcAdapter = str(load_result["status"]["tmcAdapter"])
            if tmcAdapter != "OK":
                current_app.logger.info("tmcAdapter status " + tmcAdapter)
                return False
            else:
                current_app.logger.info("tmcAdapter status " + tmcAdapter)
            return True
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
                if self.tkgs_util.is_env_tkgs_ns(self.env):
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
            status, message = self.create_tkgs_proxy_credential()
            if status is None:
                return None, message

            mgmt = self.spec.envSpec.saasEndpoints.tmcDetails.tmcSupervisorClusterName
            status, message = self.register_supervisor_cluster_tmc(mgmt, vcenter, vcenter_username, vcenter_password)
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
                cluster_endpoint = self.tkgs_util.get_cluster_endpoint(cluster_name, header)

                configure_kubectl = self.kubectl_util.configure_kubectl(cluster_endpoint)
                if configure_kubectl[1] != HTTPStatus.OK:
                    return configure_kubectl[0], HTTPStatus.INTERNAL_SERVER_ERROR

                supervisor_tmc = self.tkgs_util.supervisor_tmc(cluster_endpoint)
                if supervisor_tmc[1] != HTTPStatus.OK:
                    return supervisor_tmc[0], HTTPStatus.INTERNAL_SERVER_ERROR

                supervisor_cluster = self.spec.envSpec.saasEndpoints.tmcDetails.tmcSupervisorClusterName
                if SaaSUtil.check_tmc_Register(supervisor_cluster, True):
                    current_app.logger.info(supervisor_cluster + " is already registered")
                else:
                    cluster_group = self.spec.envSpec.saasEndpoints.tmcDetails.tmcSupervisorClusterGroupName
                    if not cluster_group:
                        cluster_group = "default"
                    os.putenv("TMC_API_TOKEN", self.tmc_refresh_token)
                    list_of_cmd_tmc_login = TmcCommands.TMC_LOGIN.format(user=TmcUser.USER_VSPHERE)
                    runProcess(list_of_cmd_tmc_login)
                    list_of_command_register = TmcCommands.REGISTER_SUPERVISOR_TMC.format(
                        supervisor_cluster=supervisor_cluster, cluster_group=cluster_group
                    )
                    generateYaml = runShellCommandAndReturnOutput(list_of_command_register)
                    if generateYaml[1] != 0:
                        return (
                            " Failed to register Supervisor Cluster " + str(generateYaml[0]),
                            HTTPStatus.INTERNAL_SERVER_ERROR,
                        )
                    main_command = ["kubectl", "get", "ns"]
                    sub_command = ["grep", "svc-tmc"]
                    command_cert = grabPipeOutput(main_command, sub_command)
                    if command_cert[1] != 0:
                        return "Failed to get namespace details", HTTPStatus.INTERNAL_SERVER_ERROR
                    namespace = command_cert[0].split("\\s")[0].strip()
                    os.system("chmod +x " + Paths.INJECT_FILE)
                    os.system(Paths.INJECT_FILE + " " + "k8s-register-manifest.yaml" + " inject_namespace " + namespace)
                    command = ["kubectl", "apply", "-f", "k8s-register-manifest.yaml"]
                    state = runShellCommandAndReturnOutputAsList(command)
                    if state[1] != 0:
                        return "Failed to apply k8s-register-manifest.yaml file", HTTPStatus.INTERNAL_SERVER_ERROR

                    current_app.logger.info("Waiting for TMC registration to complete... ")
                    time.sleep(300)
                    wait_status = SaaSUtil.wait_for_supervisor_tmc_registration(supervisor_cluster)
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

        cluster_create_command = self.get_tmc_command_tkgs_workload_cluster(
            supervisor_cluster, name_space, cluster_name, cluster_version
        )
        if cluster_create_command[0] is None:
            return None, cluster_create_command[1]

        cluster_create_command = cluster_create_command[0]
        current_app.logger.info(cluster_create_command)

        os.putenv("TMC_API_TOKEN", self.tmc_refresh_token)
        tmc_login_command = TmcCommands.TMC_LOGIN.format(user=TmcUser.USER_VSPHERE)
        runProcess(tmc_login_command)
        worload = runShellCommandAndReturnOutputAsList(cluster_create_command)
        if worload[1] != 0:
            return None, "Failed to create  workload cluster " + str(worload[0])
        current_app.logger.info("Waiting for 2 mins for checking status == ready")
        time.sleep(120)
        command_monitor = TmcCommands.GET_CLUSTER_STATUS.format(
            cluster=cluster_name, mgmt_cluster=supervisor_cluster, provisioner=name_space
        )
        count = 0
        found = False
        while count < 135:
            o = runShellCommandAndReturnOutput(command_monitor)
            if o[1] == 0:
                load_item = yaml.safe_load(o[0])
                try:
                    phase = str(load_item["status"]["phase"])
                    wcm = str(load_item["status"]["conditions"]["WCM-Ready"]["status"])
                    health = str(load_item["status"]["health"])
                    if phase == "READY" and wcm == "TRUE" and health == "HEALTHY":
                        found = True
                        current_app.logger.info(
                            "Phase status " + phase + " wcm status " + wcm + " Health status " + health
                        )
                        break
                    current_app.logger.info("Phase status " + phase + " wcm status " + wcm + " Health status " + health)
                except Exception:
                    pass
            time.sleep(20)
            current_app.logger.info("Waited for " + str(count * 20) + "s, retrying")
            count = count + 1
        if not found:
            return None, "Cluster not in ready state"
        return "SUCCESS", "Cluster created successfully on TMC"

    def get_tmc_command_tkgs_workload_cluster(self, supervisor_cluster, name_space, workload_name, version):
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
        allowed = allowed.strip(",")

        workload_cluster_create_command = TmcCommands.CREATE_TKGS_WORKLOAD_CLUSTER.format(
            supervisor_cluster=supervisor_cluster,
            namespace=name_space,
            cluster_group=cluster_group,
            cluster_name=workload_name,
            version=version,
            pod_cidr=pod_cidr,
            service_cidr=service_cidr,
            node_storage_class=node_storage_class,
            allowed_storage_class=allowed,
            default_storage_class=default_class,
            worker_type=worker_vm_class,
            instance_type=control_plane_vm_class,
            node_count=worker_node_count,
        )

        if str(enable_ha).lower() == "true":
            workload_cluster_create_command = f"{workload_cluster_create_command} --high-availability"

        if self.tkgs_util.check_tkgs_proxy_enabled():
            proxy_cred_response = self.create_tkgs_proxy_credential()
            if proxy_cred_response[0] is None:
                return None, proxy_cred_response[1]
            workload_cluster_create_command = (
                f"{workload_cluster_create_command} --proxy-name "
                f"{Tkgs_Extension_Details.TKGS_PROXY_CREDENTIAL_NAME}"
            )
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
                    dict(
                        name=control_plane_volume["name"],
                        mountPath=control_plane_volume["mountPath"],
                        capacity=dict(storage=control_plane_volume["storage"]),
                        storageClass=storageClass,
                    )
                )
            control_plane_vol = True
        except Exception:
            control_plane_vol = False
        try:
            worker_volumes = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.workerVolumes
            )
            worker_vol = True
            worker_volumes_list = []
            for worker_volume in worker_volumes:
                if worker_volume["storageClass"]:
                    storageClass = worker_volume["storageClass"]
                else:
                    storageClass = default_class
                worker_volumes_list.append(
                    dict(
                        name=worker_volume["name"],
                        mountPath=worker_volume["mountPath"],
                        capacity=dict(storage=worker_volume["storage"]),
                        storageClass=storageClass,
                    )
                )
        except Exception:
            worker_vol = False
        if control_plane_vol and worker_vol:
            control_plane_command = ""
            for control_plane_volumes in control_plane_volumes_list:
                control_plane_command += (
                    control_plane_volumes["name"]
                    + ":["
                    + control_plane_volumes["mountPath"]
                    + " "
                    + str(control_plane_volumes["capacity.storage"]).lower().strip("gi")
                    + " "
                    + control_plane_volumes["storageClass"]
                    + "],"
                )
            workload_cluster_create_command = (
                workload_cluster_create_command
                + " --control-plane-volumes "
                + '"'
                + control_plane_command.strip(",")
                + '"'
            )
            worker_command = ""
            for worker_volumes in worker_volumes_list:
                worker_command += (
                    worker_volumes["name"]
                    + ":["
                    + worker_volumes["mountPath"]
                    + " "
                    + str(worker_volumes["capacity"]["storage"]).lower().strip("gi")
                    + " "
                    + worker_volumes["storageClass"]
                    + "]"
                )
            workload_cluster_create_command = (
                workload_cluster_create_command + " --nodepool-volumes " + '"' + worker_command.strip(",") + '"'
            )
        elif control_plane_vol:
            control_plane_command = ""
            for control_plane_volumes in control_plane_volumes_list:
                control_plane_command += (
                    control_plane_volumes["name"]
                    + ":["
                    + control_plane_volumes["mountPath"]
                    + " "
                    + str(control_plane_volumes["capacity"]["storage"]).lower().strip("gi")
                    + " "
                    + control_plane_volumes["storageClass"]
                    + "],"
                )
            workload_cluster_create_command = (
                workload_cluster_create_command
                + " --control-plane-volumes "
                + '"'
                + control_plane_command.strip(",")
                + '"'
            )
        elif worker_vol:
            worker_command = ""
            for worker_volumes in worker_volumes_list:
                worker_command += (
                    worker_volumes["name"]
                    + ":["
                    + worker_volumes["mountPath"]
                    + " "
                    + str(worker_volumes["capacity"]["storage"]).lower().strip("gi")
                    + " "
                    + worker_volumes["storageClass"]
                    + "]"
                )
            workload_cluster_create_command = (
                workload_cluster_create_command + " --nodepool-volumes " + '"' + worker_command.strip(",") + '"'
            )

        return workload_cluster_create_command, "TMC command created successfully"

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
            current_app.logger.error("Failed to run command to create shared cluster " + str(response.text))
            return False, "Failed to run command to create shared cluster " + str(response.text)
        return True, "Successfully created cluster on TMC"
