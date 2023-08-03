# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import base64
import json
import os
import time
from http import HTTPStatus
from pathlib import Path

import requests
from flask import Blueprint, current_app, jsonify, request
from jinja2 import Template
from ruamel import yaml as ryaml

from common.certificate_base64 import getBase64CertWriteToFile
from common.common_utilities import (
    checkDataProtectionEnabled,
    checkDataProtectionEnabledVelero,
    cidr_to_netmask,
    convertStringToCommaSeperated,
    createClusterFolder,
    enable_data_protection,
    enable_data_protection_velero,
    envCheck,
    getBodyResourceSpec,
    getCountOfIpAdress,
    preChecks,
    seperateNetmaskAndIp,
    verifyVcenterVersion,
)
from common.lib.govc.govc_operations import GOVCOperations
from common.lib.vcenter.vcenter_endpoints_operations import VCEndpointOperations, VCEndpointURLs
from common.model.vsphereTkgsSpecNameSpace import VsphereTkgsNameSpaceMasterSpec
from common.operation.constants import ControllerLocation, Csp, Env, EnvType, Paths, Tkgs_Extension_Details
from common.operation.ShellHelper import grabPipeOutput, runProcess, runShellCommandAndReturnOutputAsList
from common.operation.vcenter_operations import getDvPortGroupId
from common.prechecks.precheck import checkClusterVersionCompatibility, get_tkr_name
from common.util.file_helper import FileHelper
from common.util.kubectl_util import KubectlUtil
from common.util.local_cmd_helper import LocalCmdHelper
from common.util.request_api_util import RequestApiUtil
from common.util.saas_util import SaaSUtil
from common.util.tanzu_util import TanzuUtil
from common.util.tkgs_util import TkgsUtil

vsphere_tkgs_workload_cluster = Blueprint("vsphere_tkgs_workload_cluster", __name__, static_folder="workloadConfig")


