# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import base64
import os
import time
from pathlib import Path

import requests
import ruamel
from flask import Blueprint, current_app, jsonify, request
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from tqdm import tqdm

from common.common_utilities import (
    checkAirGappedIsEnabled,
    checkAviL7EnabledForShared,
    checkDataProtectionEnabled,
    checkDataProtectionEnabledVelero,
    checkEnableIdentityManagement,
    createClusterFolder,
    createOverlayYaml,
    createRbacUsers,
    downloadAndPushKubernetesOvaMarketPlace,
    enable_data_protection,
    enable_data_protection_velero,
    envCheck,
    get_avi_version,
    installCertManagerAndContour,
    obtain_second_csrf,
    ping_test,
    preChecks,
    waitForGrepProcessWithoutChangeDir,
)
from common.lib.govc_client import GovcClient
from common.model.vmcSpec import VmcMasterSpec
from common.operation.constants import (
    PLAN,
    AkoType,
    AppName,
    Cloud,
    ControllerLocation,
    Env,
    KubernetesOva,
    Paths,
    RegexPattern,
    Repo,
    ResourcePoolAndFolderName,
    SegmentsName,
    Sizing,
    Type,
)
from common.operation.ShellHelper import (
    grabKubectlCommand,
    grabPipeOutput,
    runProcess,
    runShellCommandAndReturnOutput,
    runShellCommandAndReturnOutputAsList,
    verifyPodsAreRunning,
)
from common.operation.vcenter_operations import create_folder, createResourcePool
from common.prechecks.list_reources import validateKubeVersion
from common.util.common_utils import CommonUtils
from common.util.kubectl_util import KubectlUtil
from common.util.local_cmd_helper import LocalCmdHelper
from common.util.saas_util import SaaSUtil
from common.util.tanzu_util import TanzuUtil

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

shared_config = Blueprint("shared_config", __name__, static_folder="sharedConfig")


