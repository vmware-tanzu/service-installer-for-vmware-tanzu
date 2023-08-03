from http import HTTPStatus

import requests
from flask import current_app, jsonify
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from common.lib.vcenter.vcenter_endpoints_operations import VCEndpointOperations, VCEndpointURLs
from common.model.vsphereTkgsSpec import VsphereTkgsMasterSpec
from common.operation.constants import Env, EnvType
from common.operation.ShellHelper import runShellCommandAndReturnOutputAsList
from common.util.common_utils import CommonUtils
from common.util.kubectl_util import KubectlUtil
from common.util.request_api_util import RequestApiUtil
from common.util.tanzu_util import TanzuUtil

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class TkgsUtil:
    def __init__(self, spec):
        self.spec: VsphereTkgsMasterSpec = spec
        self.vcenter_server = self.spec.envSpec.vcenterDetails.vcenterAddress
        self.vcenter_username = self.spec.envSpec.vcenterDetails.vcenterSsoUser
        password = str(self.spec.envSpec.vcenterDetails.vcenterSsoPasswordBase64)
        self.vc_password = CommonUtils.decode_password(password)

        self.vc_operation = VCEndpointOperations(self.vcenter_server, self.vcenter_username, self.vc_password)
        self.kubectl_util = KubectlUtil()

    def is_env_tkgs_wcp(self, env):
        try:
            if env == Env.VSPHERE:
                tkgs = str(self.spec.envSpec.envType)
                if tkgs.lower() == EnvType.TKGS_WCP:
                    return True
                else:
                    return False
            else:
                return False
        except KeyError:
            return False

    def is_env_tkgs_ns(self, env):
        try:
            if env == Env.VSPHERE:
                tkgs = str(self.spec.envSpec.envType)
                if tkgs.lower() == EnvType.TKGS_NS:
                    return True
                else:
                    return False
            else:
                return False
        except KeyError:
            return False

    def check_tkgs_proxy_enabled(self):
        is_proxy_enabled = False
        try:
            is_proxy_enabled = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.enableProxy
            if str(is_proxy_enabled).lower() == "true":
                is_proxy_enabled = True
            else:
                is_proxy_enabled = False

            return is_proxy_enabled
        except Exception:
            return is_proxy_enabled

    def get_cluster_endpoint(self, cluster_name, header):
        cl_id = self.get_cluster_id(cluster_name)
        if cl_id[1] != HTTPStatus.OK:
            return None, cl_id[0]
        url = VCEndpointURLs.VC_CLUSTER.format(url="https://" + str(self.vcenter_server), cluster_id=str(cl_id[0]))
        cluster_ip_resp = RequestApiUtil.exec_req("GET", url, verify=False, headers=header)
        if cluster_ip_resp.status_code != HTTPStatus.OK:
            response = RequestApiUtil.create_json_object(
                "Failed to fetch API server cluster endpoint - " + self.vcenter_server,
                response_type="ERROR",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return response, HTTPStatus.INTERNAL_SERVER_ERROR

        cluster_endpoint = cluster_ip_resp.json()["api_server_cluster_endpoint"]
        return cluster_endpoint

    def supervisor_tmc(self, cluster_ip):
        command = ["tanzu", "config", "server", "list"]
        server_list = runShellCommandAndReturnOutputAsList(command)
        if server_list[1] != 0:
            return " Failed to get list of logins " + str(server_list[0]), HTTPStatus.INTERNAL_SERVER_ERROR
        if str(server_list[0]).__contains__(cluster_ip):
            delete_response = TanzuUtil.delete_config_server(cluster_ip)
            if delete_response[1] != HTTPStatus.OK:
                current_app.logger.info("Server config delete failed")
                return "Server config delete failed", HTTPStatus.INTERNAL_SERVER_ERROR
        current_app.logger.info("Logging in to cluster " + cluster_ip)
        output = self.kubectl_util.cluster_login(cluster_ip, self.vcenter_username, self.vc_password)
        if output[1] != 0:
            return " Failed while connecting to Supervisor Cluster", HTTPStatus.INTERNAL_SERVER_ERROR
        output = self.kubectl_util.switch_context(cluster_ip)
        if output[1] != 0:
            return " Failed to use  context " + str(output[0]), HTTPStatus.INTERNAL_SERVER_ERROR

        switch_context = [
            "tanzu",
            "login",
            "--name",
            cluster_ip,
            "--kubeconfig",
            "/root/.kube/config",
            "--context",
            cluster_ip,
        ]
        output = runShellCommandAndReturnOutputAsList(switch_context)
        if output[1] != 0:
            return " Failed to switch context to Supervisor Cluster " + str(output[0]), HTTPStatus.INTERNAL_SERVER_ERROR
        return "SUCCESS", HTTPStatus.OK

    def is_wcp_enabled(self, cluster_id):
        response_csrf = self.vc_operation.vc_cluster(self.vcenter_server, cluster_id)
        if response_csrf.status_code != HTTPStatus.OK:
            if response_csrf.status_code == 400:
                if (
                    response_csrf.json()["messages"][0]["default_message"]
                    == "Cluster with identifier " + cluster_id + " does "
                    "not have Workloads enabled."
                ):
                    return False, None

        elif response_csrf.json()["config_status"] == "RUNNING":
            return True, response_csrf.json()
        else:
            return False, None

    def get_cluster_end_point(self, cluster_name, header):
        id_cluster = self.get_cluster_id(cluster_name)
        url = VCEndpointURLs.VC_CLUSTER.format(url="https://" + str(self.vcenter_server), cluster_id=str(id_cluster[0]))
        cluster_ip_resp = RequestApiUtil.exec_req("GET", url, verify=False, headers=header)
        if cluster_ip_resp.status_code != HTTPStatus.OK:
            response = RequestApiUtil.create_json_object(
                "Failed to fetch API server cluster endpoint - " + str(self.vcenter_server),
                "ERROR",
                cluster_ip_resp.status_code,
            )
            return response, cluster_ip_resp.status_code
        return cluster_ip_resp.json()["api_server_cluster_endpoint"], HTTPStatus.OK

    def get_cluster_id(self, cluster):
        try:
            session_id, status_code = self.vc_operation.get_session()
            if status_code != HTTPStatus.OK:
                return session_id, status_code

            vcenter_datacenter = self.spec.envSpec.vcenterDetails.vcenterDatacenter
            if str(vcenter_datacenter).__contains__("/"):
                vcenter_datacenter = vcenter_datacenter[vcenter_datacenter.rindex("/") + 1 :]
            if str(cluster).__contains__("/"):
                cluster = cluster[cluster.rindex("/") + 1 :]
            dc_url = VCEndpointURLs.VC_DATACENTER.format(url=self.vc_operation.vcenter_url, dc_name=vcenter_datacenter)
            datcenter_resp = RequestApiUtil.exec_req(
                "GET",
                dc_url,
                verify=False,
                headers={"vmware-api-session-id": session_id},
            )
            if not RequestApiUtil.verify_resp(datcenter_resp, status_code=HTTPStatus.OK):
                current_app.logger.error(datcenter_resp.json())
                response = RequestApiUtil.create_json_object(
                    "Failed to fetch datacenter ID for datacenter - " + vcenter_datacenter,
                    "ERROR",
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR

            datacenter_id = datcenter_resp.json()[0]["datacenter"]

            cluster_id_resp = RequestApiUtil.exec_req(
                "GET",
                VCEndpointURLs.VC_CLUSTER_DC.format(
                    url=self.vc_operation.vcenter_url, datacenter_id=datacenter_id, cluster=cluster
                ),
                verify=False,
                headers={"vmware-api-session-id": session_id},
            )
            if not RequestApiUtil.verify_resp(cluster_id_resp, status_code=HTTPStatus.OK):
                current_app.logger.error(cluster_id_resp.json())
                response = RequestApiUtil.create_json_object(
                    "Failed to fetch cluster ID for cluster - " + cluster, "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR
            return cluster_id_resp.json()[0]["cluster"], HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(e)
            response = RequestApiUtil.create_json_object(
                "Failed to fetch cluster ID for cluster - " + cluster, "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
            )
            return response, HTTPStatus.INTERNAL_SERVER_ERROR

    def connect_to_workload(self, cluster, workload_name):
        try:
            current_app.logger.info("Connecting to workload cluster...")
            cluster_id = self.get_cluster_id(cluster)
            if cluster_id[1] != HTTPStatus.OK:
                current_app.logger.error(cluster_id[0])
                return None, cluster_id[0].json["msg"]

            cluster_namespace = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereNamespaceName
            )
            cluster_id = cluster_id[0]
            wcp_status = self.is_wcp_enabled(cluster_id)
            if wcp_status[0]:
                endpoint_ip = wcp_status[1]["api_server_cluster_endpoint"]
            else:
                return None, "Failed to obtain cluster endpoint IP on given cluster - " + workload_name
            current_app.logger.info("logging into cluster - " + endpoint_ip)
            output = self.kubectl_util.cluster_login_with_namespace(
                self.vcenter_username, self.vc_password, endpoint_ip, workload_name, cluster_namespace
            )
            if output[1] != 0:
                current_app.logger.error(output[0])
                return None, "Failed to login to cluster endpoint - " + endpoint_ip
            context_output = self.kubectl_util.switch_context(workload_name)
            if context_output[1] != 0:
                current_app.logger.error(context_output[0])
                return None, "Failed to login to cluster context - " + workload_name
            return "SUCCESS", "Successfully connected to workload cluster"
        except Exception:
            return None, "Exception occurred while connecting to workload cluster"

    def fetch_namespace_info(self, env):
        try:
            if env == Env.VSPHERE:
                name_space = self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereNamespaceName

                if not (self.vcenter_server or self.vcenter_username or self.vc_password):
                    current_app.logger.error("Failed to fetch VC details")
                    response = RequestApiUtil.create_json_object(
                        "Failed to find VC details", "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
                    )
                    return response, HTTPStatus.INTERNAL_SERVER_ERROR
            else:
                current_app.logger.error("Wrong environment provided to fetch namespace details")
                response = RequestApiUtil.create_json_object(
                    "Wrong environment provided to fetch namespace details", "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR

            session_id, status_code = self.vc_operation.get_session()
            if status_code != HTTPStatus.OK:
                return session_id, status_code

            header = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "vmware-api-session-id": session_id,
            }
            namespace_response = RequestApiUtil.exec_req(
                "GET",
                VCEndpointURLs.VC_NAMESPACE.format(url=self.vc_operation.vcenter_url, name_space=name_space),
                headers=header,
                verify=False,
            )
            if namespace_response.status_code != HTTPStatus.OK:
                response = RequestApiUtil.create_json_object(
                    "Failed to fetch details for namespace - " + name_space, "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR

            storage_policies = []
            if namespace_response.json()["config_status"] != "RUNNING":
                current_app.logger.error("Selected namespace is not in running state - " + name_space)
                response = RequestApiUtil.create_json_object(
                    "Selected namespace is not in running state - " + name_space,
                    "ERROR",
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR

            for policy in namespace_response.json()["storage_specs"]:
                storage_policies.append(policy["policy"])
            vm_classes = namespace_response.json()["vm_service_spec"]["vm_classes"]
            policy_names = []

            policies = self.vc_operation.get_storage_policies()
            for id in storage_policies:
                for policy in policies[0]:
                    if policy["policy"] == id:
                        policy_names.append(policy["name"])

            if not policy_names:
                current_app.logger.error("Policy names list found empty for given namespace - " + name_space)
                response = RequestApiUtil.create_json_object(
                    "Policy names list found empty for given namespace - " + name_space,
                    "ERROR",
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR

            if not vm_classes:
                current_app.logger.error("VM Classes list found empty for given namespace - " + name_space)
                response = RequestApiUtil.create_json_object(
                    "VM Classes list found empty for given namespace - " + name_space,
                    "ERROR",
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR

            current_app.logger.info("Found namespace details successfully")
            d = {
                "responseType": "SUCCESS",
                "msg": "Found namespace details successfully - " + name_space,
                "STATUS_CODE": HTTPStatus.OK,
                "VM_CLASSES": vm_classes,
                "STORAGE_POLICIES": policy_names,
            }
            return jsonify(d), HTTPStatus.OK
        except Exception:
            response = RequestApiUtil.create_json_object(
                "Exception occurred while fetching details for namespace - " + name_space,
                "ERROR",
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

            return response, HTTPStatus.INTERNAL_SERVER_ERROR

    def is_cluster_running(self, cluster, workload_name):
        try:
            current_app.logger.info("Check if cluster is in running state - " + workload_name)

            cluster_id = self.get_cluster_id(cluster)
            if cluster_id[1] != HTTPStatus.OK:
                current_app.logger.error(cluster_id[0])
                response = RequestApiUtil.create_json_object(cluster_id[0], "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR)
                return response, HTTPStatus.INTERNAL_SERVER_ERROR

            cluster_id = cluster_id[0]

            wcp_status = self.is_wcp_enabled(cluster_id)
            if wcp_status[0]:
                endpoint_ip = wcp_status[1]["api_server_cluster_endpoint"]
            else:
                current_app.logger.error("WCP not enabled on given cluster - " + cluster)
                response = RequestApiUtil.create_json_object(
                    "WCP not enabled on given cluster - " + cluster, "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR

            current_app.logger.info("logging into cluster - " + endpoint_ip)
            output = self.kubectl_util.cluster_login(endpoint_ip, self.vcenter_username, self.vc_password)
            if output[1] != 0:
                current_app.logger.error("Failed while connecting to Supervisor Cluster ")
                response = RequestApiUtil.create_json_object(
                    "Failed while connecting to Supervisor Cluster", "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR
            output = self.kubectl_util.switch_context(endpoint_ip)
            if output[1] != 0:
                current_app.logger.error("Failed to use  context " + str(output[0]))
                response = RequestApiUtil.create_json_object(
                    "Failed to use context " + str(output[0]), "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR

            name_space = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereNamespaceName
            )
            cluster_kind = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereWorkloadClusterKind
            )
            if cluster_kind == EnvType.TKGS_CLUSTER_CLASS_KIND:
                clusters_output = runShellCommandAndReturnOutputAsList(
                    self.kubectl_util.GET_CLUSTER.format(name_space=name_space).split()
                )
            else:
                clusters_output = runShellCommandAndReturnOutputAsList(
                    self.kubectl_util.GET_TKC.format(name_space=name_space).split()
                )
            if clusters_output[1] != 0:
                current_app.logger.error("Failed to fetch cluster running status " + str(clusters_output[0]))
                response = RequestApiUtil.create_json_object(
                    "Failed to fetch cluster running status " + str(clusters_output[0]),
                    "ERROR",
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR

            index = None
            for item in range(len(clusters_output[0])):
                if clusters_output[0][item].split()[0] == workload_name:
                    index = item
                    break

            if index is None:
                current_app.logger.error("Unable to find cluster - " + workload_name)
                response = RequestApiUtil.create_json_object(
                    "Unable to find cluster - " + workload_name, "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR

            output = clusters_output[0][index].split()
            if not ((output[5] == "True" or output[5] == "running") and output[6] == "True"):
                current_app.logger.error("Failed to fetch workload cluster running status " + str(clusters_output[0]))
                current_app.logger.error("Found below Cluster status - ")
                current_app.logger.error("READY: " + str(output[5]) + " and TKR COMPATIBLE: " + str(output[6]))
                response = RequestApiUtil.create_json_object(
                    "Failed to fetch workload cluster running status " + str(clusters_output[0]),
                    "ERROR",
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )

                return response, HTTPStatus.INTERNAL_SERVER_ERROR
            response = RequestApiUtil.create_json_object(
                "Workload cluster is in running status.", "SUCCESS", HTTPStatus.OK
            )
            return response, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(str(e))
            response = RequestApiUtil.create_json_object(
                "Exception occurred while fetching the status of workload cluster" + str(e),
                "ERROR",
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

            return response, HTTPStatus.INTERNAL_SERVER_ERROR

    def get_storage_alias_details(self, storage_class):
        policy_id = self.vc_operation.get_policy_id(storage_class)
        if policy_id[0] is None:
            return None, "Failed to get policy id"
        default = self.kubectl_util.get_alias_name(policy_id[0])
        if default[0] is None:
            current_app.logger.error(default[1])
            return None, "Failed to get Alias name"
        default_class = default[0]
        return default_class, "Alias name obtained successfully"
