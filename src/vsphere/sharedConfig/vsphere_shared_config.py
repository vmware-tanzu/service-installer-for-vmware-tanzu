from flask import Blueprint
import logging
import sys

logger = logging.getLogger(__name__)
from flask import jsonify, request
from flask import current_app
import requests
import os
from tqdm import tqdm
import time
import base64
import json
from common.model.vsphereSpec import VsphereMasterSpec

sys.path.append(".../")
from common.operation.vcenter_operations import createResourcePool, create_folder, checkforIpAddress, getSi
from common.operation.constants import ResourcePoolAndFolderName, Vcenter, CIDR, Env, PLAN, Sizing, Type, Tkg_version
from common.operation.ShellHelper import runShellCommandAndReturnOutput, grabKubectlCommand, grabIpAddress, \
    verifyPodsAreRunning, grabPipeOutput, runShellCommandAndReturnOutputAsList, \
    runShellCommandAndReturnOutputAsListWithChangedDir, grabPipeOutputChagedDir, runShellCommandWithPolling, runProcess
from common.operation.constants import SegmentsName, RegexPattern, Versions, AkoType, AppName, Extentions
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from vmc.sharedConfig.shared_config import deployExtentions
from common.common_utilities import preChecks, envCheck, checkSharedServiceProxyEnabled, \
    checkWorkloadProxyEnabled, enableProxy, checkAirGappedIsEnabled, grabPortFromUrl, grabHostFromUrl, \
    registerWithTmcOnSharedAndWorkload, deployCluster, registerTanzuObservability, registerTSM, getNetworkFolder, \
    downloadAndPushKubernetesOvaMarketPlace, isEnvTkgs_wcp, isEnvTkgs_ns, getKubeVersionFullName, getNetworkPathTMC, \
    checkDataProtectionEnabled, enable_data_protection
from common.common_utilities import preChecks, envCheck, get_avi_version, checkSharedServiceProxyEnabled, \
    checkWorkloadProxyEnabled, enableProxy, checkAirGappedIsEnabled, grabPortFromUrl, grabHostFromUrl, \
    registerWithTmcOnSharedAndWorkload, deployCluster, registerTanzuObservability, registerTSM, getNetworkFolder, \
    checkTmcEnabled, createProxyCredentialsTMC, checkTmcRegister, checkEnableIdentityManagement, checkPinnipedInstalled, \
    checkPinnipedServiceStatus, checkPinnipedDexServiceStatus, createRbacUsers

from common.certificate_base64 import getBase64CertWriteToFile

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

vsphere_shared_config = Blueprint("vsphere_shared_config", __name__, static_folder="sharedConfig")