class TkgsWorkloadCluster:
    def __init__(self, spec):
        self.spec: VsphereTkgsNameSpaceMasterSpec = spec
        self.vCenter = current_app.config["VC_IP"]
        self.vc_user = current_app.config["VC_USER"]
        self.vc_password = current_app.config["VC_PASSWORD"]
        self.vc_data_center = current_app.config["VC_DATACENTER"]
        self.cluster_name = spec.envSpec.vcenterDetails.vcenterCluster
        self.vc_operation = VCEndpointOperations(self.vCenter, self.vc_user, self.vc_password)
        self.kubectl_util = KubectlUtil()
        self.govc_operation = GOVCOperations(
            self.vCenter,
            self.vc_user,
            self.vc_password,
            self.cluster_name,
            self.vc_data_center,
            None,
            LocalCmdHelper(),
        )
        self.tkgs_util = TkgsUtil(self.spec)

    def create_tkg_workload_cluster(self, env, saas_util):
        try:
            sess, status_code = self.vc_operation.get_session()
            if status_code != HTTPStatus.OK:
                return sess, status_code

            header = {"Accept": "application/json", "Content-Type": "application/json", "vmware-api-session-id": sess}
            cluster_name = self.cluster_name
            if str(cluster_name).__contains__("/"):
                cluster_name = cluster_name[cluster_name.rindex("/") + 1 :]
            id_cluster = self.tkgs_util.get_cluster_id(cluster_name)
            if id_cluster[1] != HTTPStatus.OK:
                return None, id_cluster[0]
            cluster_endpoint, status_code = self.tkgs_util.get_cluster_end_point(cluster_name, header)
            if status_code != HTTPStatus.OK:
                return cluster_endpoint, status_code
            configure_kubectl_ = self.kubectl_util.configure_kubectl(cluster_endpoint)
            if configure_kubectl_[1] != HTTPStatus.OK:
                return configure_kubectl_[0], HTTPStatus.INTERNAL_SERVER_ERROR
            self.tkgs_util.supervisor_tmc(cluster_endpoint)
            current_app.logger.info("Switch context to name space")
            name_space = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereNamespaceName
            )

            workload_name = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereWorkloadClusterName
            )
            if not createClusterFolder(workload_name):
                response = RequestApiUtil.create_json_object(
                    "Failed to create directory: " + Paths.CLUSTER_PATH + workload_name,
                    "ERROR",
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return response
            current_app.logger.info(
                "The config files for workload cluster will be located at:" " " + Paths.CLUSTER_PATH + workload_name
            )
            current_app.logger.info(
                "Before deploying cluster, checking if namespace is in running status..." + name_space
            )
            wcp_status = self.check_cluster_status(header, name_space, id_cluster[0])
            if wcp_status[0] is None:
                return None, wcp_status[1]

            switch = ["kubectl", "config", "use-context", name_space]
            switch_context = runShellCommandAndReturnOutputAsList(switch)
            if switch_context[1] != 0:
                return None, "Failed to switch  to context " + str(switch_context[0]), HTTPStatus.INTERNAL_SERVER_ERROR

            cluster_kind = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereWorkloadClusterKind
            )
            command_beta = ["kubectl", "get", "clusters"]
            command_alpha = ["kubectl", "get", "tanzukubernetescluster"]
            cluster_list = []
            cluster_list_beta = runShellCommandAndReturnOutputAsList(command_beta)
            cluster_list_alpha = runShellCommandAndReturnOutputAsList(command_alpha)
            if cluster_list_beta[1] != 0 and cluster_list_alpha[1] != 0:
                return None, "Failed to get list of clusters ", HTTPStatus.INTERNAL_SERVER_ERROR
            if cluster_list_beta[1] == 0:
                cluster_list = cluster_list + cluster_list_beta[0]
            if cluster_list_alpha[1] == 0:
                cluster_list = cluster_list + cluster_list_alpha[0]

            for tkgs_cluster in cluster_list:
                if str(tkgs_cluster.split()[0]) == workload_name:
                    current_app.logger.info("Cluster with same name already exist - " + workload_name)
                    return "Cluster with same name already exist ", HTTPStatus.OK
                else:
                    if str(tkgs_cluster.split(" ")[0]) == workload_name:
                        current_app.logger.info("Cluster with same name already exist - " + workload_name)
                        return "Cluster with same name already exist ", HTTPStatus.OK
            if saas_util.check_tmc_enabled():
                version = (
                    self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereWorkloadClusterVersion
                )

                # if user using json and v not appended to version
                if not version.startswith("v"):
                    version = "v" + version
                is_compatible = checkClusterVersionCompatibility(
                    self.vCenter, self.vc_user, self.vc_password, cluster_name, version
                )
                if not is_compatible[0]:
                    return None, is_compatible[1]

                current_app.logger.info("Provided cluster version is valid!")

                response = saas_util.create_tkgs_workload_cluster_on_tmc(
                    cluster_name=workload_name, cluster_version=version
                )
                if response[0] is None:
                    return None, response[1]
                return "SUCCESS", HTTPStatus.OK
            else:
                try:
                    gen = self.generate_yaml_file(workload_name)
                    if gen is None:
                        return None, "Failed"
                except Exception as e:
                    return None, "Failed to generate yaml file " + str(e)

                command = ["kubectl", "apply", "-f", gen]
                worload = runShellCommandAndReturnOutputAsList(command)
                if worload[1] != 0:
                    return None, "Failed to create workload " + str(worload[0])
                current_app.logger.info(worload[0])
                name_space = (
                    self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereNamespaceName
                )
                workload_name = (
                    self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereWorkloadClusterName
                )
                current_app.logger.info("Waiting for 60 seconds for cluster creation to be initiated...")
                time.sleep(60)

                cluster_kind = (
                    self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereWorkloadClusterKind
                )
                if cluster_kind == EnvType.TKGS_CLUSTER_CLASS_KIND:
                    count = 0
                    while count < 90:
                        output = self.check_v1beta1_cluster_status(workload_cls=workload_name, namespace=name_space)
                        if output:
                            current_app.logger.info("Waiting for 10 minutes to let the configuration complete")
                            time.sleep(600)
                            return "SUCCESS", "DEPLOYED"
                        else:
                            count = count + 1
                            time.sleep(30)
                            current_app.logger.info("Waited for " + str(count * 30) + "s, retrying")

                    current_app.logger.error("Cluster is not up and running on waiting " + str(count * 30) + "s")
                    return None, "Failed"
                else:
                    command = ["kubectl", "get", "tkc", "-n", name_space]
                    count = 0
                    found = False
                    while count < 90:
                        worload = runShellCommandAndReturnOutputAsList(command)
                        if worload[1] != 0:
                            return None, "Failed to monitor workload " + str(worload[0])

                        try:
                            for item in range(len(worload[0])):
                                if worload[0][item].split()[0] == workload_name:
                                    index = item
                                    break

                            output = worload[0][index].split()
                            if not ((output[5] == "True" or output[5] == "running") and output[6] == "True"):
                                current_app.logger.info("Waited for " + str(count * 30) + "s, retrying")
                                count = count + 1
                                time.sleep(30)
                            else:
                                found = True
                                break
                        except Exception:
                            current_app.logger.info(
                                "Cluster creation is not yet initiated. "
                                "Waited for " + str(count * 30) + "s, retrying"
                            )
                            count = count + 1
                            time.sleep(30)

                if not found:
                    current_app.logger.error("Cluster is not up and running on waiting " + str(count * 30) + "s")
                    return None, "Failed"
                return "SUCCESS", "DEPLOYED"
        except Exception as e:
            return None, "Failed to create tkg workload cluster  " + str(e)

    def check_v1beta1_cluster_status(self, workload_cls, namespace):
        try:
            command_main = ["kubectl", "describe", "cluster", workload_cls, "-n", namespace]
            command_pipe = ["grep", "Status"]
            output = grabPipeOutput(command_main, command_pipe)
            if output[0].__contains__("False"):
                return False
            else:
                current_app.logger.info("All the cluster services are Ready")
                return True
        except Exception as e:
            current_app.logger.error(str(e))
            return False

    def check_cluster_status(self, header, name_space, cluster_id):
        try:
            url = VCEndpointURLs.VC_NAMESPACE.format(url=self.vc_operation.vcenter_url, name_space="")
            namespace_status = self.check_name_space_running_status(url, header, name_space, cluster_id)
            running = False
            if namespace_status[0] != "SUCCESS":
                current_app.logger.info("Namespace is not in running status... retrying")
            else:
                running = True

            count = 0
            while count < 60 and not running:
                namespace_status = self.check_name_space_running_status(url, header, name_space, cluster_id)
                if namespace_status[0] == "SUCCESS":
                    running = True
                    break
                count = count + 1
                time.sleep(5)
                current_app.logger.info("Waited for " + str(count * 1) + "s ...retrying")

            if not running:
                return (
                    None,
                    "Namespace is not in running status - " + name_space + ". Waited for " + str(count * 5) + "seconds",
                )

            current_app.logger.info("Checking Cluster WCP status...")
            url1 = VCEndpointURLs.VC_CLUSTER.format(url="https://" + str(self.vCenter), cluster_id=str(cluster_id))
            count = 0
            found = False
            while count < 60 and not found:
                response_csrf = RequestApiUtil.exec_req("GET", url1, headers=header, verify=False)
                try:
                    if response_csrf.json()["config_status"] == "RUNNING":
                        found = True
                        break
                    else:
                        if response_csrf.json()["config_status"] == "ERROR":
                            return None, "WCP status in ERROR"
                    current_app.logger.info("Cluster config status " + response_csrf.json()["config_status"])
                except Exception:
                    pass
                time.sleep(20)
                count = count + 1
                current_app.logger.info("Waited " + str(count * 20) + "s, retrying")
            if not found:
                current_app.logger.error("Cluster is not running on waiting " + str(count * 20))
                return None, "Failed"
            else:
                current_app.logger.info("WCP config status " + response_csrf.json()["config_status"])

            return "SUCCESS", "WCP and Namespace configuration check pass"
        except Exception as e:
            current_app.logger.error(str(e))
            return None, "Exception occurred while checking cluster config status"

    def get_calico_ref_name(self, tkr_name):
        """
        This method is used to fetch the reference name for Calico CNI
        """
        command_main = ["kubectl", "get", "tkr", tkr_name, "-o", "yaml"]
        command_pipe = ["grep", "calico"]
        output = grabPipeOutput(command_main, command_pipe)
        if output[1] == 0:
            return output[0].split()[2]
        else:
            current_app.logger.error("Failed to fetch Calico reference name for TKR: " + tkr_name)
            return None

    def generate_yaml_file_v1beta1(self):
        try:
            """
            This method is used to generate a YAML template for the Workload cluster with v1beta1 APIs.
            """
            # Fetch workload cluster name
            workload_name = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereWorkloadClusterName
            )

            # Removing older file from the system
            cluster_path = Paths.CLUSTER_PATH
            file = os.path.join(cluster_path, workload_name, "tkgs_workload.yaml")
            command = ["rm", "-rf", file]
            runShellCommandAndReturnOutputAsList(command)

            # Rendering template for the v1beta1 file
            deploy_yaml = FileHelper.read_resource(Paths.TKGS_WORKLOAD_V1BETA1_J2)
            t = Template(deploy_yaml)
            current_app.logger.info("Reading v1beta1 template file")
            # Fetch the right TKR name
            kube_version = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereWorkloadClusterVersion
            )
            cluster_name = self.spec.envSpec.vcenterDetails.vcenterCluster
            if str(cluster_name).__contains__("/"):
                cluster_name = cluster_name[cluster_name.rindex("/") + 1 :]
            if not kube_version.startswith("v"):
                kube_version = "v" + kube_version
            is_compatible = checkClusterVersionCompatibility(
                self.vCenter, self.vc_user, self.vc_password, cluster_name, kube_version
            )
            if is_compatible[0]:
                current_app.logger.info("Provided cluster version is valid !")
            else:
                return None
            tkr_name = get_tkr_name(kube_version, self.vCenter, self.vc_user, self.vc_password, cluster_name)
            if tkr_name[1] == 500:
                return None
            else:
                tkr_name = tkr_name[0]
            current_app.logger.info("Fetched TKR Name: " + tkr_name)

            try:
                cni = self.spec.tkgsComponentSpec.tkgServiceConfig.defaultCNI
            except Exception:
                cni = "antrea"
            if cni.lower() == "calico":
                calico_ref_name = self.get_calico_ref_name(tkr_name)
                if calico_ref_name is None:
                    current_app.logger.error("Failed to fetch Calico ref name for TKR: " + tkr_name)
                    return None
                else:
                    current_app.logger.info("Found Calico ref name for TKR: " + calico_ref_name)
            else:
                calico_ref_name = ""

            # Fetch namespace for the cluster deployment
            name_space = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereNamespaceName
            )
            # Fetch Service and Pod CIDR values
            service_cidr = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.serviceCidrBlocks
            )
            service_cidr = convertStringToCommaSeperated(service_cidr)
            pod_cidr = self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.podCidrBlocks
            pod_cidr = convertStringToCommaSeperated(pod_cidr)
            # Count for control plane nodes
            enable_ha = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.enableControlPlaneHa
            )
            if str(enable_ha).lower() == "true":
                current_app.logger.info("Control plane has HA enabled")
                count = "3"
            else:
                current_app.logger.info("Control plane has HA disabled")
                count = "1"
            # Worker node VM class
            worker_vm_class = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.workerVmClass
            )
            # Worker node count
            worker_node_count = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.workerNodeCount
            )
            # Control plane VM class
            control_plane_vm_class = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.controlPlaneVmClass
            )
            # Fetch node storage class
            node_storage_class = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.nodeStorageClass
            )
            policy_id = self.vc_operation.get_policy_id(node_storage_class)
            if policy_id[0] is None:
                current_app.logger.error("Failed to get policy id")
                return None
            allowed_ = self.kubectl_util.get_alias_name(policy_id[0])
            if allowed_[0] is None:
                current_app.logger.error(allowed_[1])
                return None
            node_storage_class = str(allowed_[0])
            current_app.logger.info("Fetched node storage class: " + node_storage_class)
            # Fetch Allowed Storage classes and put as list
            allowed_classes = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.allowedStorageClasses
            )
            allowed = ""
            classes = allowed_classes
            for c in classes:
                policy_id = self.vc_operation.get_policy_id(c)
                if policy_id[0] is None:
                    current_app.logger.error("Failed to get policy id")
                    return None
                allowed_ = self.kubectl_util.get_alias_name(policy_id[0])
                if allowed_[0] is None:
                    current_app.logger.error(allowed_[1])
                    return None
                allowed += str(allowed_[0]) + ","
            if allowed is None:
                current_app.logger.error("Failed to get allowed classes")
                return None
            allowed = allowed.strip(",")
            allowed_class_list = convertStringToCommaSeperated(allowed)
            current_app.logger.info("Fetched allowed storage classes: ")
            current_app.logger.info(allowed_class_list)

            # Fetch default class
            default_classes = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.defaultStorageClass
            )
            policy_id = self.vc_operation.get_policy_id(default_classes)
            if policy_id[0] is None:
                current_app.logger.error("Failed to get policy id")
                return None
            default_class = self.kubectl_util.get_alias_name(policy_id[0])
            if default_class[0] is None:
                current_app.logger.error(default_class[1])
                return None
            default_class = str(default_class[0])
            current_app.logger.info("Fetched default storage class: " + default_class)

            # Fetch worker volumes
            worker_volumes = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.workerVolumes
            )
            if len(worker_volumes) > 0:
                worker_volume_present = "true"
                current_app.logger.info("Configure additional volumes for Worker Nodes")
                worker_volumes_list = []
                for worker_volume in worker_volumes:
                    worker_volumes_list.append(
                        dict(
                            name=worker_volume["name"],
                            mountPath=worker_volume["mountPath"],
                            storage=worker_volume["storage"],
                            storageClass=worker_volume["storageClass"],
                        )
                    )
            else:
                worker_volume_present = "false"
                worker_volumes_list = []

            # Fetch whether proxy is enabled
            cert_list = []
            try:
                is_proxy_enabled = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.enableProxy
                if str(is_proxy_enabled).lower() == "true":
                    current_app.logger.info("Fetching proxy values as proxy is enabled")
                    http_proxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.httpProxy
                    https_proxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.httpsProxy
                    no_proxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.noProxy
                    no_proxy_list = convertStringToCommaSeperated(no_proxy)
                    proxy_cert = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.proxyCert
                else:
                    current_app.logger.info("Proxy is disabled")
                    http_proxy = ""
                    https_proxy = ""
                    no_proxy_list = []
                    proxy_cert = ""
            except Exception:
                current_app.logger.info("Proxy is disabled")
                is_proxy_enabled = "false"
                http_proxy = ""
                https_proxy = ""
                no_proxy_list = []
                proxy_cert = ""

            additional_cert_paths = self.spec.tkgsComponentSpec.tkgServiceConfig.additionalTrustedCAs.paths
            additional_cert_endpoints = self.spec.tkgsComponentSpec.tkgServiceConfig.additionalTrustedCAs.endpointUrls
            count = 1
            if proxy_cert:
                cert = Path(proxy_cert).read_text()
                string_bytes = cert.encode("ascii")
                base64_bytes = base64.b64encode(string_bytes)
                cert_base64 = base64_bytes.decode("ascii")
                string_bytes = cert_base64.encode("ascii")
                base64_bytes = base64.b64encode(string_bytes)
                cert_base64 = base64_bytes.decode("ascii")
                cert_list.append(dict(name="additional-ca-" + count, data=cert_base64))
                count = count + 1

            for path in additional_cert_paths:
                cert = Path(path).read_text()
                string_bytes = cert.encode("ascii")
                base64_bytes = base64.b64encode(string_bytes)
                cert_base64 = base64_bytes.decode("ascii")

                string_bytes = cert_base64.encode("ascii")
                base64_bytes = base64.b64encode(string_bytes)
                cert_base64 = base64_bytes.decode("ascii")
                cert_list.append(dict(name="additional-ca-" + count, data=cert_base64))
                count = count + 1

            for endpoint in additional_cert_endpoints:
                getBase64CertWriteToFile(endpoint, "443")
                with open("cert.txt", "r") as file2:
                    cert_base64 = file2.readline()
                string_bytes = cert_base64.encode("ascii")
                base64_bytes = base64.b64encode(string_bytes)
                cert_base64 = base64_bytes.decode("ascii")
                cert_list.append(dict(name="additional-ca-" + count, data=cert_base64))
                count = count + 1

            if len(cert_list) > 0:
                additional_certs_present = "true"
            else:
                additional_certs_present = "false"

            for list_item in cert_list:
                cert_file_name = self.create_secret_for_trusted_cert(
                    workload_name, name_space, list_item["name"], list_item["data"]
                )
                if cert_file_name:
                    command = ["kubectl", "apply", "-f", cert_file_name]
                    secret_applied = runShellCommandAndReturnOutputAsList(command)
                    if secret_applied[1] != 0:
                        return None, "Failed apply Secret " + str(secret_applied[0])

            FileHelper.write_to_file(
                t.render(
                    workload_name=workload_name,
                    cni=cni,
                    tkr_name=tkr_name,
                    calico_ref_name=calico_ref_name,
                    name_space=name_space,
                    service_cidr=service_cidr,
                    pod_cidr=pod_cidr,
                    control_plane_count=int(count),
                    worker_node_count=int(worker_node_count),
                    worker_vm_class=worker_vm_class,
                    node_storage_class=node_storage_class,
                    control_plane_vm_class=control_plane_vm_class,
                    allowed_storage_classes=allowed_class_list,
                    default_classes=default_class,
                    worker_volume_present=worker_volume_present,
                    worker_volumes=worker_volumes_list,
                    proxy_enabled=is_proxy_enabled.lower(),
                    http_proxy=http_proxy,
                    https_proxy=https_proxy,
                    no_proxy_list=no_proxy_list,
                    additional_certs_present=additional_certs_present.lower(),
                    additional_certs=cert_list,
                ),
                Paths.CLUSTER_PATH + workload_name + "/tkgs_workload.yaml",
            )
            return file
        except Exception as e:
            current_app.logger.error(str(e))
            return None

    def create_secret_for_trusted_cert(self, workload_name, ns, cert_name, cert_data):
        """
        Create Secrets for Additional certs
        """
        try:
            clusterPath = Paths.CLUSTER_PATH
            file = os.path.join(clusterPath, workload_name, "cert-secret.yaml")
            command = ["rm", "-rf", file]
            runShellCommandAndReturnOutputAsList(command)

            meta_dict = dict(name=workload_name + "-user-trusted-ca-secret", namespace=ns)
            data_dict = {cert_name: cert_data}
            ytr = dict(apiVersion="v1", data=data_dict, kind="Secret", metadata=meta_dict, type="Opaque")
            with open(file, "w") as outfile:
                ryaml.dump(ytr, outfile, Dumper=ryaml.RoundTripDumper, indent=2)
            return file
        except Exception as e:
            current_app.logger.error("Failed to create secret manifest for additional certs")
            current_app.logger.error(str(e))
            return None

    def generate_yaml_file(self, workload_name):
        vcenter_8 = False
        vcenter_7 = False
        if verifyVcenterVersion("8"):
            vcenter_8 = True
            vcenter_7 = False
        elif verifyVcenterVersion("7"):
            vcenter_7 = True
            vcenter_8 = False

        cluster_kind = (
            self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereWorkloadClusterKind
        )
        if vcenter_8 and cluster_kind == EnvType.TKGS_CLUSTER_CLASS_KIND:
            current_app.logger.info("Workload cluster will be deployed with v1beta1 apiVersion")
            return self.generate_yaml_file_v1beta1()
        else:
            current_app.logger.info("Workload cluster will be deployed with v1alpha3 apiVersion")
            workload_name = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereWorkloadClusterName
            )
            clusterPath = Paths.CLUSTER_PATH
            file = os.path.join(clusterPath, workload_name, "tkgs_workload.yaml")
            command = ["rm", "-rf", file]
            runShellCommandAndReturnOutputAsList(command)
            name_space = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereNamespaceName
            )
            enable_ha = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.enableControlPlaneHa
            )
            if str(enable_ha).lower() == "true":
                count = "3"
            else:
                count = "1"
            control_plane_vm_class = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.controlPlaneVmClass
            )
            node_storage_class = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.nodeStorageClass
            )
            policy_id = self.vc_operation.get_policy_id(node_storage_class)
            if policy_id[0] is None:
                current_app.logger.error("Failed to get policy id")
                return None
            allowed_ = self.kubectl_util.get_alias_name(policy_id[0])
            if allowed_[0] is None:
                current_app.logger.error(allowed_[1])
                return None
            node_storage_class = str(allowed_[0])
            worker_node_count = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.workerNodeCount
            )
            worker_vm_class = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.workerVmClass
            )
            cluster_name = self.spec.envSpec.vcenterDetails.vcenterCluster
            if str(cluster_name).__contains__("/"):
                cluster_name = cluster_name[cluster_name.rindex("/") + 1 :]

            kube_version = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereWorkloadClusterVersion
            )
            if not kube_version.startswith("v"):
                kube_version = "v" + kube_version
            is_compatible = checkClusterVersionCompatibility(
                self.vCenter, self.vc_user, self.vc_password, cluster_name, kube_version
            )
            if is_compatible[0]:
                current_app.logger.info("Provided cluster version is valid !")
            else:
                return None
            tkr_name = get_tkr_name(kube_version, self.vCenter, self.vc_user, self.vc_password, cluster_name)
            if tkr_name[1] == 500:
                return None
            else:
                tkr_name = tkr_name[0]
            service_cidr = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.serviceCidrBlocks
            )
            pod_cidr = self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.podCidrBlocks
            allowed_clases = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.allowedStorageClasses
            )
            allowed = ""
            classes = allowed_clases
            for c in classes:
                policy_id = self.vc_operation.get_policy_id(c)
                if policy_id[0] is None:
                    current_app.logger.error("Failed to get policy id")
                    return None
                allowed_ = self.kubectl_util.get_alias_name(policy_id[0])
                if allowed_[0] is None:
                    current_app.logger.error(allowed_[1])
                    return None
                allowed += str(allowed_[0]) + ","
            if allowed is None:
                current_app.logger.error("Failed to get allowed classes")
                return None
            allowed = allowed.strip(",")
            li = convertStringToCommaSeperated(allowed)
            default_clases = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.defaultStorageClass
            )
            policy_id = self.vc_operation.get_policy_id(default_clases)
            if policy_id[0] is None:
                current_app.logger.error("Failed to get policy id")
                return None
            allowed_ = self.kubectl_util.get_alias_name(policy_id[0])
            if allowed_[0] is None:
                current_app.logger.error(allowed_[1])
                return None
            default_clases = str(allowed_[0])
            try:
                control_plane_volumes = (
                    self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.controlPlaneVolumes
                )
                control_plane_volumes_list = []
                for control_plane_volume in control_plane_volumes:
                    control_plane_volumes_list.append(
                        dict(
                            name=control_plane_volume["name"],
                            mountPath=control_plane_volume["mountPath"],
                            capacity=dict(storage=control_plane_volume["storage"]),
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
                    worker_volumes_list.append(
                        dict(
                            name=worker_volume["name"],
                            mountPath=worker_volume["mountPath"],
                            capacity=dict(storage=worker_volume["storage"]),
                        )
                    )
            except Exception:
                worker_vol = False

            if worker_vol and control_plane_vol:
                if vcenter_8:
                    topology_dict = {
                        "controlPlane": {
                            "replicas": 1,
                            "vmClass": control_plane_vm_class,
                            "storageClass": node_storage_class,
                            "tkr": {"reference": {"name": tkr_name}},
                            "volumes": control_plane_volumes_list,
                        },
                        "nodePools": [
                            {
                                "name": "test11",
                                "replicas": int(worker_node_count),
                                "vmClass": worker_vm_class,
                                "storageClass": node_storage_class,
                                "tkr": {"reference": {"name": tkr_name}},
                                "volumes": worker_volumes_list,
                            }
                        ],
                    }
                elif vcenter_7:
                    topology_dict = {
                        "controlPlane": {
                            "count": int(count),
                            "class": control_plane_vm_class,
                            "storageClass": node_storage_class,
                            "volumes": control_plane_volumes_list,
                        },
                        "workers": {
                            "count": int(worker_node_count),
                            "class": worker_vm_class,
                            "storageClass": node_storage_class,
                            "volumes": worker_volumes_list,
                        },
                    }
            elif control_plane_vol:
                if vcenter_8:
                    list_ = [
                        {
                            "name": "test10",
                            "replicas": int(worker_node_count),
                            "vmClass": worker_vm_class,
                            "storageClass": node_storage_class,
                        }
                    ]
                    topology_dict = {
                        "controlPlane": {
                            "replicas": int(count),
                            "vmClass": control_plane_vm_class,
                            "storageClass": node_storage_class,
                            "tkr": {"reference": {"name": tkr_name}},
                            "volumes": control_plane_volumes_list,
                        },
                        "nodePools": list_,
                    }
                elif vcenter_7:
                    topology_dict = {
                        "controlPlane": {
                            "count": int(count),
                            "class": control_plane_vm_class,
                            "storageClass": node_storage_class,
                            "volumes": control_plane_volumes_list,
                        },
                        "workers": {
                            "count": int(worker_node_count),
                            "class": worker_vm_class,
                            "storageClass": node_storage_class,
                        },
                    }
            elif worker_vol:
                if vcenter_8:
                    topology_dict = {
                        "controlPlane": {
                            "replicas": int(count),
                            "vmClass": control_plane_vm_class,
                            "storageClass": node_storage_class,
                            "tkr": {"reference": {"name": tkr_name}},
                        },
                        "nodePools": [
                            {
                                "name": "test9",
                                "replicas": int(worker_node_count),
                                "vmClass": worker_vm_class,
                                "storageClass": node_storage_class,
                                "tkr": {"reference": {"name": tkr_name}},
                                "volumes": worker_volumes_list,
                            }
                        ],
                    }
                elif vcenter_7:
                    topology_dict = {
                        "controlPlane": {
                            "count": int(count),
                            "class": control_plane_vm_class,
                            "storageClass": node_storage_class,
                        },
                        "workers": {
                            "count": int(worker_node_count),
                            "class": worker_vm_class,
                            "storageClass": node_storage_class,
                            "volumes": worker_volumes_list,
                        },
                    }
            else:
                if vcenter_8:
                    topology_dict = {
                        "controlPlane": {
                            "replicas": int(count),
                            "vmClass": control_plane_vm_class,
                            "tkr": {"reference": {"name": tkr_name}},
                            "storageClass": node_storage_class,
                        },
                        "nodePools": [
                            {
                                "name": "test12",
                                "replicas": int(worker_node_count),
                                "vmClass": worker_vm_class,
                                "storageClass": node_storage_class,
                                "tkr": {"reference": {"name": tkr_name}},
                            }
                        ],
                    }
                elif vcenter_7:
                    topology_dict = {
                        "controlPlane": {
                            "count": int(count),
                            "class": control_plane_vm_class,
                            "storageClass": node_storage_class,
                        },
                        "workers": {
                            "count": int(worker_node_count),
                            "class": worker_vm_class,
                            "storageClass": node_storage_class,
                        },
                    }
            meta_dict = {"name": workload_name, "namespace": name_space}
            try:
                cni = self.spec.tkgsComponentSpec.tkgServiceConfig.defaultCNI
                if cni:
                    defaultCNI = cni
                    isCni = True
                else:
                    defaultCNI = "antrea"
                    isCni = False
            except Exception:
                defaultCNI = "antrea"
                isCni = False
            if vcenter_8:
                spec_dict = {
                    "topology": topology_dict,
                    "settings": {
                        "storage": {"defaultClass": default_clases},
                        "network": {
                            "services": {"cidrBlocks": [service_cidr]},
                            "pods": {"cidrBlocks": [pod_cidr]},
                            "serviceDomain": "cluster.local",
                        },
                    },
                }
            elif vcenter_7:
                spec_dict = {
                    "topology": topology_dict,
                    "distribution": {"version": kube_version},
                    "settings": {
                        "network": {"services": {"cidrBlocks": [service_cidr]}, "pods": {"cidrBlocks": [pod_cidr]}},
                        "storage": {"classes": li, "defaultClass": default_clases},
                    },
                }
            if isCni:
                default = dict(cni=dict(name=defaultCNI))
                spec_dict["settings"]["network"].update(default)
            try:
                isProxyEnabled = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.enableProxy
                if str(isProxyEnabled).lower() == "true":
                    proxyEnabled = True
                else:
                    proxyEnabled = False
            except Exception:
                proxyEnabled = False
            if proxyEnabled:
                try:
                    httpProxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.httpProxy
                    httpsProxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.httpsProxy
                    noProxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.noProxy
                    list_ = convertStringToCommaSeperated(noProxy)
                except Exception as e:
                    return None, str(e)
                proxy = dict(proxy=dict(httpProxy=httpProxy, httpsProxy=httpsProxy, noProxy=list_))
                spec_dict["settings"]["network"].update(proxy)
                cert_list = []
                isProxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.proxyCert
                if isProxy:
                    cert = Path(isProxy).read_text()
                    string_bytes = cert.encode("ascii")
                    base64_bytes = base64.b64encode(string_bytes)
                    cert_base64 = base64_bytes.decode("ascii")
                    cert_list.append(dict(name="certProxy", data=cert_base64))
                proxyPath = self.spec.tkgsComponentSpec.tkgServiceConfig.additionalTrustedCAs.paths
                proxyEndpoints = self.spec.tkgsComponentSpec.tkgServiceConfig.additionalTrustedCAs.endpointUrls
                if proxyPath:
                    proxyCert = proxyPath
                    isProxyCert = True
                    isCaPath = True
                elif proxyEndpoints:
                    proxyCert = proxyEndpoints
                    isProxyCert = True
                    isCaPath = False
                else:
                    isProxyCert = False
                    isCaPath = False
                if isProxyCert:
                    count = 0
                    for certs in proxyCert:
                        count = count + 1
                        if isCaPath:
                            cert = Path(certs).read_text()
                            string_bytes = cert.encode("ascii")
                            base64_bytes = base64.b64encode(string_bytes)
                            cert_base64 = base64_bytes.decode("ascii")
                        else:
                            getBase64CertWriteToFile(certs, "443")
                            with open("cert.txt", "r") as file2:
                                cert_base64 = file2.readline()
                        cert_list.append(dict(name="cert" + str(count), data=cert_base64))
                trust = dict(trust=dict(additionalTrustedCAs=cert_list))
                spec_dict["settings"]["network"].update(trust)
            if vcenter_8:
                app_version = "run.tanzu.vmware.com/v1alpha3"
            elif vcenter_7:
                app_version = "run.tanzu.vmware.com/v1alpha1"
            ytr = dict(apiVersion=app_version, kind="TanzuKubernetesCluster", metadata=meta_dict, spec=spec_dict)
            with open(file, "w") as outfile:
                ryaml.dump(ytr, outfile, Dumper=ryaml.RoundTripDumper, indent=2)
            return file

    def create_name_space(self, vcenter_ip, vcenter_username, password):
        try:
            sess = requests.request(
                "POST",
                "https://" + str(vcenter_ip) + "/rest/com/vmware/cis/session",
                auth=(vcenter_username, password),
                verify=False,
            )
            if sess.status_code != HTTPStatus.OK:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to fetch session ID for vCenter - " + vcenter_ip,
                    "STATUS_CODE": HTTPStatus.INTERNAL_SERVER_ERROR,
                }
                return jsonify(d), HTTPStatus.INTERNAL_SERVER_ERROR
            else:
                vc_session = sess.json()["value"]

            header = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "vmware-api-session-id": vc_session,
            }
            name_space = self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereNamespaceName
            url = "https://" + str(vcenter_ip) + "/api/vcenter/namespaces/instances"
            cluster_name = self.spec.envSpec.vcenterDetails.vcenterCluster
            if str(cluster_name).__contains__("/"):
                cluster_name = cluster_name[cluster_name.rindex("/") + 1 :]
            id = self.tkgs_util.get_cluster_id(cluster_name)
            if id[1] != HTTPStatus.OK:
                return None, id[0]
            status = self.check_name_space_running_status(url, header, name_space, id[0])
            if status[0] is None:
                if status[1] == "NOT_FOUND":
                    pass
                elif status[1] == "NOT_FOUND_INITIAL":
                    pass
                elif status[1] == "NOT_RUNNING":
                    return None, "Name is already created but not in running state"
            if status[0] == "SUCCESS":
                return "SUCCESS", name_space + " already created"
            try:
                cpu_limit = (
                    self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereNamespaceResourceSpec.cpuLimit
                )
            except Exception:
                cpu_limit = ""
                current_app.logger.info("CPU Limit is not provided, will continue without setting Custom CPU Limit")
            try:
                memory_limit = (
                    self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereNamespaceResourceSpec.memoryLimit
                )
            except Exception:
                memory_limit = ""
                current_app.logger.info(
                    "Memory Limit is not provided, will continue without setting Custom Memory Limit"
                )
            try:
                storage_limit = (
                    self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereNamespaceResourceSpec.storageRequestLimit
                )
            except Exception:
                storage_limit = ""
                current_app.logger.info(
                    "Storage Request Limit is not provided,"
                    " will continue without setting Custom "
                    "Storage Request Limit"
                )
            content_library = self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereNamespaceContentLibrary
            resource_spec = getBodyResourceSpec(cpu_limit, memory_limit, storage_limit)
            if not content_library:
                content_library = ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY
            lib = self.govc_operation.get_library_id(content_library)
            if lib is None:
                return None, "Failed to get content library id " + content_library
            name_space_vm_classes = self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereNamespaceVmClasses
            storage_specs = self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereNamespaceStorageSpec
            list_storage = []
            for storage_spec in storage_specs:
                policy = storage_spec["storagePolicy"]
                policy_id = self.vc_operation.get_policy_id(policy)
                if policy_id[0] is None:
                    current_app.logger.error("Failed to get policy id")
                    return None, policy_id[1]
                if "storageLimit" in storage_spec:
                    if not storage_spec["storageLimit"]:
                        list_storage.append(dict(policy=policy_id[0]))
                    else:
                        list_storage.append(dict(limit=storage_spec["storageLimit"], policy=policy_id[0]))
                else:
                    list_storage.append(dict(policy=policy_id[0]))
            workload_network = self.spec.tkgsComponentSpec.tkgsWorkloadNetwork.tkgsWorkloadNetworkName
            network_status = self.checkWorkloadNetwork(vcenter_ip, vcenter_username, password, id[0], workload_network)
            if network_status[1] and network_status[0] == "SUCCESS":
                current_app.logger.info("Workload network is already created - " + workload_network)
                current_app.logger.info("Using " + workload_network + " network for creating namespace " + name_space)
            elif network_status[0] == "NOT_CREATED":
                create_status = self.create_workload_network(
                    vcenter_ip, vcenter_username, password, id[0], workload_network
                )
                if create_status[0] == "SUCCESS":
                    current_app.logger.info("Workload network created successfully - " + workload_network)
                else:
                    current_app.logger.error("Failed to create workload network - " + workload_network)
                    return None, create_status[1]
            else:
                return None, network_status[0]

            body = {
                "cluster": id[0],
                "description": "name space",
                "namespace": name_space,
                "networks": [workload_network],
                "resource_spec": resource_spec,
                "storage_specs": list_storage,
                "vm_service_spec": {"content_libraries": [lib], "vm_classes": name_space_vm_classes},
            }
            json_object = json.dumps(body, indent=4)
            url = "https://" + str(vcenter_ip) + "/api/vcenter/namespaces/instances"
            response_csrf = RequestApiUtil.exec_req("POST", url, headers=header, data=json_object, verify=False)
            if response_csrf.status_code != 204:
                return None, "Failed to create name-space " + response_csrf.text
            count = 0
            while count < 30:
                status = self.check_name_space_running_status(url, header, name_space, id[0])
                if status[0] == "SUCCESS":
                    break
                current_app.logger.info("Waited for " + str(count * 10) + "s, retrying")
                count = count + 1
                time.sleep(10)
            return "SUCCESS", "CREATED"
        except Exception as e:
            return None, str(e)

    def create_workload_network(self, vCenter, vc_user, password, cluster_id, network_name):
        worker_cidr = self.spec.tkgsComponentSpec.tkgsWorkloadNetwork.tkgsWorkloadNetworkGatewayCidr
        start = self.spec.tkgsComponentSpec.tkgsWorkloadNetwork.tkgsWorkloadNetworkStartRange
        end = self.spec.tkgsComponentSpec.tkgsWorkloadNetwork.tkgsWorkloadNetworkEndRange
        port_group_name = self.spec.tkgsComponentSpec.tkgsWorkloadNetwork.tkgsWorkloadPortgroupName
        datacenter = self.spec.envSpec.vcenterDetails.vcenterDatacenter
        if str(datacenter).__contains__("/"):
            datacenter = datacenter[datacenter.rindex("/") + 1 :]
        if not (worker_cidr or start or end or port_group_name):
            return None, "Details to create workload network are not provided - " + network_name
        ip_cidr = seperateNetmaskAndIp(worker_cidr)
        count_of_ip = getCountOfIpAdress(worker_cidr, start, end)
        worker_network_id = getDvPortGroupId(vCenter, vc_user, password, port_group_name, datacenter)

        sess = requests.request(
            "POST", "https://" + str(vCenter) + "/rest/com/vmware/cis/session", auth=(vc_user, password), verify=False
        )
        if sess.status_code != HTTPStatus.OK:
            current_app.logger.error("Connection to vCenter failed")
            return None, "Connection to vCenter failed"
        else:
            vc_session = sess.json()["value"]

        header = {"Accept": "application/json", "Content-Type": "application/json", "vmware-api-session-id": vc_session}

        body = {
            "network": network_name,
            "network_provider": "VSPHERE_NETWORK",
            "vsphere_network": {
                "address_ranges": [{"address": start, "count": count_of_ip}],
                "gateway": ip_cidr[0],
                "ip_assignment_mode": "STATICRANGE",
                "portgroup": worker_network_id,
                "subnet_mask": cidr_to_netmask(worker_cidr),
            },
        }

        json_object = json.dumps(body, indent=4)
        url1 = "https://" + vCenter + "/api/vcenter/namespace-management/clusters/" + cluster_id + "/networks"
        create_response = RequestApiUtil.exec_req("POST", url1, headers=header, data=json_object, verify=False)
        if create_response.status_code == 204:
            return "SUCCESS", "Workload network created successfully"
        else:
            return None, create_response.txt

    def checkWorkloadNetwork(self, vcenter_ip, vc_user, password, cluster_id, workload_network):
        sess = requests.request(
            "POST",
            "https://" + str(vcenter_ip) + "/rest/com/vmware/cis/session",
            auth=(vc_user, password),
            verify=False,
        )
        if sess.status_code != HTTPStatus.OK:
            current_app.logger.error("Connection to vCenter failed")
            return "Connection to vCenter failed", False
        else:
            vc_session = sess.json()["value"]
        header = {"Accept": "application/json", "Content-Type": "application/json", "vmware-api-session-id": vc_session}

        url = "https://" + vcenter_ip + "/api/vcenter/namespace-management/clusters/" + cluster_id + "/networks"
        response_networks = RequestApiUtil.exec_req("GET", url, headers=header, verify=False)
        if response_networks.status_code != HTTPStatus.OK:
            return "Failed to fetch workload networks for given cluster", False

        for network in response_networks.json():
            if network["network"] == workload_network:
                return "SUCCESS", True
        else:
            return "NOT_CREATED", False

    def check_name_space_running_status(self, url, header, name_space, cluster_id):
        response_csrf = RequestApiUtil.exec_req("GET", url, headers=header, verify=False)
        if response_csrf.status_code != HTTPStatus.OK:
            return None, "Failed to get namespace list " + str(response_csrf.text)
        found = False
        if len(response_csrf.json()) < 1:
            current_app.logger.info("No namespace is created")
            return None, "NOT_FOUND_INITIAL"
        else:
            for name in response_csrf.json():
                if name["cluster"] == cluster_id:
                    if name["namespace"] == name_space:
                        found = True
                        break
        if found:
            running = False
            current_app.logger.info(name_space + " namespace  is already created")
            current_app.logger.info("Checking Running status")
            for name in response_csrf.json():
                if name["cluster"] == cluster_id:
                    if name["namespace"] == name_space:
                        if name["config_status"] == "RUNNING":
                            running = True
                            break
            if running:
                current_app.logger.info(name_space + " namespace  is running")
                return "SUCCESS", "RUNNING"
            else:
                current_app.logger.info(name_space + " namespace  is not running")
                return None, "NOT_RUNNING"
        else:
            return None, "NOT_FOUND"

    def attach_proxy_tkgs_workload_to_tmc(self):
        proxyEnabled = False
        try:
            isProxyEnabled = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.enableProxy
            if str(isProxyEnabled).lower() == "true":
                proxyEnabled = True
            else:
                proxyEnabled = False
        except Exception:
            proxyEnabled = False
        if proxyEnabled:
            proxy_name = Tkgs_Extension_Details.TKGS_PROXY_CREDENTIAL_NAME
            try:
                name_space = (
                    self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereNamespaceName
                )

                workload_name = (
                    self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereWorkloadClusterName
                )
                tmc_url = self.spec.envSpec.saasEndpoints.tmcDetails.tmcInstanceURL
                current_app.logger.info("Getting health information of cluster " + workload_name)
                mgmt = self.spec.envSpec.saasEndpoints.tmcDetails.tmcSupervisorClusterName
                url = (
                    tmc_url
                    + "/v1alpha1/managementclusters/"
                    + mgmt
                    + "/provisioners/"
                    + name_space
                    + "/tanzukubernetesclusters"
                )
                refreshToken = self.spec.envSpec.saasEndpoints.tmcDetails.tmcRefreshToken

                url = Csp.AUTH_URL_REFRESH_TOKEN_URL.format(ref_token=refreshToken)
                headers = {}
                payload = {}
                response_login = RequestApiUtil.exec_req("POST", url, headers=headers, data=payload, verify=False)
                if response_login.status_code != HTTPStatus.OK:
                    return "login failed using provided TMC refresh token", HTTPStatus.INTERNAL_SERVER_ERROR

                access_token = response_login.json()["access_token"]

                header = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": access_token,
                }
                url = (
                    tmc_url
                    + "/v1alpha1/managementclusters/"
                    + mgmt
                    + "/provisioners/"
                    + name_space
                    + "/tanzukubernetesclusters"
                )
                response_clusters = RequestApiUtil.exec_req("GET", url, headers=header, verify=False)
                if response_clusters.status_code != HTTPStatus.OK:
                    current_app.logger.error(response_clusters.text)
                    return None, str(response_clusters.text)
                isClusterReady = False
                for cluster in response_clusters.json()["tanzuKubernetesClusters"]:
                    cluster_name = cluster["fullName"]["name"]
                    if cluster_name == workload_name:
                        phase = cluster["status"]["phase"]
                        status = cluster["status"]["conditions"]["Ready"]["status"]
                        if phase == "READY" and status == "TRUE":
                            current_app.logger.info("Checking if proxy is enabled on cluster " + workload_name)
                            try:
                                proxyName = cluster["spec"]["proxyName"]
                                if proxyName == proxy_name:
                                    return "Success", "Proxy is already configured for cluster " + workload_name
                            except Exception:
                                pass
                            isClusterReady = True
                            break
                        else:
                            return None, workload_name + " is not in ready state phase " + phase + " status " + status
                if isClusterReady:
                    current_app.logger.info("Configuring proxy in workload cluster " + workload_name)
                    clusterGroup = (
                        self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsWorkloadClusterGroupName
                    )
                    if not clusterGroup:
                        clusterGroup = "default"
                    body = {
                        "patch": [
                            {"op": "replace", "path": "/spec/tmcManaged", "value": True},
                            {"op": "replace", "path": "/spec/clusterGroupName", "value": clusterGroup},
                            {"op": "replace", "path": "/spec/proxyName", "value": proxy_name},
                        ]
                    }
                    json_object = json.dumps(body, indent=4)
                    response_clusters = RequestApiUtil.exec_req(
                        "PATCH", url, headers=header, data=json_object, verify=False
                    )
                    if response_clusters.status_code != HTTPStatus.OK:
                        return None, str(response_clusters.text)
                    isConfigured = False
                    for cluster in response_clusters.json()["tanzuKubernetesClusters"]:
                        cluster_name = cluster["fullName"]["name"]
                        if cluster_name == workload_name:
                            phase = cluster["status"]["phase"]
                            status = cluster["status"]["conditions"]["Ready"]["status"]
                            if phase == "READY" and status == "TRUE":
                                current_app.logger.info("Checking if proxy is enabled on cluster " + workload_name)
                                try:
                                    proxyName = cluster["spec"]["proxyName"]
                                    proxy_name = "sivt-tkgs-proxy"
                                    if proxyName == proxy_name:
                                        isConfigured = True
                                        return (
                                            "Success",
                                            "Proxy is successfully configured for cluster " + workload_name,
                                        )
                                except Exception as e:
                                    return (
                                        None,
                                        "Failed to configure proxy on workload " + workload_name + " due to " + str(e),
                                    )
                    if not isConfigured:
                        return (
                            None,
                            "Failed to configure proxy  on workload " + workload_name + " failed to find proxy name",
                        )
            except Exception as e:
                current_app.logger.error(str(e))
                return None, str(e)
        else:
            return "Success", "Proxy for tkgs is not enabled"


