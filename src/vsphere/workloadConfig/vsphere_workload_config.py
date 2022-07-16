from flask import Blueprint
import logging
import sys

logger = logging.getLogger(__name__)
from flask import jsonify, request, make_response
import requests
from tqdm import tqdm
import time
import os
import json
from common.model.vsphereSpec import VsphereMasterSpec

vsphere_workload_config = Blueprint("vsphere_workload_config", __name__, static_folder="workloadConfig")
from flask import current_app
import ruamel
import sys
import base64

sys.path.append(".../")
from common.operation.vcenter_operations import createResourcePool, create_folder, checkforIpAddress, getSi, \
    checkVmPresent
from common.operation.constants import ResourcePoolAndFolderName, Vcenter, GroupNameCgw, GroupNameMgw, FirewallRuleMgw, \
    ControllerLocation, Env, Policy_Name, Paths, TmcUser
from common.common_utilities import isAviHaEnabled,getDomainName, getTier1Details, grabNsxtHeaders, getList, obtain_second_csrf, \
    preChecks, get_avi_version, envCheck, getClusterStatusOnTanzu, \
    getCloudStatus, getSECloudStatus, createResourceFolderAndWait, getVrfAndNextRoutId, addStaticRoute, VrfType, \
    checkAirGappedIsEnabled, registerWithTmcOnSharedAndWorkload, deployCluster, registerTanzuObservability, \
    checkWorkloadProxyEnabled, registerTSM, getNetworkFolder, getNetworkIp, createNsxtSegment, createGroup, \
    createFirewallRule, checkObjectIsPresentAndReturnPath, downloadAndPushKubernetesOvaMarketPlace, isEnvTkgs_wcp, \
    checkTmcEnabled, isEnvTkgs_ns, checTSMEnabled, checkToEnabled, getKubeVersionFullName, getNetworkPathTMC, \
    createProxyCredentialsTMC, checkTmcRegister, checkDataProtectionEnabled, enable_data_protection, \
    checkEnableIdentityManagement, checkPinnipedInstalled, checkPinnipedServiceStatus, \
    checkPinnipedDexServiceStatus, createRbacUsers, createClusterFolder
from common.operation.ShellHelper import runShellCommandAndReturnOutput, grabKubectlCommand, grabIpAddress, \
    verifyPodsAreRunning, grabPipeOutput, runShellCommandAndReturnOutputAsList, runProcess, \
    runShellCommandAndReturnOutputAsListWithChangedDir, grabPipeOutputChagedDir, runShellCommandWithPolling
from common.operation.constants import SegmentsName, RegexPattern, Versions, AkoType, AppName, FirewallRuleCgw, \
    ServiceName, \
    Cloud, Type, PLAN, Sizing, Tkg_version
from vsphere.managementConfig.vsphere_management_config import updateIpam_profile, getIpam, enableDhcpForManagementNetwork, \
    updateNetworkWithIpPools, getNetworkDetails, getClusterUrl, createSECloud, getNetworkUrl, \
    seperateNetmaskAndIp
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from vmc.workloadConfig.workload_config import connectToWorkLoadCluster
from vsphere.workloadConfig.vsphere_tkgs_workload import createTkgWorkloadCluster, createNameSpace

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