@vsphere_shared_config.route("/api/tanzu/vsphere/tkgsharedsvc", methods=['POST'])
def configSharedCluster():
    deploy_shared = deploy()
    if deploy_shared[1] != 200:
        current_app.logger.error(deploy_shared[0].json['msg'])
        d = {
            "responseType": "ERROR",
            "msg": "Failed to Config shared cluster " + str(deploy_shared[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    deploy_extention = deployExtentions()
    if deploy_extention[1] != 200:
        current_app.logger.error(str(deploy_extention[0].json['msg']))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to deploy extention " + str(deploy_extention[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    d = {
        "responseType": "SUCCESS",
        "msg": "Shared cluster configured Successfully",
        "ERROR_CODE": 200
    }
    current_app.logger.info("Shared cluster configured Successfully")
    return jsonify(d), 200


@vsphere_shared_config.route("/api/tanzu/vsphere/tkgsharedsvc/config", methods=['POST'])
def deploy():
    pre = preChecks()
    if pre[1] != 200:
        current_app.logger.error(pre[0].json['msg'])
        d = {
            "responseType": "ERROR",
            "msg": pre[0].json['msg'],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {
            "responseType": "ERROR",
            "msg": "Wrong env provided " + env[0],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    json_dict = request.get_json(force=True)
    vsSpec = VsphereMasterSpec.parse_obj(json_dict)
    env = env[0]
    aviVersion = get_avi_version(env)
    password = current_app.config['VC_PASSWORD']
    vcenter_username = current_app.config['VC_USER']
    vcenter_ip = current_app.config['VC_IP']
    cluster_name = current_app.config['VC_CLUSTER']
    data_center = current_app.config['VC_DATACENTER']
    data_store = current_app.config['VC_DATASTORE']
    parent_resourcePool = current_app.config['RESOURCE_POOL']
    refToken = request.get_json(force=True)['envSpec']['marketplaceSpec']['refreshToken']
    if not (isEnvTkgs_wcp(env) or isEnvTkgs_ns(env)):
        if env == Env.VSPHERE:
            kubernetes_ova_os = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"][
                "tkgSharedserviceBaseOs"]
            kubernetes_ova_version = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"][
                "tkgSharedserviceKubeVersion"]
            pod_cidr = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                'tkgSharedserviceClusterCidr']
            service_cidr = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                'tkgSharedserviceServiceCidr']
        elif env == Env.VCF:
            kubernetes_ova_os = request.get_json(force=True)["tkgComponentSpec"]["tkgSharedserviceSpec"][
                "tkgSharedserviceBaseOs"]
            kubernetes_ova_version = request.get_json(force=True)["tkgComponentSpec"]["tkgSharedserviceSpec"][
                "tkgSharedserviceKubeVersion"]
            pod_cidr = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                'tkgSharedserviceClusterCidr']
            service_cidr = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                'tkgSharedserviceServiceCidr']
        if refToken:
            current_app.logger.info("Kubernetes OVA configs for shared services cluster")
            down_status = downloadAndPushKubernetesOvaMarketPlace(env, kubernetes_ova_version, kubernetes_ova_os)
            if down_status[0] is None:
                current_app.logger.error(down_status[1])
                d = {
                    "responseType": "ERROR",
                    "msg": down_status[1],
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
    else:
        current_app.logger.info("MarketPlace refresh token is not provided, skipping the download of kubernetes ova")
    try:
        isCreated4 = createResourcePool(vcenter_ip, vcenter_username, password,
                                        cluster_name,
                                        ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME_VCENTER,
                                        parent_resourcePool, data_center)
        if isCreated4 is not None:
            current_app.logger.info(
                "Created resource pool " + ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME_VCENTER)
    except Exception as e:
        current_app.logger.error("Failed to create resource pool " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create resource pool " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    try:
        isCreated1 = create_folder(vcenter_ip, vcenter_username, password,
                                   data_center,
                                   ResourcePoolAndFolderName.SHARED_FOLDER_NAME_VSPHERE)
        if isCreated1 is not None:
            current_app.logger.info("Created folder " + ResourcePoolAndFolderName.SHARED_FOLDER_NAME_VSPHERE)
    except Exception as e:
        current_app.logger.error("Failed to create folder " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create folder " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500, str(e)
    management_cluster = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
        'tkgMgmtClusterName']
    try:
        with open('/root/.ssh/id_rsa.pub', 'r') as f:
            re = f.readline()
    except Exception as e:
        current_app.logger.error("Failed to ssh key from config file " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to ssh key from config file " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    podRunninng = ["tanzu", "cluster", "list"]
    command_status = runShellCommandAndReturnOutputAsList(podRunninng)
    if command_status[1] != 0:
        current_app.logger.error("Failed to run command to check status of pods")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to run command to check status of pods",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    tmc_required = str(request.get_json(force=True)['envSpec']["saasEndpoints"]['tmcDetails']['tmcAvailability'])
    tmc_flag = False
    if tmc_required.lower() == "true":
        tmc_flag = True
    elif tmc_required.lower() == "false":
        tmc_flag = False
        current_app.logger.info("Tmc registration is disabled")
    else:
        current_app.logger.error("Wrong tmc selection attribute provided " + tmc_required)
        d = {
            "responseType": "ERROR",
            "msg": "Wrong tmc selection attribute provided " + tmc_required,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if env == Env.VCF:
        shared_cluster_name = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
            'tkgSharedserviceClusterName']
        cluster_plan = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
            'tkgSharedserviceDeploymentType']
    else:
        shared_cluster_name = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
            'tkgSharedserviceClusterName']
        cluster_plan = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
            'tkgSharedserviceDeploymentType']
    if cluster_plan == PLAN.DEV_PLAN:
        additional_command = ""
        if env == Env.VCF:
            machineCount = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                'tkgSharedserviceWorkerMachineCount']
        else:
            machineCount = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                'tkgSharedserviceWorkerMachineCount']
    elif cluster_plan == PLAN.PROD_PLAN:
        additional_command = "--high-availability"
        if env == Env.VCF:
            machineCount = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                'tkgSharedserviceWorkerMachineCount']
        else:
            machineCount = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                'tkgSharedserviceWorkerMachineCount']
    else:
        current_app.logger.error("Un supported control plan provided please specify prod or dev " + cluster_plan)
        d = {
            "responseType": "ERROR",
            "msg": "Un supported control plan provided please specify prod or dev " + cluster_plan,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if env == Env.VSPHERE:
        size = str(request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceSize'])
    else:
        size = str(request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceSize'])
    if size.lower() == "large":
        pass
    elif size.lower() == "medium":
        pass
    elif size.lower() == "extra-large":
        pass
    elif size.lower() == "custom":
        pass
    else:
        current_app.logger.error("Provided cluster size: " + size + "is not supported, please provide one of: medium/large/extra-large/custom")
        d = {
            "responseType": "ERROR",
            "msg": "Provided cluster size: " + size + "is not supported, please provide one of: medium/large/extra-large/custom",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if size.lower() == "medium":
        cpu = Sizing.medium['CPU']
        memory = Sizing.medium['MEMORY']
        disk = Sizing.medium['DISK']
    elif size.lower() == "large":
        cpu = Sizing.large['CPU']
        memory = Sizing.large['MEMORY']
        disk = Sizing.large['DISK']
    elif size.lower() == "extra-large":
        cpu = Sizing.extraLarge['CPU']
        memory = Sizing.extraLarge['MEMORY']
        disk = Sizing.extraLarge['DISK']
    elif size.lower() == "custom":
        if env == Env.VCF:
            cpu = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                'tkgSharedserviceCpuSize']
            disk = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                'tkgSharedserviceStorageSize']
            control_plane_mem_gb = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                'tkgSharedserviceMemorySize']
            memory = str(int(control_plane_mem_gb) * 1024)
        else:
            cpu = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                'tkgSharedserviceCpuSize']
            disk = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                'tkgSharedserviceStorageSize']
            control_plane_mem_gb = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                'tkgSharedserviceMemorySize']
            memory = str(int(control_plane_mem_gb) * 1024)
    else:
        current_app.logger.error("Provided cluster size: " + size + "is not supported, please provide one of: medium/large/extra-large/custom")
        d = {
            "responseType": "ERROR",
            "msg": "Provided cluster size: " + size + "is not supported, please provide one of: medium/large/extra-large/custom",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if env == Env.VCF:
        shared_service_network = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
            'tkgSharedserviceNetworkName']
    else:
        shared_service_network = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
            'tkgMgmtNetworkName']

    vsphere_password = password
    _base64_bytes = vsphere_password.encode('ascii')
    _enc_bytes = base64.b64encode(_base64_bytes)
    vsphere_password = _enc_bytes.decode('ascii')
    datacenter_path = "/" + data_center
    datastore_path = datacenter_path + "/datastore/" + data_store
    shared_folder_path = datacenter_path + "/vm/" + ResourcePoolAndFolderName.SHARED_FOLDER_NAME_VSPHERE
    if parent_resourcePool:
        shared_resource_path = datacenter_path + "/host/" + cluster_name + "/Resources/" + parent_resourcePool + "/" + ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME_VCENTER
    else:
        shared_resource_path = datacenter_path + "/host/" + cluster_name + "/Resources/" + ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME_VCENTER
    shared_network_path = getNetworkFolder(shared_service_network, vcenter_ip, vcenter_username, password)
    if not shared_network_path:
        current_app.logger.error("Network folder not found for " + shared_service_network)
        d = {
            "responseType": "ERROR",
            "msg": "Network folder not found for " + shared_service_network,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if Tkg_version.TKG_VERSION == "1.5" and checkTmcEnabled(env):
        if env == Env.VCF:
            clusterGroup = request.get_json(force=True)['tkgComponentSpec']["tkgSharedserviceSpec"]['tkgSharedserviceClusterGroupName']
        else:
            clusterGroup = request.get_json(force=True)['tkgComponentSpec']["tkgMgmtComponents"]['tkgSharedserviceClusterGroupName']

        if not clusterGroup:
            clusterGroup = "default"
        commands = ["tanzu", "management-cluster", "kubeconfig", "get", management_cluster, "--admin"]
        kubeContextCommand = grabKubectlCommand(commands, RegexPattern.SWITCH_CONTEXT_KUBECTL)
        if kubeContextCommand is None:
            current_app.logger.error("Failed to get switch to management cluster context command")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get switch to management cluster context command",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        lisOfSwitchContextCommand = str(kubeContextCommand).split(" ")
        status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand)
        if status[1] != 0:
            current_app.logger.error("Failed to get switch to management cluster context " + str(status[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get switch to management cluster context " + str(status[0]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        version_status = getKubeVersionFullName(kubernetes_ova_version)
        if version_status[0] is None:
            current_app.logger.error("Kubernetes OVA Version is not found for Shared Service Cluster")
            d = {
                "responseType": "ERROR",
                "msg": "Kubernetes OVA Version is not found for Shared Service Cluster",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        else:
            version = version_status[0]
        shared_network_folder_path = getNetworkPathTMC(shared_service_network, vcenter_ip, vcenter_username, password)
        if checkSharedServiceProxyEnabled(env) and not checkTmcRegister(shared_cluster_name, False):
            proxy_name_state = createProxyCredentialsTMC(env, shared_cluster_name, "true", "shared", register=False)
            if proxy_name_state[1] != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": proxy_name_state[0],
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            proxy_name = "arcas-" + shared_cluster_name + "-tmc-proxy"
            if cluster_plan.lower() == PLAN.PROD_PLAN:
                createSharedCluster = ["tmc", "cluster", "create", "-t", "tkg-vsphere", "-n", shared_cluster_name, "-m",
                                       management_cluster, "-p", "default", "--cluster-group", clusterGroup,
                                       "--ssh-key", re, "--version", version, "--datacenter", datacenter_path,
                                       "--datastore",
                                       datastore_path, "--folder", shared_folder_path, "--resource-pool",
                                       shared_resource_path,
                                       "--workspace-network", shared_network_folder_path, "--control-plane-cpu", cpu,
                                       "--control-plane-disk-gib", disk, "--control-plane-memory-mib", memory,
                                       "--worker-node-count", machineCount, "--worker-cpu", cpu, "--worker-disk-gib",
                                       disk, "--worker-memory-mib", memory, "--pods-cidr-blocks", pod_cidr,
                                       "--service-cidr-blocks", service_cidr, "--high-availability", "--proxy-name",
                                       proxy_name]
            else:
                createSharedCluster = ["tmc", "cluster", "create", "-t", "tkg-vsphere", "-n", shared_cluster_name, "-m",
                                       management_cluster, "-p", "default", "--cluster-group", clusterGroup,
                                       "--ssh-key", re, "--version", version, "--datacenter", datacenter_path,
                                       "--datastore",
                                       datastore_path, "--folder", shared_folder_path, "--resource-pool",
                                       shared_resource_path,
                                       "--workspace-network", shared_network_folder_path, "--control-plane-cpu", cpu,
                                       "--control-plane-disk-gib", disk, "--control-plane-memory-mib", memory,
                                       "--worker-node-count", machineCount, "--worker-cpu", cpu, "--worker-disk-gib",
                                       disk, "--worker-memory-mib", memory, "--pods-cidr-blocks", pod_cidr,
                                       "--service-cidr-blocks", service_cidr,"--proxy-name",
                                       proxy_name]
        else:
            if cluster_plan.lower() == PLAN.PROD_PLAN:
                createSharedCluster = ["tmc", "cluster", "create", "-t", "tkg-vsphere", "-n", shared_cluster_name, "-m",
                                       management_cluster, "-p", "default", "--cluster-group", clusterGroup,
                                       "--ssh-key", re, "--version", version, "--datacenter", datacenter_path,
                                       "--datastore",
                                       datastore_path, "--folder", shared_folder_path, "--resource-pool",
                                       shared_resource_path,
                                       "--workspace-network", shared_network_folder_path, "--control-plane-cpu", cpu,
                                       "--control-plane-disk-gib", disk, "--control-plane-memory-mib", memory,
                                       "--worker-node-count", machineCount, "--worker-cpu", cpu, "--worker-disk-gib",
                                       disk, "--worker-memory-mib", memory, "--pods-cidr-blocks", pod_cidr,
                                       "--service-cidr-blocks", service_cidr, "--high-availability"]
            else:
                createSharedCluster = ["tmc", "cluster", "create", "-t", "tkg-vsphere", "-n", shared_cluster_name, "-m",
                                       management_cluster, "-p", "default", "--cluster-group", clusterGroup,
                                       "--ssh-key", re, "--version", version, "--datacenter", datacenter_path,
                                       "--datastore",
                                       datastore_path, "--folder", shared_folder_path, "--resource-pool",
                                       shared_resource_path,
                                       "--workspace-network", shared_network_folder_path, "--control-plane-cpu", cpu,
                                       "--control-plane-disk-gib", disk, "--control-plane-memory-mib", memory,
                                       "--worker-node-count", machineCount, "--worker-cpu", cpu, "--worker-disk-gib",
                                       disk, "--worker-memory-mib", memory, "--pods-cidr-blocks", pod_cidr,
                                       "--service-cidr-blocks", service_cidr]
    isCheck = False
    if command_status[0] is None:
        if Tkg_version.TKG_VERSION == "1.5" and checkTmcEnabled(env):
            current_app.logger.info("Deploying shared cluster")
            command_status = runShellCommandAndReturnOutputAsList(createSharedCluster)
            if command_status[1] != 0:
                current_app.logger.error("Failed to run command to create shared cluster " + str(command_status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to run command to create shared cluster " + str(command_status[0]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            else:
                current_app.logger.info("Shared cluster is successfully deployed and running " + command_status[0])
    else:
        if not verifyPodsAreRunning(shared_cluster_name, command_status[0], RegexPattern.running):
            isCheck = True
            if not checkTmcEnabled(env):
                current_app.logger.info("Deploying shared cluster using tanzu 1.5")
                deploy_status = deployCluster(shared_cluster_name, cluster_plan,
                                              data_center, data_store, shared_folder_path, shared_network_path,
                                              vsphere_password,
                                              shared_resource_path, vcenter_ip, re, vcenter_username, machineCount,
                                              size, env, Type.SHARED, vsSpec)
                if deploy_status[0] is None:
                    current_app.logger.error("Failed to deploy cluster " + deploy_status[1])
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to deploy cluster " + deploy_status[1],
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
            else:
                if checkTmcEnabled(env):
                    current_app.logger.info("Deploying shared cluster, after verification using tmc")
                    command_status_v = runShellCommandAndReturnOutputAsList(createSharedCluster)
                    if command_status_v[1] != 0:
                        if str(command_status_v[0]).__contains__("DeadlineExceeded"):
                            current_app.logger.error(
                                "Failed to run command to create shared cluster check tmc management cluster is not in disconnected state " + str(
                                    command_status_v[0]))
                        else:
                            current_app.logger.info("Waiting for folders to be available in tmc…")
                            for i in tqdm(range(150), desc="Waiting for folders to be available in tmc…", ascii=False,
                                          ncols=75):
                                time.sleep(1)
                            command_status_v = runShellCommandAndReturnOutputAsList(createSharedCluster)
                            if command_status_v[1] != 0:
                                current_app.logger.error(
                                    "Failed to run command to create shared cluster " + str(command_status_v[0]))
                                d = {
                                    "responseType": "ERROR",
                                    "msg": "Failed to run command to create shared cluster " + str(command_status_v[0]),
                                    "ERROR_CODE": 500
                                }
                                return jsonify(d), 500
            count = 0
            if isCheck:
                command_status = runShellCommandAndReturnOutputAsList(podRunninng)
                if command_status[1] != 0:
                    current_app.logger.error("Failed to check pods are running " + str(command_status[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to check pods are running " + str(command_status[0]),
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
                while not verifyPodsAreRunning(shared_cluster_name, command_status[0],
                                               RegexPattern.running) and count < 60:
                    command_status = runShellCommandAndReturnOutputAsList(podRunninng)
                    if command_status[1] != 0:
                        current_app.logger.error("Failed to check pods are running " + str(command_status[0]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to check pods are running " + str(command_status[0]),
                            "ERROR_CODE": 500
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
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            commands = ["tanzu", "management-cluster", "kubeconfig", "get", management_cluster, "--admin"]
            kubeContextCommand = grabKubectlCommand(commands, RegexPattern.SWITCH_CONTEXT_KUBECTL)
            if kubeContextCommand is None:
                current_app.logger.error("Failed to get switch to management cluster context command")
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get switch to management cluster context command",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            lisOfSwitchContextCommand = str(kubeContextCommand).split(" ")
            status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand)
            if status[1] != 0:
                current_app.logger.error("Failed to get switch to management cluster context " + str(status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get switch to management cluster context " + str(status[0]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            lisOfCommand = ["kubectl", "label", "cluster.cluster.x-k8s.io/" + shared_cluster_name,
                            "cluster-role.tkg.tanzu.vmware.com/tanzu-services=""", "--overwrite=true"]
            status = runShellCommandAndReturnOutputAsList(lisOfCommand)
            if status[1] != 0:
                current_app.logger.error("Failed to apply k8s label " + str(status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to apply k8s label " + str(status[0]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            lisOfCommand = ["kubectl", "label", "cluster",
                            shared_cluster_name, AkoType.KEY + "=" + AkoType.VALUE, "--overwrite=true"]
            status = runShellCommandAndReturnOutputAsList(lisOfCommand)
            if status[1] != 0:
                if not str(status[0]).__contains__("already has a value"):
                    current_app.logger.error("Failed to apply ako label " + str(status[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to apply ako label " + str(status[0]),
                        "ERROR_CODE": 500
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
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            lisOfSwitchContextCommand_shared = str(kubeContextCommand_shared).split(" ")
            status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand_shared)
            if status[1] != 0:
                current_app.logger.error("Failed to get switch to shared cluster context " + str(status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get switch to shared cluster context " + str(status[0]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            current_app.logger.info("Switched to " + shared_cluster_name + " context")
            if checkEnableIdentityManagement(env):
                current_app.logger.info("Validating pinniped installation status")
                check_pinniped = checkPinnipedInstalled()
                if check_pinniped[1] != 200:
                    current_app.logger.error(check_pinniped[0].json['msg'])
                    d = {
                        "responseType": "ERROR",
                        "msg": check_pinniped[0].json['msg'],
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
                if env == Env.VSPHERE:
                    cluster_admin_users = \
                        request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                            'tkgSharedserviceRbacUserRoleSpec'][
                            'clusterAdminUsers']
                    admin_users = \
                        request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                            'tkgSharedserviceRbacUserRoleSpec'][
                            'adminUsers']
                    edit_users = \
                        request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                            'tkgSharedserviceRbacUserRoleSpec'][
                            'editUsers']
                    view_users = \
                        request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                            'tkgSharedserviceRbacUserRoleSpec'][
                            'viewUsers']
                elif env == Env.VCF:
                    cluster_admin_users = \
                        request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                            'tkgSharedserviceRbacUserRoleSpec'][
                            'clusterAdminUsers']
                    admin_users = \
                        request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                            'tkgSharedserviceRbacUserRoleSpec'][
                            'adminUsers']
                    edit_users = \
                        request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                            'tkgSharedserviceRbacUserRoleSpec'][
                            'editUsers']
                    view_users = \
                        request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                            'tkgSharedserviceRbacUserRoleSpec'][
                            'viewUsers']
                rbac_user_status = createRbacUsers(shared_cluster_name, isMgmt=False, env=env, edit_users=edit_users,
                                                   cluster_admin_users=cluster_admin_users, admin_users=admin_users,
                                                   view_users=view_users)
                if rbac_user_status[1] != 200:
                    current_app.logger.error(rbac_user_status[0].json['msg'])
                    d = {
                        "responseType": "ERROR",
                        "msg": rbac_user_status[0].json['msg'],
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
                current_app.logger.info("Successfully created RBAC for all the provided users")
            else:
                current_app.logger.info("Identity Management is not enabled")
            podRunninng_ako_main = ["kubectl", "get", "pods", "-A"]
            podRunninng_ako_grep = ["grep", AppName.AKO]
            count_ako = 0
            command_status_ako = grabPipeOutput(podRunninng_ako_main, podRunninng_ako_grep)
            found = False
            if verifyPodsAreRunning(AppName.AKO, command_status_ako[0], RegexPattern.RUNNING):
                found = True

            while not verifyPodsAreRunning(AppName.AKO, command_status_ako[0],
                                           RegexPattern.RUNNING) and count_ako < 20:
                command_status = grabPipeOutput(podRunninng_ako_main, podRunninng_ako_grep)
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
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            if count_ako > 30:
                for i in tqdm(range(60), desc="Waiting for ako pods to be uup…", ascii=False, ncols=75):
                    time.sleep(1)
        else:
            current_app.logger.info(shared_cluster_name + " cluster is already deployed and running ")
    if tmc_flag and (Tkg_version.TKG_VERSION != "1.5"):
        isSharedProxy = "false"
        if checkSharedServiceProxyEnabled(env):
            isSharedProxy = "true"
        state = registerWithTmcOnSharedAndWorkload(env, shared_cluster_name, isSharedProxy, "shared")
        if state[1] != 200:
            current_app.logger.error(state[0].json['msg'])
            d = {
                "responseType": "ERROR",
                "msg": state[0].json['msg'],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    elif checkTmcEnabled(env) and Tkg_version.TKG_VERSION == "1.5":
        current_app.logger.info("Cluster is already deployed via TMC")
        if checkDataProtectionEnabled(env, "shared"):
            is_enabled = enable_data_protection(env, shared_cluster_name, management_cluster)
            if not is_enabled[0]:
                current_app.logger.error(is_enabled[1])
                d = {
                    "responseType": "ERROR",
                    "msg": is_enabled[1],
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            current_app.logger.info(is_enabled[1])
        else:
            current_app.logger.info("Data protection not enabled for cluster " + shared_cluster_name)
    elif checkTmcEnabled(env):
        current_app.logger.info("Cluster is already deployed via TMC")
    else:
        current_app.logger.info("TMC is disabled")
    to = registerTanzuObservability(shared_cluster_name, env, size)
    if to[1] != 200:
        current_app.logger.error(to[0].json['msg'])
        return to[0], to[1]
    d = {
        "responseType": "SUCCESS",
        "msg": "Successfully deployed  cluster " + shared_cluster_name,
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def waitForGrepProcess(list1, list2, podName, dir):
    time.sleep(30)
    count_cert = 0
    running = False
    try:
        while count_cert < 60:
            cert_state = grabPipeOutputChagedDir(list1, list2, dir)
            if verifyPodsAreRunning(podName, cert_state[0], RegexPattern.RUNNING):
                running = True
                break
            time.sleep(30)
            count_cert = count_cert + 1
            current_app.logger.info("Waited for  " + str(count_cert * 30) + "s, retrying.")
    except Exception as e:
        current_app.logger.error(" Failed to verify pod running ")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to verify pod running",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500, count_cert
    if not running:
        current_app.logger.error(podName + " is not running on waiting " + str(count_cert * 30) + "s")
        d = {
            "responseType": "ERROR",
            "msg": podName + " is not running on waiting " + str(count_cert * 30) + "s",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500, count_cert
    d = {
        "responseType": "ERROR",
        "msg": "Successfully running " + podName + " ",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200, count_cert


def checkCertManagerRunning():
    list1 = ["kubectl", "get", "pods", "-A"]
    list2 = ["grep", "cert-manager"]
    dir = Extentions.TKG_EXTENTION_LOCATION
    podName = "cert-manager"
    try:
        cert_state = grabPipeOutputChagedDir(list1, list2, dir)
        if cert_state[1] != 0:
            current_app.logger.error("Failed to get " + podName + " " + cert_state[0])
            return False
        if verifyPodsAreRunning(podName, cert_state[0], RegexPattern.RUNNING):
            current_app.logger.info("Cert Manager is Running.")
            return True
    except Exception as e:
        return False
    return False


def waitForProcess(list1, podName):
    time.sleep(30)
    count_cert = 0
    running = False
    while count_cert < 60:
        cert_state = runShellCommandAndReturnOutputAsList(list1)
        time.sleep(30)
        if verifyPodsAreRunning(podName, cert_state[0], RegexPattern.RECONCILE_SUCCEEDED):
            running = True
            break
        count_cert = count_cert + 1
        current_app.logger.info("Waited for  " + str(count_cert * 30) + "s, retrying.")
    if not running:
        current_app.logger.error(podName + " is not running on waiting " + str(count_cert * 30) + "s")
        d = {
            "responseType": "ERROR",
            "msg": podName + " is not running on waiting " + str(count_cert * 30) + "s",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500, count_cert
    current_app.logger.info("Successfully running " + podName)
    d = {
        "responseType": "SUCCESS",
        "msg": "Successfully running" + podName,
        "ERROR_CODE": 500
    }
    return jsonify(d), 200, count_cert