@vsphere_tkgs_workload_cluster.route("/api/tanzu/vsphere/workload/createnamespace", methods=["POST"])
def create_name_space():
    spec_json = request.get_json(force=True)
    spec: VsphereTkgsNameSpaceMasterSpec = VsphereTkgsNameSpaceMasterSpec.parse_obj(spec_json)
    workload_cluster = TkgsWorkloadCluster(spec)
    password = current_app.config["VC_PASSWORD"]
    vcenter_username = current_app.config["VC_USER"]
    vcenter_ip = current_app.config["VC_IP"]
    name_space = workload_cluster.create_name_space(vcenter_ip, vcenter_username, password)
    if name_space[0] is None:
        current_app.logger.error("Failed to create namespace " + str(name_space[1]))
        d = {"responseType": "ERROR", "msg": "Failed to create namespace " + str(name_space[1]), "STATUS_CODE": 500}
        return jsonify(d), 500
    current_app.logger.info("Successfully created namespace")
    d = {"responseType": "SUCCESS", "msg": "Successfully created namespace", "STATUS_CODE": 200}
    return jsonify(d), 200


@vsphere_tkgs_workload_cluster.route("/api/tanzu/vsphere/workload/createworkload", methods=["POST"])
def create_workload():
    spec_json = request.get_json(force=True)
    spec: VsphereTkgsNameSpaceMasterSpec = VsphereTkgsNameSpaceMasterSpec.parse_obj(spec_json)
    workload_cluster = TkgsWorkloadCluster(spec)
    tkgs_util = TkgsUtil(spec)
    pre = preChecks()
    if pre[1] != HTTPStatus.OK:
        current_app.logger.error(pre[0].json["msg"])
        response = RequestApiUtil.create_json_object(pre[0].json["msg"], "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR)
        return response, HTTPStatus.INTERNAL_SERVER_ERROR
    env = envCheck()
    if env[1] != HTTPStatus.OK:
        current_app.logger.error("Wrong env provided " + env[0])
        response = RequestApiUtil.create_json_object("Wrong env provided ", "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR)
        return response, HTTPStatus.INTERNAL_SERVER_ERROR
    env = env[0]
    saas_util: SaaSUtil = SaaSUtil(env, spec)
    TanzuUtil(env=env, spec=spec)
    password = current_app.config["VC_PASSWORD"]
    vcenter_username = current_app.config["VC_USER"]
    vcenter_ip = current_app.config["VC_IP"]

    command = ["tanzu", "plugin", "install", "--group", "vmware-tkg/default:v2.3.0"]
    listOfCmd = ["tanzu", "config", "eula", "accept"]
    runProcess(listOfCmd)
    runShellCommandAndReturnOutputAsList(command)

    name_space = workload_cluster.create_tkg_workload_cluster(env, saas_util)
    if name_space[0] is None:
        current_app.logger.error("Failed to create workload cluster " + str(name_space[1]))
        response = RequestApiUtil.create_json_object(
            "Failed to create workload cluster " + str(name_space[0]), "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
        )
        return response, HTTPStatus.INTERNAL_SERVER_ERROR
    current_app.logger.info("Successfully created workload cluster")
    if saas_util.check_tmc_enabled():
        current_app.logger.info("Initiating TKGs SAAS integration")
        size = spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.workerNodeCount
        workload_cluster_name = (
            spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereWorkloadClusterName
        )
        if saas_util.check_to_enabled():
            to = saas_util.register_tanzu_observability(workload_cluster_name, size)
            if to[1] != HTTPStatus.OK:
                current_app.logger.error(to[0])
                response = RequestApiUtil.create_json_object(
                    "TO " "registration failed for workload cluster", "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR
        else:
            current_app.logger.info("Tanzu Observability not enabled")
        if saas_util.check_tsm_enabled():
            cluster_version = (
                spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereWorkloadClusterVersion
            )
            version_ = "v1.18.19+vmware.1"
            if not cluster_version.startswith("v"):
                cluster_version = "v" + cluster_version
            if not cluster_version.startswith(version_):
                current_app.logger.warn(
                    "On vSphere with Tanzu platform, TSM supports the Kubernetes version " + version_
                )
                warn_msg = "For latest updates please check - "
                "https://docs.vmware.com/en/VMware-Tanzu-Service-Mesh/services/\
                tanzu-service-mesh-environment-requirements-and-supported-platforms/\
                    GUID-D0B939BE-474E-4075-9A65-3D72B5B9F237.html"
                current_app.logger.warn(warn_msg)
            tsm = saas_util.register_tsm(workload_cluster_name, size)
            if tsm[1] != HTTPStatus.OK:
                current_app.logger.error("TSM registration failed for workload cluster")
                response = RequestApiUtil.create_json_object(
                    "TSM " "registration failed for workload cluster", "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR
        else:
            current_app.logger.info("TSM not enabled")

        if checkDataProtectionEnabled(Env.VSPHERE, "workload"):
            supervisor_cluster = spec.envSpec.saasEndpoints.tmcDetails.tmcSupervisorClusterName
            is_enabled = enable_data_protection(env, workload_cluster_name, supervisor_cluster)
            if not is_enabled[0]:
                current_app.logger.error(is_enabled[1])
                response = RequestApiUtil.create_json_object(is_enabled[1], "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR)
                return response, HTTPStatus.INTERNAL_SERVER_ERROR
            current_app.logger.info(is_enabled[1])
        else:
            current_app.logger.info("Data Protection is not enabled for cluster " + workload_cluster_name)
    else:
        current_app.logger.info("TMC not enabled.")
        current_app.logger.info("Check whether data protection is to be enabled via Velero on Workload Cluster")
        if checkDataProtectionEnabledVelero(env, "workload"):
            url_ = "https://" + vcenter_ip + "/"
            sess = requests.request(
                "POST", url_ + "rest/com/vmware/cis/session", auth=(vcenter_username, password), verify=False
            )
            if sess.status_code != HTTPStatus.OK:
                response = RequestApiUtil.create_json_object(
                    "Failed to fetch session ID for vCenter - " + vcenter_ip, "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR
            else:
                session_id = sess.json()["value"]
            header = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "vmware-api-session-id": session_id,
            }
            cluster_name = spec.envSpec.vcenterDetails.vcenterCluster
            if str(cluster_name).__contains__("/"):
                cluster_name = cluster_name[cluster_name.rindex("/") + 1 :]
            id = tkgs_util.get_cluster_id(cluster_name)
            if id[1] != HTTPStatus.OK:
                return None, id[0]
            clusterip_resp = RequestApiUtil.exec_req(
                "GET", url_ + "api/vcenter/namespace-management/clusters/" + str(id[0]), verify=False, headers=header
            )
            if clusterip_resp.status_code != HTTPStatus.OK:
                response = RequestApiUtil.create_json_object(
                    "Failed to fetch API server cluster endpoint - " + vcenter_ip,
                    "ERROR",
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR
            cluster_endpoint = clusterip_resp.json()["api_server_cluster_endpoint"]
            workload_cluster_name = (
                spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereWorkloadClusterName
            )
            name_space = (
                spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereNamespaceName
            )
            switch_context_workload = [
                "kubectl",
                "vsphere",
                "login",
                "--server",
                cluster_endpoint,
                "--vsphere-username",
                vcenter_username,
                "--tanzu-kubernetes-cluster-name",
                workload_cluster_name,
                "--tanzu-kubernetes-cluster-namespace",
                name_space,
                "--insecure-skip-tls-verify",
            ]
            switch_context = runShellCommandAndReturnOutputAsList(switch_context_workload)
            if switch_context[1] != 0:
                current_app.logger.error("Failed to switch to context " + str(switch_context[0]))
                response = RequestApiUtil.create_json_object(
                    "Failed to switch  to context " + str(switch_context[0]), "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR
            current_app.logger.info("Switched to " + workload_cluster_name + " context")
            is_enabled = enable_data_protection_velero("workload", env)
            if not is_enabled[0]:
                current_app.logger.error("Failed to enable data protection via velero on Workload Cluster")
                current_app.logger.error(is_enabled[1])
                response = RequestApiUtil.create_json_object(is_enabled[1], "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR)
                return response, HTTPStatus.INTERNAL_SERVER_ERROR
            current_app.logger.info("Successfully enabled data protection via Velero on Workload Cluster")
            current_app.logger.info(is_enabled[1])
        else:
            current_app.logger.info("Data protection via Velero setting is not active for Workload Cluster")
    response = RequestApiUtil.create_json_object("Successfully created workload cluster", "SUCCESS", HTTPStatus.OK)
    return response, HTTPStatus.OK