@vsphere_workload_config.route("/api/tanzu/vsphere/workload/preconfig", methods=['POST'])
def workloadConfig():
    network_config = networkConfig()
    if network_config[1] != 200:
        current_app.logger.error(network_config[0].json['msg'])
        d = {
            "responseType": "ERROR",
            "msg": "Failed to Config workload cluster " + str(network_config[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    deploy_workload = deploy()
    if deploy_workload[1] != 200:
        current_app.logger.error(str(deploy_workload[0].json['msg']))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to deploy extention " + str(deploy_workload[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    d = {
        "responseType": "SUCCESS",
        "msg": "Workload cluster configured Successfully",
        "ERROR_CODE": 200
    }
    current_app.logger.info("Workload cluster configured Successfully")
    return jsonify(d), 200


@vsphere_workload_config.route("/api/tanzu/vsphere/workload/network-config", methods=['POST'])
def networkConfig():
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
    env = env[0]
    aviVersion = get_avi_version(env)
    password = current_app.config['VC_PASSWORD']
    vcenter_username = current_app.config['VC_USER']
    vcenter_ip = current_app.config['VC_IP']
    cluster_name = current_app.config['VC_CLUSTER']
    data_center = current_app.config['VC_DATACENTER']
    data_store = current_app.config['VC_DATASTORE']
    refToken = request.get_json(force=True)['envSpec']['marketplaceSpec']['refreshToken']
    if env == Env.VSPHERE or env == Env.VCF:
        if not (isEnvTkgs_ns(env) or isEnvTkgs_wcp(env)):
            kubernetes_ova_os = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadBaseOs"]
            kubernetes_ova_version = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadKubeVersion"]
            if refToken:
                current_app.logger.info("Kubernetes OVA configs for workload cluster")
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
    workload_network_name = request.get_json(force=True)['tkgWorkloadDataNetwork'][
            'tkgWorkloadDataNetworkName']
    if env == Env.VCF:
        try:
            gatewayAddress = request.get_json(force=True)['tkgWorkloadDataNetwork'][
                'tkgWorkloadDataNetworkGatewayCidr']
            dnsServers = request.get_json(force=True)['envSpec']['infraComponents']['dnsServersIp']
            network = getNetworkIp(gatewayAddress)
            shared_segment = createNsxtSegment(workload_network_name, gatewayAddress,
                                               None,
                                               None, dnsServers, network, False)
            if shared_segment[1] != 200:
                current_app.logger.error("Failed to create shared segments" + str(shared_segment[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create shared segments" + str(shared_segment[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
        except Exception as e:
            current_app.logger.error("Failed to configure vcf workload " + str(e))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to configure vcf workload " + str(e),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    avi_fqdn = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController01Fqdn']
    ##########################################################
    if isAviHaEnabled(env):
        ip = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviClusterFqdn']
    else:
        ip = avi_fqdn
    if ip is None:
        current_app.logger.error("Failed to get ip of avi controller")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get ip of avi controller",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        current_app.logger.error("Failed to get csrf from new set password")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get csrf from new set password",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    get_cloud = getCloudStatus(ip, csrf2, aviVersion, Cloud.CLOUD_NAME_VSPHERE)
    if get_cloud[0] is None:
        current_app.logger.error("Failed to get cloud status " + str(get_cloud[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get cloud status " + str(get_cloud[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    isGen = False
    if get_cloud[0] == "NOT_FOUND":
        current_app.logger.error("Requested cloud is not created")
        d = {
            "responseType": "ERROR",
            "msg": "Requested cloud is not created",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    else:
        cloud_url = get_cloud[0]
    cluster_name = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterCluster"]
    cluster_status = getClusterUrl(ip, csrf2, cluster_name, aviVersion)
    if cluster_status[0] is None:
        current_app.logger.error("Failed to get cluster details" + str(cluster_status[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get cluster details " + str(cluster_status[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if cluster_status[0] == "NOT_FOUND":
        current_app.logger.error("Failed to get cluster details" + str(cluster_status[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get cluster details " + str(cluster_status[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    get_ipam = getIpam(ip, csrf2, Cloud.IPAM_NAME_VSPHERE, aviVersion)
    if get_ipam[0] is None:
        current_app.logger.error("Failed to get se Ipam " + str(get_ipam[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get ipam " + str(get_ipam[1]),
            "ERROR_CODE": 500
            }
        return jsonify(d), 500

    update = updateIpam_profile(ip, csrf2, workload_network_name, aviVersion)
    if update[0] is None:
        current_app.logger.error("Failed to update se Ipam " + str(update[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to update ipam " + str(update[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    get_se_cloud = getSECloudStatus(ip, csrf2, aviVersion, Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE)
    if get_se_cloud[0] is None:
        current_app.logger.error("Failed to get se cloud status " + str(get_se_cloud[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get se cloud status " + str(get_se_cloud[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    isGen = False
    if get_se_cloud[0] == "NOT_FOUND":
        isGen = True
        current_app.logger.info("Creating New se cloud " + Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE)
        cloud_se = createSECloud(ip, csrf2, cloud_url, Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE, cluster_status[0],
                                 data_store, aviVersion)
        if cloud_se[0] is None:
            current_app.logger.error("Failed to create se cloud " + str(cloud_se[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create  se cloud " + str(cloud_se[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        se_cloud_url = cloud_se[0]
    else:
        se_cloud_url = get_se_cloud[0]
    management_cluster = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
        'tkgMgmtClusterName']
    data_network_workload = request.get_json(force=True)["tkgWorkloadDataNetwork"]["tkgWorkloadDataNetworkName"]
    get_management_data_pg = getNetworkUrl(ip, csrf2, data_network_workload, aviVersion)
    if get_management_data_pg[0] is None:
        current_app.logger.error("Failed to get workload data network details " + str(get_management_data_pg[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get workloadt data network details " + str(get_management_data_pg[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    startIp = request.get_json(force=True)["tkgWorkloadDataNetwork"]["tkgWorkloadAviServiceIpStartRange"]
    endIp = request.get_json(force=True)["tkgWorkloadDataNetwork"]["tkgWorkloadAviServiceIpEndRange"]
    prefixIpNetmask = seperateNetmaskAndIp(
        request.get_json(force=True)["tkgWorkloadDataNetwork"]["tkgWorkloadDataNetworkGatewayCidr"])
    getManagementDetails_data_pg = getNetworkDetails(ip, csrf2, get_management_data_pg[0], startIp, endIp,
                                                     prefixIpNetmask[0], prefixIpNetmask[1], aviVersion)
    if getManagementDetails_data_pg[0] is None:
        current_app.logger.error(
            "Failed to get workload data network details " + str(getManagementDetails_data_pg[2]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get workload data network details " + str(getManagementDetails_data_pg[2]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if getManagementDetails_data_pg[0] == "AlreadyConfigured":
        current_app.logger.info("Ip pools are already configured.")
    else:
        update_resp = updateNetworkWithIpPools(ip, csrf2, get_management_data_pg[0], "managementNetworkDetails.json",
                                               aviVersion)
        if update_resp[0] != 200:
            current_app.logger.error("Failed to update ip " + str(update_resp[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get management network details " + str(update_resp[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    with open("./newCloudInfo.json", 'r') as file2:
        new_cloud_json = json.load(file2)
    uuid = None
    try:
        uuid = new_cloud_json["uuid"]
    except:
        for re in new_cloud_json["results"]:
            if re["name"] == Cloud.CLOUD_NAME_VSPHERE:
                uuid = re["uuid"]
    if uuid is None:
        current_app.logger.error("uuid not found ")
        d = {
            "responseType": "ERROR",
            "msg": "uuid not found ",
            "ERROR_CODE": 500
        }
        return jsonify(d), "NOT_FOUND"
    vrf = getVrfAndNextRoutId(ip, csrf2, uuid, VrfType.GLOBAL, prefixIpNetmask[0], aviVersion)
    if vrf[0] is None or vrf[1] == "NOT_FOUND":
        current_app.logger.error("Vrf not found " + str(vrf[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Vrf not found " + str(vrf[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if vrf[1] != "Already_Configured":
        current_app.logger.info("Routing is not cofigured , configuring.")
        ad = addStaticRoute(ip, csrf2, vrf[0], prefixIpNetmask[0], vrf[1], aviVersion)
        if ad[0] is None:
            current_app.logger.error("Failed to add static route " + str(ad[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Vrf not found " + str(ad[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Routing is cofigured")
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
    podRunninng_ako_main = ["kubectl", "get", "pods", "-A"]
    podRunninng_ako_grep = ["grep", AppName.AKO]
    time.sleep(30)
    timer = 30
    ako_pod_running = False
    while timer < 600:
        current_app.logger.info("Check AKO pods are running. Waited for " + str(timer) + "s retrying")
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
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    wip = getVipNetworkIpNetMask(ip, csrf2, data_network_workload, aviVersion)
    if wip[0] is None or wip[0] == "NOT_FOUND":
        current_app.logger.error("Failed to get wip netmask ")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get wip netmask ",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    workload_cluster_name = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadClusterName']
    if not createClusterFolder(workload_cluster_name):
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create directory: " + Paths.CLUSTER_PATH + workload_cluster_name,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    current_app.logger.info(
        "The config files for shared services cluster will be located at: " + Paths.CLUSTER_PATH + workload_cluster_name)
    createAkoFile(ip, workload_cluster_name, wip[0], data_network_workload, env)
    lisOfCommand = ["kubectl", "apply", "-f", Paths.CLUSTER_PATH + workload_cluster_name + "/ako_vsphere_workloadset1.yaml", "--validate=false"]
    status = runShellCommandAndReturnOutputAsList(lisOfCommand)
    if status[1] != 0:
        if not str(status[0]).__contains__("already has a value"):
            current_app.logger.error("Failed to apply ako" + str(status[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to apply ako label " + str(status[0]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    current_app.logger.info("Applied ako successfully")
    d = {
        "responseType": "SUCCESS",
        "msg": "Successfully configured workload preconfig",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


@vsphere_workload_config.route("/api/tanzu/vsphere/workload/createnamespace", methods=['POST'])
def create_name_space():
    password = current_app.config['VC_PASSWORD']
    vcenter_username = current_app.config['VC_USER']
    vcenter_ip = current_app.config['VC_IP']
    name_space = createNameSpace(vcenter_ip, vcenter_username, password)
    if name_space[0] is None:
        current_app.logger.error("Failed to create name space " + str(name_space[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create name space " + str(name_space[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    current_app.logger.info("Successfully created name space")
    d = {
        "responseType": "SUCCESS",
        "msg": "Successfully created name space",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


@vsphere_workload_config.route("/api/tanzu/vsphere/workload/createworkload", methods=['POST'])
def create_workload():
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
    env = env[0]
    password = current_app.config['VC_PASSWORD']
    vcenter_username = current_app.config['VC_USER']
    vcenter_ip = current_app.config['VC_IP']
    name_space = createTkgWorkloadCluster(env, vcenter_ip, vcenter_username, password)
    if name_space[0] is None:
        current_app.logger.error("Failed to create workload cluster " + str(name_space[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create workload cluster " + str(name_space[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    current_app.logger.info("Successfully created workload cluster")
    if checkTmcEnabled(env):
        current_app.logger.info("Initiating TKGs SAAS integration")
        size = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['workerNodeCount']
        workload_cluster_name = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereWorkloadClusterName']
        if checkToEnabled(env):
            to = registerTanzuObservability(workload_cluster_name, env, size)
            if to[1] != 200:
                current_app.logger.error(to[0])
                d = {
                    "responseType": "SUCCESS",
                    "msg": "TO registration failed for workload cluster",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
        else:
            current_app.logger.info("Tanzu Observability not enabled")
        if checTSMEnabled(env):
            cluster_version = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereWorkloadClusterVersion']
            if not cluster_version.startswith('v'):
                cluster_version = 'v' + cluster_version
            if not cluster_version.startswith("v1.18.19+vmware.1"):
                current_app.logger.warn("On vSphere with Tanzu platform, TSM supports the Kubernetes version 1.18.19+vmware.1")
                current_app.logger.warn("For latest updates please check - "
                                        "https://docs.vmware.com/en/VMware-Tanzu-Service-Mesh/services/tanzu-service-mesh-environment-requirements-and-supported-platforms/GUID-D0B939BE-474E-4075-9A65-3D72B5B9F237.html")
            tsm = registerTSM(workload_cluster_name, env, size)
            if tsm[1] != 200:
                current_app.logger.error("TSM registration failed for workload cluster")
                d = {
                    "responseType": "SUCCESS",
                    "msg": "TSM registration failed for workload cluster",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
        else:
            current_app.logger.info("TSM not enabled")

        if checkDataProtectionEnabled(Env.VSPHERE, "workload"):
            supervisor_cluster = request.get_json(force=True)['envSpec']["saasEndpoints"]['tmcDetails'][
                'tmcSupervisorClusterName']
            is_enabled = enable_data_protection(env, workload_cluster_name, supervisor_cluster)
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
            current_app.logger.info("Data Protection is not enabled for cluster " + workload_cluster_name)
    else:
        current_app.logger.info("TMC not enabled.")

    d = {
        "responseType": "SUCCESS",
        "msg": "Successfully created workload cluster",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


@vsphere_workload_config.route("/api/tanzu/vsphere/workload/config", methods=['POST'])
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
    if env == Env.VCF:
        try:
            gatewayAddress = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadGatewayCidr']
            dhcp_start = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadDhcpStartRange']
            dhcp_end = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadDhcpEndRange']
            dnsServers = request.get_json(force=True)['envSpec']['infraComponents']['dnsServersIp']
            network = getNetworkIp(gatewayAddress)
            workload_network_name = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadNetworkName']
            workload_segment = createNsxtSegment(workload_network_name, gatewayAddress,
                                                 dhcp_start,
                                                 dhcp_end, dnsServers, network, True)
            if workload_segment[1] != 200:
                current_app.logger.error("Failed to create workload segments" + str(workload_segment[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create workload segments" + str(workload_segment[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            worklod_group = createGroup(GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW,
                                        workload_network_name,
                                        False, None)
            if worklod_group[1] != 200:
                current_app.logger.error(
                    "Failed to create  group " + GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW + " " + str(
                        worklod_group[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create group " + GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW + " " + str(
                        worklod_group[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            headers_ = grabNsxtHeaders()
            if headers_[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to nsxt info " + str(headers_[1]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            domainName = getDomainName(headers_, "default")
            if domainName[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get domain name " + str(domainName[1]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            uri = "https://" + headers_[2] + "/policy/api/v1/infra/domains/" + domainName[0] + "/groups"
            output = getList(headers_[1], uri)
            if output[1] != 200:
                current_app.logger.error("Failed to get list of groups " + str(output[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get list of groups " + str(output[0]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            teir1 = getTier1Details(headers_)
            if teir1[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to tier1 details" + str(headers_[1]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            payload = {"action": "ALLOW",
                       "display_name": FirewallRuleCgw.DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_DNS,
                       "logged": False,
                       "source_groups": [
                           checkObjectIsPresentAndReturnPath(output[0],
                                                             GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW)[
                               1],
                           checkObjectIsPresentAndReturnPath(output[0],
                                                             GroupNameCgw.DISPLAY_NAME_VCF_TKG_Management_Network_Group_CGW)[
                               1]
                       ],
                       "destination_groups": [
                           checkObjectIsPresentAndReturnPath(output[0],
                                                             GroupNameCgw.DISPLAY_NAME_VCF_DNS_IPs_Group)[
                               1],
                           checkObjectIsPresentAndReturnPath(output[0],
                                                             GroupNameCgw.DISPLAY_NAME_VCF_NTP_IPs_Group)[
                               1],
                           checkObjectIsPresentAndReturnPath(output[0],
                                                             GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW)[
                               1],
                           checkObjectIsPresentAndReturnPath(output[0],
                                                             GroupNameCgw.DISPLAY_NAME_VCF_CLUSTER_VIP_NETWORK_Group_CGW)[
                               1]
                       ],
                       "services": ["/infra/services/DNS",
                                    "/infra/services/DNS-UDP",
                                    "/infra/services/NTP",
                                    "/infra/services/" + ServiceName.KUBE_VIP_VCF_SERVICE],
                       "scope": [teir1[0]]
                       }
            fw = createFirewallRule(Policy_Name.POLICY_NAME, FirewallRuleCgw.DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_DNS,
                                    payload)
            if fw[1] != 200:
                current_app.logger.error(
                    "Failed to create firewall " + FirewallRuleCgw.DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_DNS + " " + str(
                        fw[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create firewall " + GroupNameCgw.DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_DNS + " " + str(
                        fw[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            payload = {"action": "ALLOW",
                       "display_name": FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_WORKLOAD_to_vCenter,
                       "logged": False,
                       "source_groups": [
                           checkObjectIsPresentAndReturnPath(output[0],
                                                             GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW)[
                               1]
                       ],
                       "destination_groups": [
                           checkObjectIsPresentAndReturnPath(output[0],
                                                             GroupNameCgw.DISPLAY_NAME_VCF_vCenter_IP_Group)[
                               1]
                       ],
                       "services": ["/infra/services/HTTPS"],
                       "scope": [teir1[0]]
                       }
            fw = createFirewallRule(Policy_Name.POLICY_NAME, FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_WORKLOAD_to_vCenter,
                                    payload)
            if fw[1] != 200:
                current_app.logger.error(
                    "Failed to create firewall " + FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_WORKLOAD_to_vCenter + " " + str(
                        fw[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create firewall " + GroupNameCgw.DISPLAY_NAME_VCF_TKG_WORKLOAD_to_vCenter + " " + str(
                        fw[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            payload = {"action": "ALLOW",
                       "display_name": FirewallRuleCgw.DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_to_Internet,
                       "logged": False,
                       "source_groups": [checkObjectIsPresentAndReturnPath(output[0],
                                                                           GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW)[
                                             1]
                                         ],
                       "destination_groups": ["ANY"],
                       "services": ["ANY"],
                       "scope": [teir1[0]]
                       }
            fw = createFirewallRule(Policy_Name.POLICY_NAME,
                                    FirewallRuleCgw.DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_to_Internet,
                                    payload)
            if fw[1] != 200:
                current_app.logger.error(
                    "Failed to create firewall " + FirewallRuleCgw.DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_to_Internet + " " + str(
                        fw[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create firewall " + GroupNameCgw.DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_to_Internet + " " + str(
                        fw[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
        except Exception as e:
            current_app.logger.error("Failed to configure vcf workload " + str(e))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to configure vcf workload " + str(e),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    kubernetes_ova_version = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadKubeVersion"]
    pod_cidr = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadClusterCidr']
    service_cidr = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadServiceCidr']
    avi_fqdn = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController01Fqdn']
    if isAviHaEnabled(env):
        ip = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviClusterFqdn']
    else:
        ip = avi_fqdn
    if ip is None:
        current_app.logger.error("Failed to get ip of avi controller")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get ip of avi controller",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        current_app.logger.error("Failed to get csrf from new set password")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get csrf from new set password",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    create = createResourceFolderAndWait(vcenter_ip, vcenter_username, password,
                                         cluster_name, data_center,
                                         ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL_VSPHERE,
                                         ResourcePoolAndFolderName.WORKLOAD_FOLDER_VSPHERE, parent_resourcePool)
    if create[1] != 200:
        current_app.logger.error("Failed to create resource pool and folder " + create[0].json['msg'])
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create resource pool " + str(create[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
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
    cluster_plan = request.get_json(force=True)['tkgWorkloadComponents'][
        'tkgWorkloadDeploymentType']
    if cluster_plan == PLAN.DEV_PLAN:
        additional_command = ""
        machineCount = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadWorkerMachineCount']
    elif cluster_plan == PLAN.PROD_PLAN:
        additional_command = "--high-availability"
        machineCount = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadWorkerMachineCount']
    else:
        current_app.logger.error("Un supported control plan provided please specify prod or dev " + cluster_plan)
        d = {
            "responseType": "ERROR",
            "msg": "Un supported control plan provided please specify prod or dev " + cluster_plan,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    size = str(request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadSize'])
    if size.lower() == "small":
        cpu = Sizing.small['CPU']
        memory = Sizing.small['MEMORY']
        disk = Sizing.small['DISK']
    elif size.lower() == "medium":
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
        cpu = request.get_json(force=True)['tkgWorkloadComponents'][
            'tkgWorkloadCpuSize']
        disk = request.get_json(force=True)['tkgWorkloadComponents'][
            'tkgWorkloadStorageSize']
        control_plane_mem_gb = request.get_json(force=True)['tkgWorkloadComponents'][
            'tkgWorkloadMemorySize']
        memory = str(int(control_plane_mem_gb) * 1024)
    else:
        current_app.logger.error("Provided cluster size: " + size + "is not supported, please provide one of: "
                                                                    "small/medium/large/extra-large/custom")
        d = {
            "responseType": "ERROR",
            "msg": "Provided cluster size: " + size + "is not supported, please provide one of: "
                                                      "small/medium/large/extra-large/custom",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    deployWorkload = False
    workload_cluster_name = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadClusterName']
    management_cluster = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
        'tkgMgmtClusterName']
    workload_network = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadNetworkName']
    vsphere_password = password
    _base64_bytes = vsphere_password.encode('ascii')
    _enc_bytes = base64.b64encode(_base64_bytes)
    vsphere_password = _enc_bytes.decode('ascii')
    dhcp = enableDhcpForManagementNetwork(ip, csrf2, workload_network, aviVersion)
    if dhcp[0] is None:
        current_app.logger.error("Failed to enable dhcp " + str(dhcp[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to enable dhcp " + str(dhcp[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    datacenter_path = "/" + data_center
    datastore_path = datacenter_path + "/datastore/" + data_store
    workload_folder_path = datacenter_path + "/vm/" + ResourcePoolAndFolderName.WORKLOAD_FOLDER_VSPHERE
    if parent_resourcePool:
        workload_resource_path = datacenter_path + "/host/" + cluster_name + "/Resources/" + parent_resourcePool + "/" + ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL_VSPHERE
    else:
        workload_resource_path = datacenter_path + "/host/" + cluster_name + "/Resources/" + ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL_VSPHERE
    workload_network_path = getNetworkFolder(workload_network, vcenter_ip, vcenter_username, password)
    if not workload_network_path:
        current_app.logger.error("Network folder not found for " + workload_network)
        d = {
            "responseType": "ERROR",
            "msg": "Network folder not found for " + workload_network,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    if Tkg_version.TKG_VERSION == "1.5" and checkTmcEnabled(env):
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

        clusterGroup = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadClusterGroupName']

        if not clusterGroup:
            clusterGroup = "default"

        workload_network_folder_path = getNetworkPathTMC(workload_network, vcenter_ip, vcenter_username, password)
        if checkWorkloadProxyEnabled(env) and not checkTmcRegister(workload_cluster_name, False):
            proxy_name_state = createProxyCredentialsTMC(env, workload_cluster_name, "true", "workload", register=False)
            if proxy_name_state[1] != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": proxy_name_state[0],
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            proxy_name = "arcas-" + workload_cluster_name + "-tmc-proxy"
            if cluster_plan.lower() == PLAN.PROD_PLAN:
                createWorkloadCluster = ["tmc", "cluster", "create", "-t", "tkg-vsphere", "-n", workload_cluster_name,
                                         "-m",
                                         management_cluster, "-p", "default", "--cluster-group", clusterGroup,
                                         "--ssh-key", re, "--version", version, "--datacenter", datacenter_path,
                                         "--datastore",
                                         datastore_path, "--folder", workload_folder_path, "--resource-pool",
                                         workload_resource_path,
                                         "--workspace-network", workload_network_folder_path, "--control-plane-cpu",
                                         cpu,
                                         "--control-plane-disk-gib", disk, "--control-plane-memory-mib", memory,
                                         "--worker-node-count", machineCount, "--worker-cpu", cpu, "--worker-disk-gib",
                                         disk, "--worker-memory-mib", memory, "--pods-cidr-blocks", pod_cidr,
                                       "--service-cidr-blocks", service_cidr, "--high-availability", "--proxy-name",
                                       proxy_name]
            else:
                createWorkloadCluster = ["tmc", "cluster", "create", "-t", "tkg-vsphere", "-n", workload_cluster_name,
                                         "-m",
                                         management_cluster, "-p", "default", "--cluster-group", clusterGroup,
                                         "--ssh-key", re, "--version", version, "--datacenter", datacenter_path,
                                         "--datastore",
                                         datastore_path, "--folder", workload_folder_path, "--resource-pool",
                                         workload_resource_path,
                                         "--workspace-network", workload_network_folder_path, "--control-plane-cpu",
                                         cpu,
                                         "--control-plane-disk-gib", disk, "--control-plane-memory-mib", memory,
                                         "--worker-node-count", machineCount, "--worker-cpu", cpu, "--worker-disk-gib",
                                         disk, "--worker-memory-mib", memory, "--pods-cidr-blocks", pod_cidr,
                                       "--service-cidr-blocks", service_cidr, "--proxy-name", proxy_name]
        else:
            if cluster_plan.lower() == PLAN.PROD_PLAN:
                createWorkloadCluster = ["tmc", "cluster", "create", "-t", "tkg-vsphere", "-n", workload_cluster_name,
                                         "-m",
                                         management_cluster, "-p", "default", "--cluster-group", clusterGroup,
                                         "--ssh-key", re, "--version", version, "--datacenter", datacenter_path,
                                         "--datastore",
                                         datastore_path, "--folder", workload_folder_path, "--resource-pool",
                                         workload_resource_path,
                                         "--workspace-network", workload_network_folder_path, "--control-plane-cpu",
                                         cpu,
                                         "--control-plane-disk-gib", disk, "--control-plane-memory-mib", memory,
                                         "--worker-node-count", machineCount, "--worker-cpu", cpu, "--worker-disk-gib",
                                         disk, "--worker-memory-mib", memory, "--pods-cidr-blocks", pod_cidr,
                                       "--service-cidr-blocks", service_cidr, "--high-availability"]
            else:
                createWorkloadCluster = ["tmc", "cluster", "create", "-t", "tkg-vsphere", "-n", workload_cluster_name,
                                         "-m",
                                         management_cluster, "-p", "default", "--cluster-group", clusterGroup,
                                         "--ssh-key", re, "--version", version, "--datacenter", datacenter_path,
                                         "--datastore",
                                         datastore_path, "--folder", workload_folder_path, "--resource-pool",
                                         workload_resource_path,
                                         "--workspace-network", workload_network_folder_path, "--control-plane-cpu",
                                         cpu,
                                         "--control-plane-disk-gib", disk, "--control-plane-memory-mib", memory,
                                         "--worker-node-count", machineCount, "--worker-cpu", cpu, "--worker-disk-gib",
                                         disk, "--worker-memory-mib", memory, "--pods-cidr-blocks", pod_cidr,
                                       "--service-cidr-blocks", service_cidr]

    isCheck = False
    found = False
    if command_status[0] is None:
        if Tkg_version.TKG_VERSION == "1.5" and checkTmcEnabled(env):
            current_app.logger.info("Deploying Workload cluster")
            for i in tqdm(range(150), desc="Waiting for folder to be available in tmc…", ascii=False, ncols=75):
                time.sleep(1)
            current_app.logger.info("Deploying workload cluster")
            os.putenv("TMC_API_TOKEN",
                      request.get_json(force=True)["envSpec"]["saasEndpoints"]['tmcDetails']['tmcRefreshToken'])
            listOfCmdTmcLogin = ["tmc", "login", "--no-configure", "-name", TmcUser.USER_VSPHERE]
            runProcess(listOfCmdTmcLogin)
            command_status = runShellCommandAndReturnOutputAsList(createWorkloadCluster)
            if command_status[1] != 0:
                current_app.logger.error("Failed to run command to create workload cluster " + str(command_status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to run command to create workload cluster " + str(command_status[0]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            else:
                current_app.logger.info("Workload cluster is successfully deployed and running " + command_status[0])
                deployWorkload = True
    else:
        if not verifyPodsAreRunning(workload_cluster_name, command_status[0], RegexPattern.running):
            isCheck = True
            if not checkTmcEnabled(env):
                current_app.logger.info("Deploying workload cluster, after verification, using tanzu 1.5")
                deploy_status = deployCluster(workload_cluster_name, cluster_plan,
                                              data_center, data_store, workload_folder_path, workload_network_path,
                                              vsphere_password,
                                              workload_resource_path, vcenter_ip, re, vcenter_username, machineCount,
                                              size, env, Type.WORKLOAD, vsSpec)
                if deploy_status[0] is None:
                    current_app.logger.error("Failed to deploy workload cluster " + deploy_status[1])
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to deploy workload cluster " + deploy_status[1],
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
            else:
                if checkTmcEnabled(env):
                    current_app.logger.info("Deploying workload cluster, after verification, using tmc")
                    os.putenv("TMC_API_TOKEN",
                              request.get_json(force=True)["envSpec"]["saasEndpoints"]['tmcDetails']['tmcRefreshToken'])
                    listOfCmdTmcLogin = ["tmc", "login", "--no-configure", "-name", TmcUser.USER_VSPHERE]
                    runProcess(listOfCmdTmcLogin)
                    command_status_v = runShellCommandAndReturnOutputAsList(createWorkloadCluster)
                    if command_status_v[1] != 0:
                        for i in tqdm(range(150), desc="Waiting for folders to be available in tmc…", ascii=False,
                                      ncols=75):
                            time.sleep(1)
                        command_status_v1 = runShellCommandAndReturnOutputAsList(createWorkloadCluster)
                        if command_status_v1[1] != 0:
                            current_app.logger.error(
                                "Failed to run command to create workload cluster " + str(command_status_v[0]))
                            d = {
                                "responseType": "ERROR",
                                "msg": "Failed to run command to create workload cluster " + str(command_status_v[0]),
                                "ERROR_CODE": 500
                            }
                            return jsonify(d), 500
        else:
            current_app.logger.info("Workload cluster is already deployed and running")
            deployWorkload = True
            found = True
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
        if verifyPodsAreRunning(workload_cluster_name, command_status[0], RegexPattern.running):
            found = True
        while not verifyPodsAreRunning(workload_cluster_name, command_status[0],
                                       RegexPattern.running) and count < 60:
            command_status_next = runShellCommandAndReturnOutputAsList(podRunninng)
            if verifyPodsAreRunning(workload_cluster_name, command_status_next[0], RegexPattern.running):
                found = True
                break
            count = count + 1
            time.sleep(30)
            current_app.logger.info("Waited for  " + str(count * 30) + "s, retrying.")
    if not found:
        current_app.logger.error(workload_cluster_name + " is not running on waiting " + str(count * 30) + "s")
        d = {
            "responseType": "ERROR",
            "msg": workload_cluster_name + " is not running on waiting " + str(count * 30) + "s",
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
    lisOfCommand = ["kubectl", "label", "cluster",
                    workload_cluster_name, AkoType.KEY + "=" + AkoType.type_ako_set]
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
    podRunninng_ako_main = ["kubectl", "get", "pods", "-A"]
    podRunninng_ako_grep = ["grep", AppName.AKO]
    count_ako = 0
    command_status_ako = grabPipeOutput(podRunninng_ako_main, podRunninng_ako_grep)
    found = False
    if verifyPodsAreRunning(AppName.AKO, command_status_ako[0], RegexPattern.RUNNING):
        found = True
    while not verifyPodsAreRunning(AppName.AKO, command_status_ako[0], RegexPattern.RUNNING) and count_ako < 20:
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
    if tmc_flag:
        if not deployWorkload:
            for i in tqdm(range(180), desc="Waiting…", ascii=False, ncols=75):
                time.sleep(1)

    current_app.logger.info("Ako pods are running on waiting " + str(count_ako * 30))
    connectToWorkload = connectToWorkLoadCluster(env)
    if connectToWorkload[1] != 200:
        current_app.logger.error("Switching context to workload failed " + connectToWorkload[0].json['msg'])
        d = {
            "responseType": "ERROR",
            "msg": "Switching context to workload failed " + connectToWorkload[0].json['msg'],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    current_app.logger.info(
        "Successfully configured workload cluster and ako pods are running on waiting " + str(count_ako * 30))
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
                request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec']['clusterAdminUsers']
            admin_users = \
                request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec'][
                    'adminUsers']
            edit_users = \
                request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec'][
                    'editUsers']
            view_users = \
                request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec'][
                    'viewUsers']
        elif env == Env.VCF:
            cluster_admin_users = \
                request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec'][
                    'clusterAdminUsers']
            admin_users = \
                request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec'][
                    'adminUsers']
            edit_users = \
                request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec'][
                    'editUsers']
            view_users = \
                request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec'][
                    'viewUsers']
        rbac_user_status = createRbacUsers(workload_cluster_name, isMgmt=False, env=env, edit_users=edit_users,
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
    if (Tkg_version.TKG_VERSION != "1.5") and checkTmcEnabled(env):
        isWorkProxy = "false"
        if checkWorkloadProxyEnabled(env):
            isWorkProxy = "true"
        state = registerWithTmcOnSharedAndWorkload(env, workload_cluster_name, isWorkProxy, "workload")
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
        if checkDataProtectionEnabled(env, "workload"):
            is_enabled = enable_data_protection(env, workload_cluster_name, management_cluster)
            if not is_enabled[0]:
                current_app.logger.error(is_enabled[1])
                d = {
                    "responseType": "ERROR",
                    "msg": is_enabled[1],
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            current_app.logger.info(is_enabled[1])
    elif checkTmcEnabled(env):
        current_app.logger.info("Cluster is already deployed via TMC")
    else:
        current_app.logger.info("TMC is disabled")
    to = registerTanzuObservability(workload_cluster_name, env, size)
    if to[1] != 200:
        current_app.logger.error(to[0].json['msg'])
        return to[0], to[1]
    tsm = registerTSM(workload_cluster_name, env, size)
    if tsm[1] != 200:
        current_app.logger.error(tsm[0].json['msg'])
        return tsm[0], tsm[1]
    d = {
        "responseType": "SUCCESS",
        "msg": "Successfully deployed  cluster " + workload_cluster_name,
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def waitForGrepProcess(list1, list2, podName, dir):
    cert_state = grabPipeOutputChagedDir(list1, list2, dir)
    if cert_state[1] != 0:
        current_app.logger.error("Failed to apply " + podName + " " + cert_state[0])
        d = {
            "responseType": "ERROR",
            "msg": "Failed to apply " + podName + " " + cert_state[0],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500, 0
    count_cert = 0
    while verifyPodsAreRunning(podName, cert_state[0], RegexPattern.RUNNING) and count_cert < 10:
        cert_state = grabPipeOutputChagedDir(list1, list2, dir)
        time.sleep(30)
        count_cert = count_cert + 1
        current_app.logger.info("Waited for  " + str(count_cert * 30) + "s, retrying.")
    if not verifyPodsAreRunning(podName, cert_state[0], RegexPattern.RUNNING):
        current_app.logger.error(podName + " is not running on waiting " + str(count_cert * 30) + "s")
        d = {
            "responseType": "ERROR",
            "msg": podName + " is not running on waiting " + str(count_cert * 30) + "s",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500, count_cert
    d = {
        "responseType": "ERROR",
        "msg": "Failed to apply " + podName + " " + cert_state[0],
        "ERROR_CODE": 500
    }

    return jsonify(d), 200, count_cert


def getVipNetworkIpNetMask(ip, csrf2, name, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    body = {}
    url = "https://" + ip + "/api/network"
    try:
        response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        else:
            for re in response_csrf.json()["results"]:
                if re['name'] == name:
                    for sub in re["configured_subnets"]:
                        return str(sub["prefix"]["ip_addr"]["addr"]) + "/" + str(sub["prefix"]["mask"]), "SUCCESS"
            else:
                next_url = None if not response_csrf.json()["next"] else response_csrf.json()["next"]
                while len(next_url) > 0:
                    response_csrf = requests.request("GET", next_url, headers=headers, data=body, verify=False)
                    for re in response_csrf.json()["results"]:
                        if re['name'] == name:
                            for sub in re["configured_subnets"]:
                                return str(sub["prefix"]["ip_addr"]["addr"]) + "/" + str(
                                    sub["prefix"]["mask"]), "SUCCESS"
                    next_url = None if not response_csrf.json()["next"] else response_csrf.json()["next"]

        return "NOT_FOUND", "FAILED"
    except KeyError:
        return "NOT_FOUND", "FAILED"


def createAkoFile(ip, cluster_name, wipCidr, tkgMgmtDataPg, env):
    if checkAirGappedIsEnabled(env):
        air_gapped_repo = str(
            request.get_json(force=True)['envSpec']['customRepositorySpec']['tkgCustomImageRepository'])
        air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
        repository = air_gapped_repo + '/ako'
    else:
        repository = 'projects.registry.vmware.com/tkg/ako'

    data = dict(
        apiVersion='networking.tkg.tanzu.vmware.com/v1alpha1',
        kind='AKODeploymentConfig',
        metadata=dict(
            finalizers=['ako-operator.networking.tkg.tanzu.vmware.com'],
            generation=1,
            name='install-ako-for-workload-set01'
        ),
        spec=dict(
            adminCredentialRef=dict(
                name='avi-controller-credentials',
                namespace='tkg-system-networking'),
            certificateAuthorityRef=dict(
                name='avi-controller-ca',
                namespace='tkg-system-networking'
            ),
            cloudName=Cloud.CLOUD_NAME_VSPHERE,
            clusterSelector=dict(
                matchLabels=dict(
                    type=AkoType.type_ako_set
                )
            ),
            controller=ip,
            dataNetwork=dict(cidr=wipCidr, name=tkgMgmtDataPg),
            extraConfigs=dict(ingress=dict(defaultIngressController=False, disableIngressClass=True)),
            serviceEngineGroup=Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE
        )
    )
    with open(Paths.CLUSTER_PATH + cluster_name + '/ako_vsphere_workloadset1.yaml', 'w') as outfile:
        yaml = ruamel.yaml.YAML()
        yaml.indent(mapping=2, sequence=4, offset=3)
        yaml.dump(data, outfile)


def changeNetworks(vcenter_ip, vcenter_username, password, engine_name):
    os.putenv("GOVC_URL", "https://" + vcenter_ip + "/sdk")
    os.putenv("GOVC_USERNAME", vcenter_username)
    os.putenv("GOVC_PASSWORD", password)
    os.putenv("GOVC_INSECURE", "true")
    change_VM_Net = ["govc", "vm.network.change", "-vm=" + engine_name, "-net", SegmentsName.DISPLAY_NAME_TKG_WORKLOAD,
                     "ethernet-2"]
    connect_VM_Net = ["govc", "device.connect", "-vm=" + engine_name, "ethernet-2"]
    try:
        runShellCommandWithPolling(change_VM_Net)
        runShellCommandWithPolling(connect_VM_Net)
    except Exception as e:
        return str(e), 500
    return "SUCCEES", 200


def waitForProcess(list1, podName):
    cert_state = runShellCommandAndReturnOutputAsList(list1)
    if cert_state[1] != 0:
        current_app.logger.error("Failed to apply " + podName + " " + cert_state[0])
        d = {
            "responseType": "ERROR",
            "msg": "Failed to apply " + podName + " " + cert_state[0],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500, 0
    count_cert = 0
    while verifyPodsAreRunning(podName, cert_state[0], RegexPattern.RUNNING) and count_cert < 50:
        cert_state = runShellCommandAndReturnOutputAsList(list1)
        time.sleep(30)
        count_cert = count_cert + 1
        current_app.logger.info("Waited for  " + str(count_cert * 30) + "s, retrying.")
    if not verifyPodsAreRunning(podName, cert_state[0], RegexPattern.RECONCILE_SUCCEEDED):
        current_app.logger.error(podName + " is not running on waiting " + str(count_cert * 30) + "s")
        d = {
            "responseType": "ERROR",
            "msg": podName + " is not running on waiting " + str(count_cert * 30) + "s",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500, count_cert
    d = {
        "responseType": "ERROR",
        "msg": "Failed to apply " + podName + " " + cert_state[0],
        "ERROR_CODE": 500
    }
    return jsonify(d), 200, count_cert