def akoDeploymentConfigSharedCluster(shared_cluster_name):
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {"responseType": "ERROR", "msg": "Wrong env provided " + env[0], "STATUS_CODE": 500}
        return jsonify(d), 500
    env = env[0]
    management_cluster = request.get_json(force=True)["componentSpec"]["tkgMgmtSpec"]["tkgMgmtClusterName"]
    commands = ["tanzu", "management-cluster", "kubeconfig", "get", management_cluster, "--admin"]

    kubeContextCommand = grabKubectlCommand(commands, RegexPattern.SWITCH_CONTEXT_KUBECTL)
    if kubeContextCommand is None:
        current_app.logger.error("Failed to get switch to management cluster context command")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get switch to management cluster context command",
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500

    lisOfSwitchContextCommand = str(kubeContextCommand).split(" ")
    status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand)
    if status[1] != 0:
        current_app.logger.error("Failed to get switch to management cluster context " + str(status[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get switch to management cluster context " + str(status[0]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500

    podRunninng_ako_main = ["kubectl", "get", "pods", "-A"]
    podRunninng_ako_grep = ["grep", AppName.AKO]
    time.sleep(30)
    timer = 30
    ako_pod_running = False
    while timer < 600:
        current_app.logger.info("Checking if AKO pods are running. Waited for " + str(timer) + "s retrying")
        command_status_ako = grabPipeOutput(podRunninng_ako_main, podRunninng_ako_grep)
        if command_status_ako[1] != 0:
            time.sleep(30)
            timer = timer + 30
        else:
            ako_pod_running = True
            break

    if not ako_pod_running:
        current_app.logger.error("AKO pods are not running on waiting for 10m " + command_status_ako[0])
        d = {
            "responseType": "ERROR",
            "msg": "AKO pods are not running on waiting for 10m " + str(command_status_ako[0]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    data_center = current_app.config["VC_DATACENTER"]
    govc_client = GovcClient(current_app.config, LocalCmdHelper())
    ip = govc_client.get_vm_ip(ControllerLocation.CONTROLLER_NAME, datacenter_name=data_center)
    if ip is None:
        current_app.logger.error("Failed to get IP of AVI controller")
        d = {"responseType": "ERROR", "msg": "Failed to get ip of avi controller", "STATUS_CODE": 500}
        return jsonify(d), 500
    ip = ip[0]
    current_app.logger.info(
        "Checking if AKO Deployment Config already exists for Shared services cluster: " + shared_cluster_name
    )
    command_main = ["kubectl", "get", "adc"]
    command_grep = ["grep", "install-ako-for-shared-services-cluster"]
    command_status_adc = grabPipeOutput(command_main, command_grep)
    if command_status_adc[1] == 0:
        current_app.logger.debug(
            "Found an already existing AKO Deployment Config: " "install-ako-for-shared-services-cluster"
        )
        command = ["kubectl", "delete", "adc", "install-ako-for-shared-services-cluster"]
        status = runShellCommandAndReturnOutputAsList(command)
        if status[1] != 0:
            current_app.logger.error("Failed to delete an already present AKO Deployment config")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to delete an already present AKO Deployment config",
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
    # MGMT DATA
    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        current_app.logger.error("Failed to get csrf from new password")
        d = {"responseType": "ERROR", "msg": "Failed to get csrf from new password", "STATUS_CODE": 500}
        return jsonify(d), 500
    aviVersion = get_avi_version(env)
    tkg_mgmt_data_netmask = getVipNetworkIpNetMask(ip, csrf2, aviVersion, Cloud.WIP_NETWORK_NAME)
    if tkg_mgmt_data_netmask[0] is None or tkg_mgmt_data_netmask[0] == "NOT_FOUND":
        current_app.logger.error("Failed to get TKG Management Data netmask")
        d = {"responseType": "ERROR", "msg": "Failed to get TKG Management Data netmask", "STATUS_CODE": 500}
        return jsonify(d), 500
    tkg_cluster_vip_netmask = getVipNetworkIpNetMask(ip, csrf2, aviVersion, Cloud.WIP_CLUSTER_NETWORK_NAME)
    if tkg_cluster_vip_netmask[0] is None or tkg_cluster_vip_netmask[0] == "NOT_FOUND":
        current_app.logger.error("Failed to get Cluster VIP netmask")
        d = {"responseType": "ERROR", "msg": "Failed to get Cluster VIP netmask", "STATUS_CODE": 500}
        return jsonify(d), 500
    current_app.logger.info("Creating AkoDeploymentConfig for shared services cluster...")
    createAkoFile(
        ip,
        shared_cluster_name,
        tkg_mgmt_data_netmask[0],
        Cloud.WIP_NETWORK_NAME,
        tkg_cluster_vip_netmask[0],
        Cloud.WIP_CLUSTER_NETWORK_NAME,
        SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment,
    )
    shared_cluster_path = Paths.CLUSTER_PATH + shared_cluster_name
    yaml_file_path = shared_cluster_path + "/tkgvmc-ako-shared-services-cluster.yaml"
    listOfCommand = ["kubectl", "create", "-f", yaml_file_path]
    status = runShellCommandAndReturnOutputAsList(listOfCommand)
    if status[1] != 0:
        if not str(status[0]).__contains__("already has a value"):
            current_app.logger.error("Failed to create new AkoDeploymentConfig" + str(status[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create new AkoDeploymentConfig " + str(status[0]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
    current_app.logger.info("Successfully created a new AkoDeploymentConfig for shared services cluster")
    d = {"responseType": "SUCCESS", "msg": "Successfully validated running status for AKO", "STATUS_CODE": 200}
    return jsonify(d), 200


def createAkoFile(
    ip, shared_cluster_name, tkgMgmtDataVipCidr, tkgMgmtDataPg, tkgClusterVipCidr, tkgClusterVipPg, sharedNetworkName
):
    sharedNetworkName = dict(networkName=sharedNetworkName)
    lis_ = [sharedNetworkName]
    if checkAviL7EnabledForShared(Env.VMC):
        extra_config = dict(
            cniPlugin="antrea",
            disableStaticRouteSync=True,
            ingress=dict(
                disableIngressClass=False,
                defaultIngressController=False,
                nodeNetworkList=lis_,
                serviceType="NodePortLocal",
                shardVSSize="MEDIUM",
            ),
        )
    else:
        extra_config = dict(
            cniPlugin="antrea",
            disableStaticRouteSync=True,
            ingress=dict(disableIngressClass=True, defaultIngressController=False, nodeNetworkList=lis_),
        )
    data = dict(
        apiVersion="networking.tkg.tanzu.vmware.com/v1alpha1",
        kind="AKODeploymentConfig",
        metadata=dict(
            finalizers=["ako-operator.networking.tkg.tanzu.vmware.com"],
            generation=2,
            name="install-ako-for-shared-services-cluster",
        ),
        spec=dict(
            adminCredentialRef=dict(name="avi-controller-credentials", namespace="tkg-system-networking"),
            certificateAuthorityRef=dict(name="avi-controller-ca", namespace="tkg-system-networking"),
            cloudName=Cloud.CLOUD_NAME,
            clusterSelector=dict(matchLabels=dict(type=AkoType.SHARED_CLUSTER_SELECTOR)),
            controller=ip,
            controlPlaneNetwork=dict(cidr=tkgClusterVipCidr, name=tkgClusterVipPg),
            dataNetwork=dict(cidr=tkgMgmtDataVipCidr, name=tkgMgmtDataPg),
            extraConfigs=extra_config,
            serviceEngineGroup=Cloud.SE_GROUP_NAME,
        ),
    )
    shared_cluster_path = Paths.CLUSTER_PATH + shared_cluster_name
    with open(shared_cluster_path + "/tkgvmc-ako-shared-services-cluster.yaml", "w") as outfile:
        yaml = ruamel.yaml.YAML()
        yaml.indent(mapping=2, sequence=4, offset=3)
        yaml.dump(data, outfile)


def getVipNetworkIpNetMask(ip, csrf2, aviVersion, networkName):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    body = {}
    url = "https://" + ip + "/api/network"
    try:
        response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        else:
            for re in response_csrf.json()["results"]:
                if re["name"] == networkName:
                    for sub in re["configured_subnets"]:
                        return str(sub["prefix"]["ip_addr"]["addr"]) + "/" + str(sub["prefix"]["mask"]), "SUCCESS"
            else:
                next_url = None if not response_csrf.json()["next"] else response_csrf.json()["next"]
                while len(next_url) > 0:
                    response_csrf = requests.request("GET", next_url, headers=headers, data=body, verify=False)
                    for re in response_csrf.json()["results"]:
                        if re["name"] == networkName:
                            for sub in re["configured_subnets"]:
                                return (
                                    str(sub["prefix"]["ip_addr"]["addr"]) + "/" + str(sub["prefix"]["mask"]),
                                    "SUCCESS",
                                )
                    next_url = None if not response_csrf.json()["next"] else response_csrf.json()["next"]

        return "NOT_FOUND", "FAILED"
    except KeyError as e:
        current_app.logger.error("Exception occured" + str(e))
        return "NOT_FOUND", "FAILED"


@shared_config.route("/api/tanzu/vmc/tkgsharedsvc", methods=["POST"])
def configSharedCluster():
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {"responseType": "ERROR", "msg": "Wrong env provided " + env[0], "STATUS_CODE": 500}
        return jsonify(d), 500
    env = env[0]
    refreshToken = request.get_json(force=True)["marketplaceSpec"]["refreshToken"]
    if not checkAirGappedIsEnabled(env) and refreshToken != "":
        validateK8s = validateKubeVersion(env, "Shared")
        if validateK8s[1] != 200:
            current_app.logger.error(validateK8s[0].json["msg"])
            d = {"responseType": "ERROR", "msg": "Failed to validate KubeVersion", "STATUS_CODE": 500}
            return jsonify(d), 500
    deploy_shared = deploy()
    if deploy_shared[1] != 200:
        current_app.logger.error(deploy_shared[0].json["msg"])
        d = {
            "responseType": "ERROR",
            "msg": "Failed to Config shared cluster " + str(deploy_shared[0].json["msg"]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    deploy_extension = deployExtensions()
    if deploy_extension[1] != 200:
        current_app.logger.error(str(deploy_extension[0].json["msg"]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to deploy extensions " + str(deploy_extension[0].json["msg"]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    d = {"responseType": "SUCCESS", "msg": "Shared cluster configured Successfully", "STATUS_CODE": 200}
    current_app.logger.info("Shared cluster configured Successfully")
    return jsonify(d), 200


@shared_config.route("/api/tanzu/vmc/tkgsharedsvc/config", methods=["POST"])
def deploy():
    pre = preChecks()
    if pre[1] != 200:
        try:
            msg = pre[0].json["msg"]
        except Exception:
            msg = pre[0]
        current_app.logger.error(msg)
        d = {"responseType": "ERROR", "msg": msg, "STATUS_CODE": 500}
        return jsonify(d), 500
    kubectl_util = KubectlUtil()
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {"responseType": "ERROR", "msg": "Wrong env provided " + env[0], "STATUS_CODE": 500}
        return jsonify(d), 500
    env = env[0]
    json_dict = request.get_json(force=True)
    vmcSpec: VmcMasterSpec = VmcMasterSpec.parse_obj(json_dict)
    tanzu_util = TanzuUtil(env=env, spec=vmcSpec)
    saas_util: SaaSUtil = SaaSUtil(env, vmcSpec)
    password = current_app.config["VC_PASSWORD"]
    vcenter_username = current_app.config["VC_USER"]
    vcenter_ip = current_app.config["VC_IP"]
    cluster_name = current_app.config["VC_CLUSTER"]
    data_center = current_app.config["VC_DATACENTER"]
    data_store = current_app.config["VC_DATASTORE"]
    vsphere_password = password
    _base64_bytes = vsphere_password.encode("ascii")
    _enc_bytes = base64.b64encode(_base64_bytes)
    vsphere_password = _enc_bytes.decode("ascii")
    parent_resourcepool = current_app.config["RESOURCE_POOL"]
    refreshToken = request.get_json(force=True)["marketplaceSpec"]["refreshToken"]

    kubernetes_ova_os = request.get_json(force=True)["componentSpec"]["tkgSharedServiceSpec"]["tkgSharedserviceBaseOs"]
    kubernetes_ova_version = request.get_json(force=True)["componentSpec"]["tkgSharedServiceSpec"][
        "tkgSharedserviceKubeVersion"
    ]

    if refreshToken:
        current_app.logger.info("Kubernetes OVA configs for shared service cluster")
        down_status = downloadAndPushKubernetesOvaMarketPlace(env, kubernetes_ova_version, kubernetes_ova_os)
        if down_status[0] is None:
            current_app.logger.error(down_status[1])
            d = {"responseType": "ERROR", "msg": down_status[1], "STATUS_CODE": 500}
            return jsonify(d), 500
    else:
        current_app.logger.info("MarketPlace refresh token is not provided, skipping the download of kubernetes OVA")

    gateway_address = request.get_json(force=True)["componentSpec"]["tkgSharedServiceSpec"]["tkgSharedGatewayCidr"]
    if ping_test("ping -c 1 " + gateway_address.split("/")[0]) != 0:
        current_app.logger.warn(
            "Ping test failed for " + gateway_address + " gateway. It is Recommended to fix "
            "this before proceeding with deployment"
        )
        time.sleep(30)
    else:
        current_app.logger.info("Ping test passed for gateway - " + gateway_address)

    try:
        isCreated4 = createResourcePool(
            vcenter_ip,
            vcenter_username,
            password,
            cluster_name,
            ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME,
            parent_resourcepool,
            data_center,
        )
        if isCreated4 is not None:
            current_app.logger.info("Created resource pool " + ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME)
    except Exception as e:
        current_app.logger.error("Failed to create resource pool " + str(e))
        d = {"responseType": "ERROR", "msg": "Failed to create resource pool " + str(e), "STATUS_CODE": 500}
        return jsonify(d), 500
    try:
        isCreated1 = create_folder(
            vcenter_ip, vcenter_username, password, data_center, ResourcePoolAndFolderName.SHARED_FOLDER_NAME
        )
        if isCreated1 is not None:
            current_app.logger.info("Created folder " + ResourcePoolAndFolderName.SHARED_FOLDER_NAME)
    except Exception as e:
        current_app.logger.error("Failed to create folder " + str(e))
        d = {"responseType": "ERROR", "msg": "Failed to create folder " + str(e), "STATUS_CODE": 500}
        return jsonify(d), 500, str(e)
    management_cluster = vmcSpec.componentSpec.tkgMgmtSpec.tkgMgmtClusterName
    try:
        with open("/root/.ssh/id_rsa.pub", "r") as f:
            re = f.readline()
    except Exception as e:
        current_app.logger.error("Failed to get ssh key from config file " + str(e))
        d = {"responseType": "ERROR", "msg": "Failed to get ssh key from config file " + str(e), "STATUS_CODE": 500}
        return jsonify(d), 500
    podRunninng = ["tanzu", "cluster", "list"]
    command_status = runShellCommandAndReturnOutputAsList(podRunninng)
    if command_status[1] != 0:
        current_app.logger.error("Failed to run command to check status of pods")
        d = {"responseType": "ERROR", "msg": "Failed to run command to check status of pods", "STATUS_CODE": 500}
        return jsonify(d), 500
    shared_cluster_name = vmcSpec.componentSpec.tkgSharedServiceSpec.tkgSharedClusterName
    datacenter_path = "/" + data_center
    size = vmcSpec.componentSpec.tkgSharedServiceSpec.tkgSharedserviceSize
    if size.lower() == "small":
        current_app.logger.debug("Recommended size for shared services cluster is: medium/large/extra-large/custom")
    elif size.lower() == "medium":
        pass
    elif size.lower() == "large":
        pass
    elif size.lower() == "extra-large":
        pass
    elif size.lower() == "custom":
        pass
    else:
        current_app.logger.error(
            "Provided cluster size: "
            + size
            + "is not supported, please provide one of: small/medium/large/extra-large/custom"
        )
        d = {
            "responseType": "ERROR",
            "msg": "Provided cluster size: "
            + size
            + "is not supported, please provide one of: small/medium/large/extra-large/custom",
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    if size.lower() == "small":
        cpu = Sizing.small["CPU"]
        memory = Sizing.small["MEMORY"]
        disk = Sizing.small["DISK"]
    elif size.lower() == "medium":
        cpu = Sizing.medium["CPU"]
        memory = Sizing.medium["MEMORY"]
        disk = Sizing.medium["DISK"]
    elif size.lower() == "large":
        cpu = Sizing.large["CPU"]
        memory = Sizing.large["MEMORY"]
        disk = Sizing.large["DISK"]
    elif size.lower() == "extra-large":
        cpu = Sizing.extraLarge["CPU"]
        memory = Sizing.extraLarge["MEMORY"]
        disk = Sizing.extraLarge["DISK"]
    elif size.lower() == "custom":
        cpu = request.get_json(force=True)["componentSpec"]["tkgSharedServiceSpec"]["tkgSharedserviceCpuSize"]
        memory = request.get_json(force=True)["componentSpec"]["tkgSharedServiceSpec"]["tkgSharedserviceMemorySize"]
        disk = request.get_json(force=True)["componentSpec"]["tkgSharedServiceSpec"]["tkgSharedserviceStorageSize"]
        memory = str(int(memory) * 1024)
    else:
        current_app.logger.error(
            "Provided cluster size: "
            + size
            + "is not supported, please provide one of: small/medium/large/extra-large/custom"
        )
        d = {
            "responseType": "ERROR",
            "msg": "Provided cluster size: "
            + size
            + "is not supported, please provide one of: small/medium/large/extra-large/custom",
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    pod_cidr = request.get_json(force=True)["componentSpec"]["tkgSharedServiceSpec"]["tkgSharedserviceClusterCidr"]
    service_cidr = request.get_json(force=True)["componentSpec"]["tkgSharedServiceSpec"]["tkgSharedserviceServiceCidr"]
    machineCount = vmcSpec.componentSpec.tkgSharedServiceSpec.tkgSharedserviceWorkerMachineCount
    cluster_plan = vmcSpec.componentSpec.tkgSharedServiceSpec.tkgSharedserviceDeploymentType
    if cluster_plan.lower() == PLAN.PROD_PLAN:
        controlPlaneNodeCount = "3"
    else:
        controlPlaneNodeCount = "1"
    datastore_path = f"{datacenter_path}/datastore/{data_store}"
    shared_folder_path = f"{datacenter_path}/vm/{ResourcePoolAndFolderName.SHARED_FOLDER_NAME}"
    if parent_resourcepool:
        shared_resource_path = (
            f"{datacenter_path}/host/{cluster_name}"
            f"/Resources/{parent_resourcepool}/{ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME}"
        )
    else:
        shared_resource_path = (
            f"{datacenter_path}/host/{cluster_name}/Resources/{ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME}"
        )
    shared_network_path = f"{datacenter_path}/network/{SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment}"
    shared_cluster_path = Paths.CLUSTER_PATH + shared_cluster_name
    if not createClusterFolder(shared_cluster_name):
        d = {"responseType": "ERROR", "msg": "Failed to create directory: " + shared_cluster_path, "STATUS_CODE": 500}
        return jsonify(d), 500
    current_app.logger.info("The config files for shared services cluster will be located at: " + shared_cluster_path)
    commands = ["tanzu", "management-cluster", "kubeconfig", "get", management_cluster, "--admin"]
    kubeContextCommand = grabKubectlCommand(commands, RegexPattern.SWITCH_CONTEXT_KUBECTL)
    if kubeContextCommand is None:
        current_app.logger.error("Failed to get switch to management cluster context command")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get switch to management cluster context command",
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    lisOfSwitchContextCommand = str(kubeContextCommand).split(" ")
    status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand)
    if status[1] != 0:
        current_app.logger.error("Failed to get switch to management cluster context " + str(status[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get switch to management cluster context " + str(status[0]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    version_status = kubectl_util.get_kube_version_full_name(kubernetes_ova_version)
    if version_status[0] is None:
        current_app.logger.error("Kubernetes OVA Version is not found for Shared Service Cluster")
        d = {
            "responseType": "ERROR",
            "msg": "Kubernetes OVA Version is not found for Shared Service Cluster",
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    else:
        version = version_status[0]

    if saas_util.check_tmc_enabled():
        clusterGroup = request.get_json(force=True)["componentSpec"]["tkgSharedServiceSpec"][
            "tkgSharedserviceClusterGroupName"
        ]
    else:
        clusterGroup = "default"

    if not clusterGroup:
        clusterGroup = "default"
    if cluster_plan.lower() == PLAN.PROD_PLAN:
        createSharedCluster = [
            "tmc",
            "cluster",
            "create",
            "-t",
            "tkg-vsphere",
            "-n",
            shared_cluster_name,
            "-m",
            management_cluster,
            "-p",
            "default",
            "--cluster-group",
            clusterGroup,
            "--ssh-key",
            re,
            "--version",
            version,
            "--datacenter",
            datacenter_path,
            "--datastore",
            datastore_path,
            "--folder",
            shared_folder_path,
            "--resource-pool",
            shared_resource_path,
            "--workspace-network",
            shared_network_path,
            "--control-plane-cpu",
            cpu,
            "--control-plane-disk-gib",
            disk,
            "--control-plane-memory-mib",
            memory,
            "--worker-node-count",
            machineCount,
            "--worker-cpu",
            cpu,
            "--worker-disk-gib",
            disk,
            "--worker-memory-mib",
            memory,
            "--pods-cidr-blocks",
            pod_cidr,
            "--service-cidr-blocks",
            service_cidr,
            "--high-availability",
        ]
    else:
        createSharedCluster = [
            "tmc",
            "cluster",
            "create",
            "-t",
            "tkg-vsphere",
            "-n",
            shared_cluster_name,
            "-m",
            management_cluster,
            "-p",
            "default",
            "--cluster-group",
            clusterGroup,
            "--ssh-key",
            re,
            "--version",
            version,
            "--datacenter",
            datacenter_path,
            "--datastore",
            datastore_path,
            "--folder",
            shared_folder_path,
            "--resource-pool",
            shared_resource_path,
            "--workspace-network",
            shared_network_path,
            "--control-plane-cpu",
            cpu,
            "--control-plane-disk-gib",
            disk,
            "--control-plane-memory-mib",
            memory,
            "--worker-node-count",
            machineCount,
            "--worker-cpu",
            cpu,
            "--worker-disk-gib",
            disk,
            "--worker-memory-mib",
            memory,
            "--pods-cidr-blocks",
            pod_cidr,
            "--service-cidr-blocks",
            service_cidr,
        ]

    isCheck = False
    if command_status[0] is None:
        if saas_util.check_tmc_enabled():
            current_app.logger.info("Creating AkoDeploymentConfig for shared services cluster")
            ako_deployment_config_status = akoDeploymentConfigSharedCluster(shared_cluster_name)
            if ako_deployment_config_status[1] != 200:
                current_app.logger.info("Failed to create AKO Deployment Config for shared services cluster")
                d = {"responseType": "SUCCESS", "msg": ako_deployment_config_status[0].json["msg"], "STATUS_CODE": 500}
                return jsonify(d), 500
            current_app.logger.info("Deploying shared cluster...")
            command_status = runShellCommandAndReturnOutputAsList(createSharedCluster)
            if command_status[1] != 0:
                current_app.logger.error("Failed to run command to create shared cluster " + str(command_status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to run command to create shared cluster " + str(command_status[0]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            else:
                current_app.logger.info("Shared cluster is successfully deployed and running " + command_status[0])
    else:
        if not verifyPodsAreRunning(shared_cluster_name, command_status[0], RegexPattern.running):
            isCheck = True
            if not saas_util.check_tmc_enabled():
                current_app.logger.info("Creating AkoDeploymentConfig for shared services cluster")
                ako_deployment_config_status = akoDeploymentConfigSharedCluster(shared_cluster_name)
                if ako_deployment_config_status[1] != 200:
                    current_app.logger.info("Failed to create AKO Deployment Config for shared services cluster")
                    d = {
                        "responseType": "SUCCESS",
                        "msg": ako_deployment_config_status[0].json["msg"],
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                current_app.logger.info("Deploying shared cluster using tanzu")
                deploy_status = tanzu_util.deploy_multi_cloud_cluster(
                    shared_cluster_name,
                    cluster_plan,
                    data_center,
                    data_store,
                    shared_folder_path,
                    shared_network_path,
                    vsphere_password,
                    shared_resource_path,
                    vcenter_ip,
                    re,
                    vcenter_username,
                    machineCount,
                    size,
                    Type.SHARED,
                )
                if deploy_status[0] is None:
                    current_app.logger.error("Failed to deploy cluster " + deploy_status[1])
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to deploy cluster " + deploy_status[1],
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
            else:
                if saas_util.check_tmc_enabled():
                    current_app.logger.info("Creating AkoDeploymentConfig for shared services cluster")
                    ako_deployment_config_status = akoDeploymentConfigSharedCluster(shared_cluster_name)
                    if ako_deployment_config_status[1] != 200:
                        current_app.logger.info("Failed to create AKO Deployment Config for shared services cluster")
                        d = {
                            "responseType": "SUCCESS",
                            "msg": ako_deployment_config_status[0].json["msg"],
                            "STATUS_CODE": 500,
                        }
                        return jsonify(d), 500
                    current_app.logger.info("Deploying shared cluster, after verification using TMC")
                    try:
                        if env == Env.VMC:
                            osName = str(
                                request.get_json(force=True)["componentSpec"]["tkgSharedServiceSpec"][
                                    "tkgSharedserviceBaseOs"
                                ]
                            )
                        else:
                            osName = "photon"
                        if osName == "photon":
                            template = (
                                KubernetesOva.MARKETPLACE_PHOTON_KUBERNETES_FILE_NAME + "-" + kubernetes_ova_version
                            )
                            osVersion = "3"
                        elif osName == "ubuntu":
                            template = (
                                KubernetesOva.MARKETPLACE_UBUNTU_KUBERNETES_FILE_NAME + "-" + kubernetes_ova_version
                            )
                            osVersion = "20.04"
                        else:
                            raise Exception("Wrong os name provided")
                    except Exception as e:
                        raise Exception("Keyword " + str(e) + "  not found in input file")
                    templatePath = datacenter_path + "/vm/" + template
                    provisioner = "default"
                    register_payload = saas_util.payload_tmc_cluster_creation(
                        management_cluster,
                        provisioner,
                        shared_cluster_name,
                        clusterGroup,
                        pod_cidr,
                        service_cidr,
                        re,
                        vcenter_ip,
                        cpu,
                        disk,
                        memory,
                        machineCount,
                        AkoType.SHARED_CLUSTER_SELECTOR,
                        version,
                        datacenter_path,
                        datastore_path,
                        shared_folder_path,
                        shared_network_path,
                        shared_resource_path,
                        osName,
                        osVersion,
                        "amd64",
                        templatePath,
                        "",
                        controlPlaneNodeCount,
                    )
                    create_response = saas_util.create_tkgm_workload_cluster_on_tmc(
                        register_payload, management_cluster, provisioner
                    )
                    if not create_response[0]:
                        d = {
                            "responseType": "ERROR",
                            "msg": create_response[1],
                            "STATUS_CODE": 500,
                        }
                        return jsonify(d), 500
                    else:
                        current_app.logger.info(create_response[1])

            count = 0
            if isCheck:
                command_status = runShellCommandAndReturnOutputAsList(podRunninng)
                if command_status[1] != 0:
                    current_app.logger.error("Failed to check if pods are running " + str(command_status[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to check if pods are running " + str(command_status[0]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                while (
                    not verifyPodsAreRunning(shared_cluster_name, command_status[0], RegexPattern.running)
                    and count < 60
                ):
                    command_status = runShellCommandAndReturnOutputAsList(podRunninng)
                    if command_status[1] != 0:
                        current_app.logger.error("Failed to check if pods are running " + str(command_status[0]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to check if pods are running " + str(command_status[0]),
                            "STATUS_CODE": 500,
                        }
                        return jsonify(d), 500
                    count = count + 1
                    time.sleep(30)
                    current_app.logger.info("Waited for  " + str(count * 30) + "s, retrying.")
            if not verifyPodsAreRunning(shared_cluster_name, command_status[0], RegexPattern.running):
                current_app.logger.error(shared_cluster_name + " is not running on waiting " + str(count * 30) + "s")
                d = {
                    "responseType": "ERROR",
                    "msg": shared_cluster_name + " is not running on waiting " + str(count * 30) + "s",
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            commands = ["tanzu", "management-cluster", "kubeconfig", "get", management_cluster, "--admin"]
            kubeContextCommand = grabKubectlCommand(commands, RegexPattern.SWITCH_CONTEXT_KUBECTL)
            if kubeContextCommand is None:
                current_app.logger.error("Failed to get switch to management cluster context command")
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get switch to management cluster context command",
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            lisOfSwitchContextCommand = str(kubeContextCommand).split(" ")
            status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand)
            if status[1] != 0:
                current_app.logger.error("Failed to get switch to management cluster context " + str(status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get switch to management cluster context " + str(status[0]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            lisOfCommand = [
                "kubectl",
                "label",
                "cluster.cluster.x-k8s.io/" + shared_cluster_name,
                "cluster-role.tkg.tanzu.vmware.com/tanzu-services=" "",
                "--overwrite=true",
            ]
            status = runShellCommandAndReturnOutputAsList(lisOfCommand)
            if status[1] != 0:
                current_app.logger.error("Failed to apply k8s label " + str(status[0]))
                d = {"responseType": "ERROR", "msg": "Failed to apply k8s label " + str(status[0]), "STATUS_CODE": 500}
                return jsonify(d), 500
            lisOfCommand = [
                "kubectl",
                "label",
                "cluster",
                shared_cluster_name,
                AkoType.KEY + "=" + AkoType.SHARED_CLUSTER_SELECTOR,
                "--overwrite=true",
            ]
            status = runShellCommandAndReturnOutputAsList(lisOfCommand)
            if status[1] != 0:
                if not str(status[0]).__contains__("already has a value"):
                    current_app.logger.error("Failed to apply ako label " + str(status[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to apply ako label " + str(status[0]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
            else:
                current_app.logger.info(status[0])
            commands_shared = ["tanzu", "cluster", "kubeconfig", "get", shared_cluster_name, "--admin"]
            kubeContextCommand_shared = grabKubectlCommand(commands_shared, RegexPattern.SWITCH_CONTEXT_KUBECTL)
            if kubeContextCommand_shared is None:
                current_app.logger.error("Failed to get switch to shared cluster context command")
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get switch to shared cluster context command",
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            lisOfSwitchContextCommand_shared = str(kubeContextCommand_shared).split(" ")
            status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand_shared)
            if status[1] != 0:
                current_app.logger.error("Failed to get switch to shared cluster context " + str(status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get switch to shared cluster context " + str(status[0]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            current_app.logger.info("Switched to " + shared_cluster_name + " context")
            if checkEnableIdentityManagement(env):
                current_app.logger.info("Validating pinniped installation status")
                check_pinniped = TanzuUtil.check_pinniped_installed()
                if check_pinniped[1] != 200:
                    current_app.logger.error(check_pinniped[0])
                    d = {"responseType": "ERROR", "msg": check_pinniped[0], "STATUS_CODE": 500}
                    return jsonify(d), 500
                cluster_admin_users = request.get_json(force=True)["componentSpec"]["tkgSharedServiceSpec"][
                    "tkgSharedserviceRbacUserRoleSpec"
                ]["clusterAdminUsers"]
                admin_users = request.get_json(force=True)["componentSpec"]["tkgSharedServiceSpec"][
                    "tkgSharedserviceRbacUserRoleSpec"
                ]["adminUsers"]
                edit_users = request.get_json(force=True)["componentSpec"]["tkgSharedServiceSpec"][
                    "tkgSharedserviceRbacUserRoleSpec"
                ]["editUsers"]
                view_users = request.get_json(force=True)["componentSpec"]["tkgSharedServiceSpec"][
                    "tkgSharedserviceRbacUserRoleSpec"
                ]["viewUsers"]
                rbac_user_status = createRbacUsers(
                    shared_cluster_name,
                    isMgmt=False,
                    env=env,
                    edit_users=edit_users,
                    cluster_admin_users=cluster_admin_users,
                    admin_users=admin_users,
                    view_users=view_users,
                )
                if rbac_user_status[1] != 200:
                    current_app.logger.error(rbac_user_status[0].json["msg"])
                    d = {"responseType": "ERROR", "msg": rbac_user_status[0].json["msg"], "STATUS_CODE": 500}
                    return jsonify(d), 500
                current_app.logger.info("Successfully created RBAC for all the provided users")
            else:
                current_app.logger.info("Identity Management is not enabled")

            current_app.logger.info("Verifying if AKO pods are running...")
            podRunninng_ako_main = ["kubectl", "get", "pods", "-n", "avi-system"]
            podRunninng_ako_grep = ["grep", "ako-0"]
            count_ako = 0
            time.sleep(30)
            timer = 30
            ako_pod_running = False
            while timer < 600:
                current_app.logger.info("Check if AKO pods are running. Waited for " + str(timer) + "s retrying")
                command_status_ako = grabPipeOutput(podRunninng_ako_main, podRunninng_ako_grep)
                if command_status_ako[1] != 0:
                    time.sleep(30)
                    timer = timer + 30
                else:
                    ako_pod_running = True
                    break
            if not ako_pod_running:
                current_app.logger.error("AKO pods are not running on waiting for 10m " + command_status_ako[0])
                d = {
                    "responseType": "ERROR",
                    "msg": "AKO pods are not running on waiting for 10m " + str(command_status_ako[0]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            found = False
            if verifyPodsAreRunning(AppName.AKO, command_status_ako[0], RegexPattern.RUNNING):
                found = True
            while not verifyPodsAreRunning(AppName.AKO, command_status_ako[0], RegexPattern.RUNNING) and count_ako < 20:
                command_status = grabPipeOutput(podRunninng_ako_main, podRunninng_ako_grep)
                if command_status[1] != 0:
                    current_app.logger.error("Failed to check if pods are running " + str(command_status_ako[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to check if pods are running " + str(command_status_ako[0]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                if verifyPodsAreRunning(AppName.AKO, command_status[0], RegexPattern.RUNNING):
                    found = True
                    break
                count_ako = count_ako + 1
                time.sleep(30)
                current_app.logger.info("Waited for  " + str(count_ako * 30) + "s, retrying.")
            if not found:
                current_app.logger.error("Ako pods are not running on waiting " + str(count_ako * 30))
                d = {
                    "responseType": "ERROR",
                    "msg": "Ako pods are not running on waiting " + str(count_ako * 30),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            if count_ako > 30:
                for i in tqdm(range(150), desc="Waiting…", ascii=False, ncols=75):
                    time.sleep(1)
        else:
            current_app.logger.info("Shared cluster is already deployed and running ")
        if saas_util.check_tmc_enabled():
            current_app.logger.info("Cluster is already deployed via TMC")
            if checkDataProtectionEnabled(env, "shared"):
                is_enabled = enable_data_protection(env, shared_cluster_name, management_cluster)
                if not is_enabled[0]:
                    current_app.logger.error(is_enabled[1])
                    d = {"responseType": "ERROR", "msg": is_enabled[1], "STATUS_CODE": 500}
                    return jsonify(d), 500
                current_app.logger.info(is_enabled[1])
        else:
            current_app.logger.info("TMC is deactivated")
            current_app.logger.info("Check whether data protection is to be enabled via Velero")
            if checkDataProtectionEnabledVelero(env, "shared"):
                commands_shared = ["tanzu", "cluster", "kubeconfig", "get", shared_cluster_name, "--admin"]
                kubeContextCommand_shared = grabKubectlCommand(commands_shared, RegexPattern.SWITCH_CONTEXT_KUBECTL)
                if kubeContextCommand_shared is None:
                    current_app.logger.error("Failed to get switch to shared cluster context command")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get switch to shared cluster context command",
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                lisOfSwitchContextCommand_shared = str(kubeContextCommand_shared).split(" ")
                status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand_shared)
                if status[1] != 0:
                    current_app.logger.error("Failed to get switch to shared cluster context " + str(status[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get switch to shared cluster context " + str(status[0]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                current_app.logger.info("Switched to " + shared_cluster_name + " context")
                is_enabled = enable_data_protection_velero("shared", env)
                if not is_enabled[0]:
                    current_app.logger.error("Failed to enable data protection via velero")
                    current_app.logger.error(is_enabled[1])
                    d = {"responseType": "ERROR", "msg": is_enabled[1], "STATUS_CODE": 500}
                    return jsonify(d), 500
                current_app.logger.info("Successfully enabled data protection via Velero")
                current_app.logger.info(is_enabled[1])
            else:
                current_app.logger.info("Data protection via Velero setting is not active")
        to = saas_util.register_tanzu_observability(shared_cluster_name, size)
        if to[1] != 200:
            current_app.logger.error(to[0])
            d = {"responseType": "ERROR", "msg": to[0], "STATUS_CODE": 500}
            return jsonify(d), to[1]
    d = {"responseType": "SUCCESS", "msg": "Successfully deployed Shared cluster", "STATUS_CODE": 200}
    return jsonify(d), 200


@shared_config.route("/api/tanzu/vsphere/tkgsharedsvc/extensions", methods=["POST"])
@shared_config.route("/api/tanzu/vmc/tkgsharedsvc/extensions", methods=["POST"])
def deployExtensions():
    pre = preChecks()
    if pre[1] != 200:
        current_app.logger.error(pre[0].json["msg"])
        d = {"responseType": "ERROR", "msg": pre[0].json["msg"], "STATUS_CODE": 500}
        return jsonify(d), 500
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {"responseType": "ERROR", "msg": "Wrong env provided " + env[0], "STATUS_CODE": 500}
        return jsonify(d), 500
    env = env[0]
    spec_json = request.get_json(force=True)
    spec_obj = CommonUtils.get_spec_obj(env)
    spec: spec_obj = spec_obj.parse_obj(spec_json)
    TanzuUtil(env=env, spec=spec)
    service = request.args.get("service", default="all", type=str)
    if env == Env.VMC:
        shared_cluster_name = request.get_json(force=True)["componentSpec"]["tkgSharedServiceSpec"][
            "tkgSharedClusterName"
        ]
        str_enc = str(request.get_json(force=True)["componentSpec"]["harborSpec"]["harborPasswordBase64"])
        base64_bytes = str_enc.encode("ascii")
        enc_bytes = base64.b64decode(base64_bytes)
        password = enc_bytes.decode("ascii").rstrip("\n")
        harborPassword = password
        host = request.get_json(force=True)["componentSpec"]["harborSpec"]["harborFqdn"]
        harborCertPath = request.get_json(force=True)["componentSpec"]["harborSpec"]["harborCertPath"]
        harborCertKeyPath = request.get_json(force=True)["componentSpec"]["harborSpec"]["harborCertKeyPath"]
        isHarborEnabled = True
    else:
        if env == Env.VCF:
            shared_cluster_name = request.get_json(force=True)["tkgComponentSpec"]["tkgSharedserviceSpec"][
                "tkgSharedserviceClusterName"
            ]
        else:
            shared_cluster_name = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"][
                "tkgSharedserviceClusterName"
            ]
        str_enc = str(request.get_json(force=True)["harborSpec"]["harborPasswordBase64"])
        base64_bytes = str_enc.encode("ascii")
        enc_bytes = base64.b64decode(base64_bytes)
        password = enc_bytes.decode("ascii").rstrip("\n")
        harborPassword = password
        host = request.get_json(force=True)["harborSpec"]["harborFqdn"]
        harborCertPath = request.get_json(force=True)["harborSpec"]["harborCertPath"]
        harborCertKeyPath = request.get_json(force=True)["harborSpec"]["harborCertKeyPath"]
        checkHarborEnabled = request.get_json(force=True)["harborSpec"]["enableHarborExtension"]
        if str(checkHarborEnabled).lower() == "true":
            isHarborEnabled = True
        else:
            isHarborEnabled = False
    if checkAirGappedIsEnabled(env):
        repo_address = str(request.get_json(force=True)["envSpec"]["customRepositorySpec"]["tkgCustomImageRepository"])
    else:
        repo_address = Repo.PUBLIC_REPO
    if not repo_address.endswith("/"):
        repo_address = repo_address + "/"
    repo_address = repo_address.replace("https://", "").replace("http://", "")
    cert_ext_status = installCertManagerAndContour(env, shared_cluster_name, repo_address, service)
    if cert_ext_status[1] != 200:
        current_app.logger.error(cert_ext_status[0].json["msg"])
        d = {"responseType": "ERROR", "msg": cert_ext_status[0].json["msg"], "STATUS_CODE": 500}
        return jsonify(d), 500

    if not isHarborEnabled:
        service = "disable"
    if service == "registry" or service == "all":
        if not host or not harborPassword:
            current_app.logger.error(
                "Harbor FQDN and password are mandatory for harbor deployment." " Please provide both the details"
            )
            d = {
                "responseType": "ERROR",
                "msg": "Harbor FQDN and password are mandatory for harbor deployment. Please provide both the details",
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        current_app.logger.info("Validating if harbor is running")
        state = installHarbor14(
            service, repo_address, harborCertPath, harborCertKeyPath, harborPassword, host, shared_cluster_name
        )
        if state[1] != 200:
            current_app.logger.error(state[0].json["msg"])
            d = {"responseType": "ERROR", "msg": state[0].json["msg"], "STATUS_CODE": 500}
            return jsonify(d), 500
    current_app.logger.info("Configured all extensions successfully")
    d = {"responseType": "SUCCESS", "msg": "Configured all extensions successfully", "STATUS_CODE": 200}
    return jsonify(d), 200


def installHarbor14(service, repo_address, harborCertPath, harborCertKeyPath, harborPassword, host, clusterName):
    clusterName_path = os.path.join(Paths.CLUSTER_PATH, clusterName)
    main_command = ["tanzu", "package", "installed", "list", "-A"]
    sub_command = ["grep", AppName.HARBOR]
    out = grabPipeOutput(main_command, sub_command)
    if not verifyPodsAreRunning(AppName.HARBOR, out[0], RegexPattern.RECONCILE_SUCCEEDED):
        timer = 0
        current_app.logger.info("Validating if contour and cert-manager is running")
        command = ["tanzu", "package", "installed", "list", "-A"]
        status = runShellCommandAndReturnOutputAsList(command)
        verify_contour = False
        verify_cert_manager = False
        while timer < 600:
            if verify_contour or verifyPodsAreRunning(AppName.CONTOUR, status[0], RegexPattern.RECONCILE_SUCCEEDED):
                current_app.logger.info("Contour is running")
                verify_contour = True
            if verify_cert_manager or verifyPodsAreRunning(
                AppName.CERT_MANAGER, status[0], RegexPattern.RECONCILE_SUCCEEDED
            ):
                verify_cert_manager = True
                current_app.logger.info("Cert Manager is running")

            if verify_contour and verify_cert_manager:
                break
            else:
                timer = timer + 30
                time.sleep(30)
                status = runShellCommandAndReturnOutputAsList(command)
                current_app.logger.info(
                    "Waited for " + str(timer) + "s, retrying for contour and cert manager to be running"
                )
        if not verify_contour:
            current_app.logger.error("Contour is not running")
            d = {"responseType": "ERROR", "msg": "Contour is not running ", "STATUS_CODE": 500}
            return jsonify(d), 500
        if not verify_cert_manager:
            current_app.logger.error("Cert manager is not running")
            d = {"responseType": "ERROR", "msg": "Cert manager is not running ", "STATUS_CODE": 500}
            return jsonify(d), 500
        state = TanzuUtil.get_version_of_package("harbor.tanzu.vmware.com")
        if state is None:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get Version of package harbor.tanzu.vmware.com",
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        current_app.logger.info("Deploying harbor")
        current_app.logger.info("Harbor version " + state)
        get_url_command = [
            "kubectl",
            "-n",
            "tkg-system",
            "get",
            "packages",
            "harbor.tanzu.vmware.com." + state,
            "-o",
            "jsonpath='{.spec.template.spec.fetch[0].imgpkgBundle.image}'",
        ]
        current_app.logger.info("Getting harbor url")
        status = runShellCommandAndReturnOutputAsList(get_url_command)
        if status[1] != 0:
            current_app.logger.error("Failed to get harbor image url " + str(status[0]))
            d = {"responseType": "ERROR", "msg": "Failed to get harbor image url " + str(status[0]), "STATUS_CODE": 500}
            return jsonify(d), 500
        current_app.logger.info("Got harbor url " + str(status[0][0]).replace("'", ""))
        my_file = Path("./cacrtbase64d.crt")
        if my_file.exists():
            pull = [
                "imgpkg",
                "pull",
                "-b",
                str(status[0][0]).replace("'", ""),
                "-o",
                "/tmp/harbor-package",
                "--registry-ca-cert-path",
                "./cacrtbase64d.crt",
            ]
        else:
            pull = ["imgpkg", "pull", "-b", str(status[0][0]).replace("'", ""), "-o", "/tmp/harbor-package"]
        status = runShellCommandAndReturnOutputAsList(pull)
        if status[1] != 0:
            current_app.logger.error("Failed to pull harbor packages " + str(status[0]))
            d = {"responseType": "ERROR", "msg": "Failed to get harbor image url " + str(status[0]), "STATUS_CODE": 500}
            return jsonify(d), 500
        rm_cmd = ["rm", "-rf ", clusterName_path, "/harbor-data-values.yaml"]
        runShellCommandAndReturnOutputAsList(rm_cmd)
        cp_cmd = ["cp", "/tmp/harbor-package/config/values.yaml", clusterName_path + "/harbor-data-values.yaml"]
        runShellCommandAndReturnOutputAsList(cp_cmd)
        command_harbor_genrate_psswd = [
            "sh",
            "/tmp/harbor-package/config/scripts/generate-passwords.sh",
            clusterName_path + "/harbor-data-values.yaml",
        ]
        state_harbor_genrate_psswd = runShellCommandAndReturnOutputAsList(command_harbor_genrate_psswd)
        if state_harbor_genrate_psswd[1] == 500:
            current_app.logger.error("Failed to generate password " + str(state_harbor_genrate_psswd[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to generate password " + str(state_harbor_genrate_psswd[0]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        cer = certChanging(harborCertPath, harborCertKeyPath, harborPassword, host, clusterName)
        if cer[1] != 200:
            current_app.logger.error(cer[0].json["msg"])
            d = {"responseType": "ERROR", "msg": cer[0].json["msg"], "STATUS_CODE": 500}
            return jsonify(d), 500

        chmod_cmd = ["chmod", "+x", "common/injectValue.sh"]
        runShellCommandAndReturnOutputAsList(chmod_cmd)
        command = ["sh", "./common/injectValue.sh", clusterName_path + "/harbor-data-values.yaml", "remove"]
        runShellCommandAndReturnOutputAsList(command)
        # Changed for glasgow
        harbor_ns = "tanzu-system-registry"
        extra_ns = "tanzu-harbor-registry"
        verify_ns = ["kubectl", "get", "ns"]
        out = runShellCommandAndReturnOutputAsList(verify_ns)
        for item in out[0]:
            if harbor_ns in item:
                break
        else:
            create_ns_cmd = ["kubectl", "create", "ns", harbor_ns]
            runProcess(create_ns_cmd)

        out = runShellCommandAndReturnOutputAsList(verify_ns)
        for item in out[0]:
            if extra_ns in item:
                break
        else:
            create_ns_cmd = ["kubectl", "create", "ns", extra_ns]
            runProcess(create_ns_cmd)

        command = [
            "tanzu",
            "package",
            "install",
            "harbor",
            "--package",
            "harbor.tanzu.vmware.com",
            "--version",
            state,
            "--values-file",
            clusterName_path + "/harbor-data-values.yaml",
            "--namespace",
            extra_ns,
        ]
        runShellCommandAndReturnOutputAsList(command)
        createOverlayYaml(repo_address, clusterName)
        cp_cmd = ["cp", "./common/harbor-overlay.yaml", Paths.CLUSTER_PATH]
        runShellCommandAndReturnOutputAsList(cp_cmd)
        state = waitForGrepProcessWithoutChangeDir(
            main_command, sub_command, AppName.HARBOR, RegexPattern.RECONCILE_SUCCEEDED
        )
        if state[1] != 200:
            current_app.logger.error(state[0].json["msg"])
            d = {"responseType": "ERROR", "msg": state[0].json["msg"], "STATUS_CODE": 500}
            return jsonify(d), 500
        current_app.logger.info("Deployed harbor successfully")
        d = {"responseType": "SUCCESS", "msg": "Deployed harbor successfully", "STATUS_CODE": 200}
        return jsonify(d), 200
    else:
        current_app.logger.info("Harbor is already deployed and running")
        d = {"responseType": "SUCCESS", "msg": "Harbor is already deployed and running", "STATUS_CODE": 200}
        return jsonify(d), 200


def certChanging(harborCertPath, harborCertKeyPath, harborPassword, host, clusterName):
    os.system("chmod +x common/inject.sh")
    location = Paths.CLUSTER_PATH + clusterName + "/harbor-data-values.yaml"
    if harborCertPath and harborCertKeyPath:
        harbor_cert = Path(harborCertPath).read_text()
        harbor_cert_key = Path(harborCertKeyPath).read_text()
        certContent = harbor_cert
        certKeyContent = harbor_cert_key
        command_harbor_change_host_password_cert = [
            "sh",
            "./common/inject.sh",
            location,
            harborPassword,
            host,
            certContent,
            certKeyContent,
        ]
        state_harbor_change_host_password_cert = runShellCommandAndReturnOutput(
            command_harbor_change_host_password_cert
        )
        if state_harbor_change_host_password_cert[1] == 500:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to change host, password and cert " + str(state_harbor_change_host_password_cert[0]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
    else:
        command_harbor_change_host_password_cert = ["sh", "./common/inject.sh", location, harborPassword, host, "", ""]
        state_harbor_change_host_password_cert = runShellCommandAndReturnOutput(
            command_harbor_change_host_password_cert
        )
        if state_harbor_change_host_password_cert[1] == 500:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to change host, password and cert " + str(state_harbor_change_host_password_cert[0]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
    d = {"responseType": "SUCCESS", "msg": "Updated harbor data-values yaml", "STATUS_CODE": 200}
    return jsonify(d), 200
