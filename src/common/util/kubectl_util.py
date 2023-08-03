# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
import os
import time
from http import HTTPStatus

from flask import current_app

from common.operation.constants import Extension, RegexPattern
from common.operation.ShellHelper import (
    grabPipeOutputChagedDir,
    runShellCommandAndReturnOutput,
    runShellCommandAndReturnOutputAsList,
    verifyPodsAreRunning,
)
from common.util.request_api_util import RequestApiUtil

__author__ = "Abhishek Inani"


class KubectlUtil:
    """Class to declare and define Kubectl related commands and their constants"""

    VERSION = "kubectl version --client --short"
    SET_KUBECTL_CONTEXT = "kubectl config use-context {cluster}-admin@{cluster}"
    SWITCH_CONTEXT = "kubectl config use-context {cluster_ip}"
    DELETE_KUBECTL_CONTEXT = "kubectl config delete-context {cluster}-admin@{cluster}"
    DELETE_KUBECTL_CONTEXT_TKGS = "kubectl config delete-context {cluster}"
    DELETE_KUBECTL_CLUSTER = "kubectl config delete-cluster {cluster}"
    GET_PODS = "kubectl get pods -A"
    GET_TKC = "kubectl get tkc -n {name_space}"
    GET_CLUSTER = "kubectl get clusters -n {name_space}"
    SVC_STATUS = "kubectl get svc -n {name_space}"
    GET_TKR = "kubectl get tkr"
    ADD_SERVICES_LABEL = (
        "kubectl label cluster.cluster.x-k8s.io/{cluster} "
        'cluster-role.tkg.tanzu.vmware.com/tanzu-services="" --overwrite=true'
    )
    GET_ALL_PODS = "kubectl get pods -A"
    APPLY = "kubectl apply -f {config_file}"
    LIST_NAMESPACES = "kubectl get namespaces {options}"
    LIST_APPS = "kubectl get apps -n {namespace} {options}"
    GET_APP_DETAILS = "kubectl get app {app_name} -n {namespace} {options}"
    LIST_SECRETS = "kubectl get secret -n {namespace} {options}"
    FILTER_NAME = "-o=name"
    FILTER_JSONPATH = "-o=jsonpath={template}"
    OUTPUT_YAML = "-o yaml"
    OUTPUT_JSON = "-o json"
    CLUSTER_LOGIN = (
        "kubectl vsphere login --server={cluster_ip}"
        " --vsphere-username={vcenter_username} --insecure-skip-tls-verify"
    )
    CLUSTER_LOGIN_WITH_NAMESPACE = (
        "kubectl vsphere login --vsphere-username {vcenter_username} "
        "--server {endpoint_ip} --tanzu-kubernetes-cluster-name {workload_name}"
        " --tanzu-kubernetes-cluster-namespace {cluster_namespace}"
        " --insecure-skip-tls-verify"
    )
    CREATE_SECRET = "kubectl create secret generic {name} --from-file={config_file} -n {namespace}"
    LIST_SERVICE_ACCOUNTS = "kubectl get serviceaccounts -n {namespace} {options}"
    GET_HARBOR_CERT = "kubectl -n {namespace} get secret harbor-tls {options}"
    DELETE = "kubectl delete -f {config_file}"
    DELETE_EXTENSION = "kubectl delete extension {app_name} -n {namespace}"
    GET_SECRET_DETAILS = "kubectl get secret {name} -n {namespace} {options}"
    UPDATE_SECRET = (
        "kubectl create secret generic {name} --from-file={config_file} -n "
        "{namespace} -o yaml --dry-run | kubectl replace -f-"
    )
    KUBECTL_VPSHERE_LOGIN_TKGS_NS = "kubectl vsphere login --vsphere-username {vc_user} --server {endpoint_ip} --tanzu-kubernetes-cluster-namespace {ns} --insecure-skip-tls-verify"
    KUBECTL_USE_TKGS_NS_CONTEXT = "kubectl config use-context {namespace}"
    KUBECTL_GET_TKC = "kubectl get tkc"
    KUBECTL_GET_CLUSTER = "kubectl get clusters"
    KUBECTL_GET_CONTEXT = "kubectl config get-contexts"
    KUBECTL_DELETE_TKGS_CLUSTER = "kubectl delete tanzukubernetescluster --namespace {namespace} {cluster}"
    KUBECTL_DELETE_TKGS_CLUSTER_BETA = "kubectl delete clusters --namespace {namespace} {cluster}"

    def get_kuvbectl_version(self):
        pass

    def configure_kubectl(self, cluster_ip):
        try:
            runShellCommandAndReturnOutputAsList(["mkdir", "tempDir"])
            url = "https://" + cluster_ip + "/wcp/plugin/linux-amd64/vsphere-plugin.zip"
            response = RequestApiUtil.exec_req("GET", url, verify=False)
            if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                current_app.logger.error("vsphere-plugin.zip download failed")
                return None, response.text
            with open(r"/tmp/vsphere-plugin.zip", "wb") as f:
                f.write(response.content)
            create_command = ["unzip", "-o", "/tmp/vsphere-plugin.zip", "-d", "tempDir"]
            output = runShellCommandAndReturnOutputAsList(create_command)
            if output[1] != 0:
                return None, "Failed to unzip vsphere-plugin.zip"
            os.system("mv -f /opt/vmware/arcas/src/tempDir/bin/* /usr/local/bin/")
            runShellCommandAndReturnOutputAsList(["chmod", "+x", "/usr/local/bin/kubectl-vsphere"])
            return "SUCCESS", 200
        except Exception as e:
            current_app.logger.error(str(e))
            return None, 500

    def check_cert_manager_running(self):
        list1 = self.GET_PODS.split()
        list2 = ["grep", "cert-manager"]
        dir = Extension.TKG_EXTENSION_LOCATION
        podName = "cert-manager"
        try:
            cert_state = grabPipeOutputChagedDir(list1, list2, dir)
            if cert_state[1] != 0:
                current_app.logger.error("Failed to get " + podName + " " + cert_state[0])
                return False
            if verifyPodsAreRunning(podName, cert_state[0], RegexPattern.RUNNING):
                current_app.logger.info("Cert Manager is Running.")
                return True
        except Exception:
            return False
        return False

    def check_pinniped_service_status(self):
        try:
            listOfCmd = self.SVC_STATUS.format(name_space="pinniped-supervisor").split()
            output = runShellCommandAndReturnOutputAsList(listOfCmd)
            line1 = output[0][0].split()
            line2 = output[0][1].split()
            if str(line1[3]) == "EXTERNAL-IP":
                try:
                    current_app.logger.info("Successfully retrieved Load Balancer External IP: " + str(line2[3]))
                    current_app.logger.info(
                        "Update the callback URI with the Load Balancers External IP: " + str(line2[3])
                    )
                    return "Load Balancers' External IP: " + str(line2[3]), 200
                except Exception:
                    current_app.logger.error("Failed to retrieve Load Balancers External IP")
                    return "Failed to retrieve Load Balancers' External IP", 500
            return "Failed to retrieve Load Balancers' External IP", 500
        except Exception:
            return "Failed to retrieve Load Balancers' External IP", 500

    def check_pinniped_dex_service_status(self):
        try:
            listOfCmd = self.SVC_STATUS.format(name_space="tanzu-system-auth").split()
            output = runShellCommandAndReturnOutputAsList(listOfCmd)
            line1 = output[0][0].split()
            line2 = output[0][1].split()
            if str(line1[3]) == "EXTERNAL-IP":
                try:
                    current_app.logger.info(
                        "Successfully retrieved dexsvc Load Balancers' External IP: " + str(line2[3])
                    )
                    return "dexsvc Load Balancers' External IP: " + str(line2[3]), 200
                except Exception:
                    current_app.logger.error("Failed to retrieve dexsvc Load Balancers External IP")
                    return (
                        RequestApiUtil.create_json_object(
                            message="Failed to retrieve dexsvc Load Balancers External IP",
                            response_type="ERROR",
                            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                        ),
                        500,
                    )
            return "Failed to retrieve dexsvc Load Balancers' External IP", 500
        except Exception:
            return "Failed to retrieve dexsvc Load Balancers' External IP", 500

    def get_kube_version_full_name(self, kube_version, get_name=False):
        """
        :param kube_version: TKR version prefix present in JSON
        :param get_name: Will fetch the name associated with TKR version
        @desc: This method will fetch the complete name of the provided kubernetes version
        """
        try:
            listOfCmd = self.GET_TKR.split()
            lu = []
            count = 0
            tkr_obtained = False
            while count < 10:
                kube_version_full = runShellCommandAndReturnOutputAsList(listOfCmd)
                if len(kube_version_full[0]) < 2:
                    current_app.logger.warn("Failed to fetch tkr version, retrying in 30s...")
                    time.sleep(30)
                    count = count + 1
                else:
                    tkr_obtained = True
                    break
            if not tkr_obtained:
                current_app.logger.error("Unable to obtain tkr version even after 300s wait ")
                return None, 500
            for version in kube_version_full[0]:
                if (
                    str(version).__contains__(kube_version)
                    and str(version).__contains__("True")
                    and not str(version).__contains__("tiny")
                ):
                    list_ = version.split(" ")
                    for item in list_:
                        if item:
                            lu.append(item)
                    current_app.logger.info(lu)
                    if get_name:
                        return lu[0], 200
                    else:
                        return lu[1], 200
            return None, 500
        except Exception:
            return None, 500

    def get_kube_version_full_name_no_compatibility_check(self, kube_version):
        try:
            listOfCmd = self.GET_TKR.split()
            kube_version_full = runShellCommandAndReturnOutputAsList(listOfCmd)
            lu = []
            for version in kube_version_full[0]:
                if str(version).__contains__(kube_version):
                    list_ = version.split(" ")
                    for item in list_:
                        if item:
                            lu.append(item)
                    current_app.logger.info(lu)
                    return lu[1], 200
            return None, 500
        except Exception:
            return None, 500

    def get_alias_name(self, storage_id):
        command = ["kubectl", "describe", "sc"]
        policy_list = runShellCommandAndReturnOutput(command)
        if policy_list[1] != 0:
            return None, "Failed to get list of policies " + str(policy_list[0]), 500
        ss = str(policy_list[0]).split("\n")
        for s in range(len(ss)):
            if ss[s].__contains__("storagePolicyID=" + storage_id):
                alias = ss[s - 4].replace("Name:", "").strip()
                current_app.logger.info("Alias name " + alias)
                return alias, "SUCCESS"
        return None, "NOT_FOUND"

    def cluster_login(self, cluster_ip, vcenter_username, vc_password):
        os.putenv("KUBECTL_VSPHERE_PASSWORD", vc_password)
        login_command = self.CLUSTER_LOGIN.format(cluster_ip=cluster_ip, vcenter_username=vcenter_username)
        output = runShellCommandAndReturnOutputAsList(login_command.split())
        return output

    def switch_context(self, cluster_ip):
        switch_context = self.SWITCH_CONTEXT.format(cluster_ip=cluster_ip)
        output = runShellCommandAndReturnOutputAsList(switch_context.split())
        return output

    def cluster_login_with_namespace(
        self, vcenter_username, vc_password, endpoint_ip, workload_name, cluster_namespace
    ):
        os.putenv("KUBECTL_VSPHERE_PASSWORD", vc_password)
        connect_command = self.CLUSTER_LOGIN_WITH_NAMESPACE.format(
            vcenter_username=vcenter_username,
            endpoint_ip=endpoint_ip,
            workload_name=workload_name,
            cluster_namespace=cluster_namespace,
        )
        output = runShellCommandAndReturnOutputAsList(connect_command.split())
        return output
