# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import base64
import json
import logging
import os
import sys
import time

import requests
import ruamel
from flask import Blueprint, current_app, jsonify, request
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from tqdm import tqdm

from common.common_utilities import (
    VrfType,
    addStaticRoute,
    checkAirGappedIsEnabled,
    checkAviL7EnabledForWorkload,
    checkDataProtectionEnabled,
    checkDataProtectionEnabledVelero,
    checkEnableIdentityManagement,
    checkObjectIsPresentAndReturnPath,
    checkPinnipedInstalled,
    checkTmcEnabled,
    checkTmcRegister,
    checkToEnabled,
    checkWorkloadProxyEnabled,
    checTSMEnabled,
    createClusterFolder,
    createFirewallRule,
    createGroup,
    createNsxtSegment,
    createProxyCredentialsTMC,
    createRbacUsers,
    createResourceFolderAndWait,
    deployCluster,
    downloadAndPushKubernetesOvaMarketPlace,
    enable_data_protection,
    enable_data_protection_velero,
    envCheck,
    get_avi_version,
    getCloudStatus,
    getClusterID,
    getDomainName,
    getKubeVersionFullName,
    getList,
    getNetworkFolder,
    getNetworkIp,
    getNetworkPathTMC,
    getSECloudStatus,
    getTier1Details,
    getVrfAndNextRoutId,
    grabNsxtHeaders,
    isAviHaEnabled,
    isEnvTkgs_ns,
    isEnvTkgs_wcp,
    obtain_second_csrf,
    ping_test,
    preChecks,
    registerTanzuObservability,
    registerTSM,
    tmcBodyClusterCreation,
)
from common.lib.govc_client import GovcClient
from common.model.vsphereSpec import VsphereMasterSpec
from common.operation.constants import (
    PLAN,
    AkoType,
    AppName,
    Cloud,
    ControllerLocation,
    Env,
    FirewallRuleCgw,
    GroupNameCgw,
    KubernetesOva,
    Paths,
    Policy_Name,
    RegexPattern,
    ResourcePoolAndFolderName,
    ServiceName,
    Sizing,
    Tkg_version,
    TmcUser,
    Type,
)
from common.operation.ShellHelper import (
    grabKubectlCommand,
    grabPipeOutput,
    grabPipeOutputChagedDir,
    runProcess,
    runShellCommandAndReturnOutputAsList,
    runShellCommandWithPolling,
    verifyPodsAreRunning,
)
from common.operation.vcenter_operations import checkVmPresent
from common.prechecks.list_reources import validateKubeVersion
from common.util.local_cmd_helper import LocalCmdHelper
from vmc.managementConfig.management_config import getDetailsOfServiceEngine, getVipNetwork
from vmc.workloadConfig.workload_config import connectToWorkLoadCluster, getIPamDetails, updateIpamWithDataNetwork
from vsphere.managementConfig.vsphere_management_config import (
    changeSeGroupAndSetInterfaces,
    controllerDeployment,
    create_virtual_service,
    createSECloud,
    createSECloud_Arch,
    createVipNetwork,
    enableDhcpForManagementNetwork,
    fetchTier1GatewayId,
    getCloudConnectUser,
    getClusterUrl,
    getIpam,
    getNetworkDetails,
    getNetworkUrl,
    listAllServiceEngine,
    seperateNetmaskAndIp,
    updateIpam_profile,
    updateNetworkWithIpPools,
)
from vsphere.workloadConfig.vsphere_tkgs_workload import createNameSpace, createTkgWorkloadCluster

sys.path.append(".../")

logger = logging.getLogger(__name__)
vsphere_workload_config = Blueprint("vsphere_workload_config", __name__, static_folder="workloadConfig")

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


@vsphere_workload_config.route("/api/tanzu/vsphere/workload/preconfig", methods=["POST"])
def workloadConfig():
    network_config = networkConfig()
    if network_config[1] != 200:
        current_app.logger.error(network_config[0].json["msg"])
        d = {
            "responseType": "ERROR",
            "msg": "Failed to Config workload cluster " + str(network_config[0].json["msg"]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    deploy_workload = deploy()
    if deploy_workload[1] != 200:
        current_app.logger.error(str(deploy_workload[0].json["msg"]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to deploy extention " + str(deploy_workload[0].json["msg"]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    d = {"responseType": "SUCCESS", "msg": "Workload cluster configured Successfully", "STATUS_CODE": 200}
    current_app.logger.info("Workload cluster configured Successfully")
    return jsonify(d), 200


@vsphere_workload_config.route("/api/tanzu/vsphere/workload/network-config", methods=["POST"])
def networkConfig():
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {"responseType": "ERROR", "msg": "Wrong env provided " + env[0], "STATUS_CODE": 500}
        return jsonify(d), 500
    env = env[0]
    refreshToken = request.get_json(force=True)["envSpec"]["marketplaceSpec"]["refreshToken"]
    if not checkAirGappedIsEnabled(env) and refreshToken != "":
        validateK8s = validateKubeVersion(env, "Workload")
        if validateK8s[1] != 200:
            current_app.logger.error(validateK8s[0].json["msg"])
            d = {"responseType": "ERROR", "msg": "Failed to validate KubeVersion", "STATUS_CODE": 500}
            return jsonify(d), 50
    pre = preChecks()
    if pre[1] != 200:
        current_app.logger.error(pre[0].json["msg"])
        d = {"responseType": "ERROR", "msg": pre[0].json["msg"], "STATUS_CODE": 500}
        return jsonify(d), 500
    aviVersion = get_avi_version(env)
    password = current_app.config["VC_PASSWORD"]
    vcenter_username = current_app.config["VC_USER"]
    vcenter_ip = current_app.config["VC_IP"]
    cluster_name = current_app.config["VC_CLUSTER"]
    data_center = current_app.config["VC_DATACENTER"]
    data_store = current_app.config["VC_DATASTORE"]
    refToken = request.get_json(force=True)["envSpec"]["marketplaceSpec"]["refreshToken"]
    if env == Env.VSPHERE or env == Env.VCF:
        if not (isEnvTkgs_ns(env) or isEnvTkgs_wcp(env)):
            kubernetes_ova_os = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadBaseOs"]
            kubernetes_ova_version = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadKubeVersion"]
            if refToken:
                current_app.logger.info("Kubernetes OVA configs for workload cluster")
                down_status = downloadAndPushKubernetesOvaMarketPlace(env, kubernetes_ova_version, kubernetes_ova_os)
                if down_status[0] is None:
                    current_app.logger.error(down_status[1])
                    d = {"responseType": "ERROR", "msg": down_status[1], "STATUS_CODE": 500}
                    return jsonify(d), 500
            else:
                current_app.logger.info(
                    "MarketPlace refresh token is not provided, skipping the download of kubernetes ova"
                )
    if env == Env.VSPHERE:
        workload_network_name = request.get_json(force=True)["tkgWorkloadDataNetwork"]["tkgWorkloadDataNetworkName"]
    if env == Env.VCF:
        workload_network_name = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"][
            "tkgClusterVipNetworkName"
        ]
        pass
        # try:
        # gatewayAddress = request.get_json(force=True)['tkgWorkloadDataNetwork'][
        # 'tkgWorkloadDataNetworkGatewayCidr']
        # dnsServers = request.get_json(force=True)['envSpec']['infraComponents']['dnsServersIp']
        # network = getNetworkIp(gatewayAddress)
        # shared_segment = createNsxtSegment(workload_network_name, gatewayAddress,
        # None,
        # None, dnsServers, network, False)
        # if shared_segment[1] != 200:
        # current_app.logger.error("Failed to create shared segments" + str(shared_segment[0].json["msg"]))
        # d = {
        # "responseType": "ERROR",
        # "msg": "Failed to create shared segments" + str(shared_segment[0].json["msg"]),
        # "STATUS_CODE": 500
        # }
        # return jsonify(d), 500
        # except Exception as e:
        # current_app.logger.error("Failed to configure vcf workload " + str(e))
        # d = {
        # "responseType": "ERROR",
        # "msg": "Failed to configure vcf workload " + str(e),
        # "STATUS_CODE": 500
        # }
        # return jsonify(d), 500
    avi_fqdn = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController01Fqdn"]
    ##########################################################
    if isAviHaEnabled(env):
        ip = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviClusterFqdn"]
    else:
        ip = avi_fqdn
    if ip is None:
        current_app.logger.error("Failed to get IP of AVI controller")
        d = {"responseType": "ERROR", "msg": "Failed to get IP of AVI controller", "STATUS_CODE": 500}
        return jsonify(d), 500
    isNonOrchestrated = False
    try:
        mode = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["modeOfDeployment"]
        if mode == "non-orchestrated":
            isNonOrchestrated = True
    except Exception:
        isNonOrchestrated = False
    if isNonOrchestrated:
        workload_vip = request.get_json(force=True)["tkgWorkloadDataNetwork"]["tkgWorkloadDataNetworkName"]
        status = create_archostrated(
            ip,
            vcenter_ip,
            vcenter_username,
            password,
            data_center,
            data_store,
            cluster_name,
            workload_vip,
            aviVersion,
            env,
        )
        if status[1] != 200:
            current_app.logger.error("Failed to configure workload cluster " + str(status[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to configure workload cluster " + str(status[0]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
    else:
        csrf2 = obtain_second_csrf(ip, env)
        if csrf2 is None:
            current_app.logger.error("Failed to get csrf from new password")
            d = {"responseType": "ERROR", "msg": "Failed to get csrf from new password", "STATUS_CODE": 500}
            return jsonify(d), 500
        cloud = Cloud.CLOUD_NAME_VSPHERE
        if env == Env.VCF:
            cloud = Cloud.CLOUD_NAME_VSPHERE.replace("vsphere", "nsxt")
        get_cloud = getCloudStatus(ip, csrf2, aviVersion, cloud)
        if get_cloud[0] is None:
            current_app.logger.error("Failed to get cloud status " + str(get_cloud[1]))
            d = {"responseType": "ERROR", "msg": "Failed to get cloud status " + str(get_cloud[1]), "STATUS_CODE": 500}
            return jsonify(d), 500

        if get_cloud[0] == "NOT_FOUND":
            current_app.logger.error("Requested cloud is not created")
            d = {"responseType": "ERROR", "msg": "Requested cloud is not created", "STATUS_CODE": 500}
            return jsonify(d), 500
        else:
            cloud_url = get_cloud[0]
        cluster_name = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterCluster"]
        if env == Env.VSPHERE:
            cluster_status = getClusterUrl(ip, csrf2, cluster_name, aviVersion)
            if cluster_status[0] is None:
                current_app.logger.error("Failed to get cluster details" + str(cluster_status[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get cluster details " + str(cluster_status[1]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            if cluster_status[0] == "NOT_FOUND":
                current_app.logger.error("Failed to get cluster details" + str(cluster_status[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get cluster details " + str(cluster_status[1]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500

            get_ipam = getIpam(ip, csrf2, Cloud.IPAM_NAME_VSPHERE, aviVersion)
            if get_ipam[0] is None:
                current_app.logger.error("Failed to get service engine Ipam " + str(get_ipam[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get service engine Ipam " + str(get_ipam[1]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500

            update = updateIpam_profile(ip, csrf2, workload_network_name, aviVersion)
            if update[0] is None:
                current_app.logger.error("Failed to update service engine Ipam " + str(update[1]))
                d = {"responseType": "ERROR", "msg": "Failed to update ipam " + str(update[1]), "STATUS_CODE": 500}
                return jsonify(d), 500
            group_name = Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE
        else:
            group_name = Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE.replace("vsphere", "nsxt")
        get_se_cloud = getSECloudStatus(ip, csrf2, aviVersion, group_name)
        if get_se_cloud[0] is None:
            current_app.logger.error("Failed to get service engine cloud status " + str(get_se_cloud[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get service engine cloud status " + str(get_se_cloud[1]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        if get_se_cloud[0] == "NOT_FOUND":
            current_app.logger.info("Creating New service engine cloud " + group_name)
            cloud_se = createSECloud(
                ip, csrf2, cloud_url, group_name, cluster_status[0], data_store, aviVersion, "Workload"
            )
            if cloud_se[0] is None:
                current_app.logger.error("Failed to create service engine cloud " + str(cloud_se[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create service engine cloud " + str(cloud_se[1]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
        management_cluster = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtClusterName"]
        if env == Env.VSPHERE:
            data_network_workload = request.get_json(force=True)["tkgWorkloadDataNetwork"]["tkgWorkloadDataNetworkName"]
        else:
            data_network_workload = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"][
                "tkgClusterVipNetworkName"
            ]
        get_management_data_pg = getNetworkUrl(ip, csrf2, data_network_workload, aviVersion)
        if get_management_data_pg[0] is None:
            current_app.logger.error("Failed to get workload data network details " + str(get_management_data_pg[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get workloadt data network details " + str(get_management_data_pg[1]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        if env == Env.VSPHERE:
            startIp = request.get_json(force=True)["tkgWorkloadDataNetwork"]["tkgWorkloadAviServiceIpStartRange"]
            endIp = request.get_json(force=True)["tkgWorkloadDataNetwork"]["tkgWorkloadAviServiceIpEndRange"]
            prefixIpNetmask = seperateNetmaskAndIp(
                request.get_json(force=True)["tkgWorkloadDataNetwork"]["tkgWorkloadDataNetworkGatewayCidr"]
            )
        else:
            startIp = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"][
                "tkgClusterVipIpStartRange"
            ]
            endIp = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"]["tkgClusterVipIpEndRange"]
            prefixIpNetmask = seperateNetmaskAndIp(
                request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"][
                    "tkgClusterVipNetworkGatewayCidr"
                ]
            )
        getManagementDetails_data_pg = getNetworkDetails(
            ip,
            csrf2,
            get_management_data_pg[0],
            startIp,
            endIp,
            prefixIpNetmask[0],
            prefixIpNetmask[1],
            aviVersion,
            env,
        )
        if getManagementDetails_data_pg[0] is None:
            current_app.logger.error(
                "Failed to get workload data network details " + str(getManagementDetails_data_pg[2])
            )
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get workload data network details " + str(getManagementDetails_data_pg[2]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        if getManagementDetails_data_pg[0] == "AlreadyConfigured":
            current_app.logger.info("Ip pools are already configured.")
        else:
            update_resp = updateNetworkWithIpPools(
                ip, csrf2, get_management_data_pg[0], "managementNetworkDetails.json", aviVersion
            )
            if update_resp[0] != 200:
                current_app.logger.error("Failed to update ip " + str(update_resp[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get management network details " + str(update_resp[1]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
        with open("./newCloudInfo.json", "r") as file2:
            new_cloud_json = json.load(file2)
        uuid = None
        try:
            uuid = new_cloud_json["uuid"]
        except Exception:
            for re in new_cloud_json["results"]:
                if re["name"] == cloud:
                    uuid = re["uuid"]
        if uuid is None:
            current_app.logger.error("Uuid not found ")
            d = {"responseType": "ERROR", "msg": "uuid not found ", "STATUS_CODE": 500}
            return jsonify(d), "NOT_FOUND"
        vrf = getVrfAndNextRoutId(ip, csrf2, uuid, VrfType.GLOBAL, prefixIpNetmask[0], aviVersion)
        if vrf[0] is None or vrf[1] == "NOT_FOUND":
            current_app.logger.error("Vrf not found " + str(vrf[1]))
            d = {"responseType": "ERROR", "msg": "Vrf not found " + str(vrf[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
        if vrf[1] != "Already_Configured":
            current_app.logger.info("Routing is not cofigured, configuring it.")
            ad = addStaticRoute(ip, csrf2, vrf[0], prefixIpNetmask[0], vrf[1], aviVersion)
            if ad[0] is None:
                current_app.logger.error("Failed to add static route " + str(ad[1]))
                d = {"responseType": "ERROR", "msg": "Vrf not found " + str(ad[1]), "STATUS_CODE": 500}
                return jsonify(d), 500
            current_app.logger.info("Routing is cofigured")
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
            current_app.logger.error("AKO pods are not running on waiting for 10 mins " + command_status_ako[0])
            d = {
                "responseType": "ERROR",
                "msg": "AKO pods are not running on waiting for 10 mins " + str(command_status_ako[0]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        wip = getVipNetworkIpNetMask(ip, csrf2, data_network_workload, aviVersion)
        if wip[0] is None or wip[0] == "NOT_FOUND":
            current_app.logger.error("Failed to get wip netmask ")
            d = {"responseType": "ERROR", "msg": "Failed to get wip netmask ", "STATUS_CODE": 500}
            return jsonify(d), 500
        workload_cluster_name = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadClusterName"]
        workload_cluster_path = Paths.CLUSTER_PATH + workload_cluster_name
        if not createClusterFolder(workload_cluster_name):
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create directory: " + workload_cluster_path,
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        current_app.logger.info("The config files for workload cluster will be located at: " + workload_cluster_path)
        cluster_vip_name = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"][
            "tkgClusterVipNetworkName"
        ]
        cluster_vip_cidr_ = getVipNetworkIpNetMask(ip, csrf2, cluster_vip_name, aviVersion)
        if env == Env.VCF:
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Cookie": csrf2[1],
                "referer": "https://" + avi_fqdn + "/login",
                "x-avi-version": aviVersion,
                "x-csrftoken": csrf2[0],
            }
            status, value = getCloudConnectUser(avi_fqdn, headers)
            nsxt_cred = value["nsxUUid"]
            tier1_id, status_tier1 = fetchTier1GatewayId(avi_fqdn, headers, nsxt_cred)
            if tier1_id is None:
                current_app.logger.error("Failed to get Tier 1 details " + str(status_tier1))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get Tier 1 details " + str(status_tier1),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            tier1 = status_tier1
        else:
            tier1 = ""
        workload_network_name = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadNetworkName"]
        createAkoFile(
            ip,
            workload_cluster_name,
            wip[0],
            data_network_workload,
            cluster_vip_name,
            workload_network_name,
            cluster_vip_cidr_[0],
            tier1,
            env,
        )
        lisOfCommand = [
            "kubectl",
            "apply",
            "-f",
            workload_cluster_path + "/ako_vsphere_workloadset1.yaml",
            "--validate=false",
        ]
        status = runShellCommandAndReturnOutputAsList(lisOfCommand)
        if status[1] != 0:
            if not str(status[0]).__contains__("already has a value"):
                current_app.logger.error("Failed to apply ako" + str(status[0]))
                d = {"responseType": "ERROR", "msg": "Failed to apply ako label " + str(status[0]), "STATUS_CODE": 500}
                return jsonify(d), 500
        current_app.logger.info("Applied ako successfully")
        if env == Env.VCF:
            teir1name = str(request.get_json(force=True)["envSpec"]["vcenterDetails"]["nsxtTier1RouterDisplayName"])
            vrf_vip = getVrfAndNextRoutId(ip, csrf2, uuid, teir1name, prefixIpNetmask[0], aviVersion)
            if vrf_vip[0] is None or vrf_vip[1] == "NOT_FOUND":
                current_app.logger.error("Cluster VIP Vrf not found " + str(vrf_vip[1]))
                d = {"responseType": "ERROR", "msg": "Cluster VIP Vrf not found " + str(vrf_vip[1]), "STATUS_CODE": 500}
                return jsonify(d), 500
            if vrf_vip[1] != "Already_Configured":
                ad = addStaticRoute(ip, csrf2, vrf_vip[0], prefixIpNetmask[0], vrf_vip[1], aviVersion)
                if ad[0] is None:
                    current_app.logger.error("Failed to add static route " + str(ad[1]))
                    d = {"responseType": "ERROR", "msg": "Vrf not found " + str(ad[1]), "STATUS_CODE": 500}
                    return jsonify(d), 500
            vrf_url = vrf_vip[0]
            virtual_service, error = create_virtual_service(
                ip, csrf2, uuid, group_name, get_management_data_pg[0], 2, tier1, vrf_url, aviVersion
            )
            if virtual_service is None:
                current_app.logger.error("Failed to create virtual service " + str(error))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create virtual service " + str(error),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
    d = {"responseType": "SUCCESS", "msg": "Successfully configured workload preconfig", "STATUS_CODE": 200}
    return jsonify(d), 200


@vsphere_workload_config.route("/api/tanzu/vsphere/workload/createnamespace", methods=["POST"])
def create_name_space():
    password = current_app.config["VC_PASSWORD"]
    vcenter_username = current_app.config["VC_USER"]
    vcenter_ip = current_app.config["VC_IP"]
    name_space = createNameSpace(vcenter_ip, vcenter_username, password)
    if name_space[0] is None:
        current_app.logger.error("Failed to create namespace " + str(name_space[1]))
        d = {"responseType": "ERROR", "msg": "Failed to create namespace " + str(name_space[1]), "STATUS_CODE": 500}
        return jsonify(d), 500
    current_app.logger.info("Successfully created namespace")
    d = {"responseType": "SUCCESS", "msg": "Successfully created namespace", "STATUS_CODE": 200}
    return jsonify(d), 200


@vsphere_workload_config.route("/api/tanzu/vsphere/workload/createworkload", methods=["POST"])
def create_workload():
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
    password = current_app.config["VC_PASSWORD"]
    vcenter_username = current_app.config["VC_USER"]
    vcenter_ip = current_app.config["VC_IP"]
    name_space = createTkgWorkloadCluster(env, vcenter_ip, vcenter_username, password)
    if name_space[0] is None:
        current_app.logger.error("Failed to create workload cluster " + str(name_space[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create workload cluster " + str(name_space[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    current_app.logger.info("Successfully created workload cluster")
    if checkTmcEnabled(env):
        current_app.logger.info("Initiating TKGs SAAS integration")
        size = request.get_json(force=True)["tkgsComponentSpec"]["tkgsVsphereNamespaceSpec"][
            "tkgsVsphereWorkloadClusterSpec"
        ]["workerNodeCount"]
        workload_cluster_name = request.get_json(force=True)["tkgsComponentSpec"]["tkgsVsphereNamespaceSpec"][
            "tkgsVsphereWorkloadClusterSpec"
        ]["tkgsVsphereWorkloadClusterName"]
        if checkToEnabled(env):
            to = registerTanzuObservability(workload_cluster_name, env, size)
            if to[1] != 200:
                current_app.logger.error(to[0])
                d = {
                    "responseType": "ERROR",
                    "msg": "TO registration failed for workload cluster",
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
        else:
            current_app.logger.info("Tanzu Observability not enabled")
        if checTSMEnabled(env):
            cluster_version = request.get_json(force=True)["tkgsComponentSpec"]["tkgsVsphereNamespaceSpec"][
                "tkgsVsphereWorkloadClusterSpec"
            ]["tkgsVsphereWorkloadClusterVersion"]
            if not cluster_version.startswith("v"):
                cluster_version = "v" + cluster_version
            if not cluster_version.startswith("v1.18.19+vmware.1"):
                current_app.logger.warn(
                    "On vSphere with Tanzu platform, TSM supports the Kubernetes version 1.18.19+vmware.1"
                )
                current_app.logger.warn(
                    "For latest updates please check - "
                    "https://docs.vmware.com/en/VMware-Tanzu-Service-Mesh/services/\
                    tanzu-service-mesh-environment-requirements-and-supported-platforms/\
                        GUID-D0B939BE-474E-4075-9A65-3D72B5B9F237.html"
                )
            tsm = registerTSM(workload_cluster_name, env, size)
            if tsm[1] != 200:
                current_app.logger.error("TSM registration failed for workload cluster")
                d = {
                    "responseType": "ERROR",
                    "msg": "TSM registration failed for workload cluster",
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
        else:
            current_app.logger.info("TSM not enabled")

        if checkDataProtectionEnabled(Env.VSPHERE, "workload"):
            supervisor_cluster = request.get_json(force=True)["envSpec"]["saasEndpoints"]["tmcDetails"][
                "tmcSupervisorClusterName"
            ]
            is_enabled = enable_data_protection(env, workload_cluster_name, supervisor_cluster)
            if not is_enabled[0]:
                current_app.logger.error(is_enabled[1])
                d = {"responseType": "ERROR", "msg": is_enabled[1], "STATUS_CODE": 500}
                return jsonify(d), 500
            current_app.logger.info(is_enabled[1])
        else:
            current_app.logger.info("Data Protection is not enabled for cluster " + workload_cluster_name)
    else:
        current_app.logger.info("TMC not enabled.")
        current_app.logger.info("Check whether data protection is to be enabled via Velero on Workload Cluster")
        if checkDataProtectionEnabledVelero(env, "workload"):
            url_ = "https://" + vcenter_ip + "/"
            sess = requests.post(url_ + "rest/com/vmware/cis/session", auth=(vcenter_username, password), verify=False)
            if sess.status_code != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to fetch session ID for vCenter - " + vcenter_ip,
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            else:
                session_id = sess.json()["value"]
            header = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "vmware-api-session-id": session_id,
            }
            cluster_name = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterCluster"]
            if str(cluster_name).__contains__("/"):
                cluster_name = cluster_name[cluster_name.rindex("/") + 1 :]
            id = getClusterID(vcenter_ip, vcenter_username, password, cluster_name)
            if id[1] != 200:
                return None, id[0]
            clusterip_resp = requests.get(
                url_ + "api/vcenter/namespace-management/clusters/" + str(id[0]), verify=False, headers=header
            )
            if clusterip_resp.status_code != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to fetch API server cluster endpoint - " + vcenter_ip,
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            cluster_endpoint = clusterip_resp.json()["api_server_cluster_endpoint"]
            workload_cluster_name = request.get_json(force=True)["tkgsComponentSpec"]["tkgsVsphereNamespaceSpec"][
                "tkgsVsphereWorkloadClusterSpec"
            ]["tkgsVsphereWorkloadClusterName"]
            name_space = request.get_json(force=True)["tkgsComponentSpec"]["tkgsVsphereNamespaceSpec"][
                "tkgsVsphereWorkloadClusterSpec"
            ]["tkgsVsphereNamespaceName"]
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
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to switch  to context " + str(switch_context[0]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            current_app.logger.info("Switched to " + workload_cluster_name + " context")
            is_enabled = enable_data_protection_velero("workload", env)
            if not is_enabled[0]:
                current_app.logger.error("Failed to enable data protection via velero on Workload Cluster")
                current_app.logger.error(is_enabled[1])
                d = {"responseType": "ERROR", "msg": is_enabled[1], "STATUS_CODE": 500}
                return jsonify(d), 500
            current_app.logger.info("Successfully enabled data protection via Velero on Workload Cluster")
            current_app.logger.info(is_enabled[1])
        else:
            current_app.logger.info("Data protection via Velero setting is not active for Workload Cluster")

    d = {"responseType": "SUCCESS", "msg": "Successfully created workload cluster", "STATUS_CODE": 200}
    return jsonify(d), 200


@vsphere_workload_config.route("/api/tanzu/vsphere/workload/config", methods=["POST"])
def deploy():
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
    json_dict = request.get_json(force=True)
    vsSpec = VsphereMasterSpec.parse_obj(json_dict)
    env = env[0]
    aviVersion = get_avi_version(env)
    password = current_app.config["VC_PASSWORD"]
    vcenter_username = current_app.config["VC_USER"]
    vcenter_ip = current_app.config["VC_IP"]
    cluster_name = current_app.config["VC_CLUSTER"]
    data_center = current_app.config["VC_DATACENTER"]
    data_store = current_app.config["VC_DATASTORE"]
    parent_resourcePool = current_app.config["RESOURCE_POOL"]
    if env == Env.VCF:
        try:
            gatewayAddress = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadGatewayCidr"]
            dhcp_start = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadDhcpStartRange"]
            dhcp_end = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadDhcpEndRange"]
            dnsServers = request.get_json(force=True)["envSpec"]["infraComponents"]["dnsServersIp"]
            network = getNetworkIp(gatewayAddress)
            workload_network_name = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadNetworkName"]
            workload_segment = createNsxtSegment(
                workload_network_name, gatewayAddress, dhcp_start, dhcp_end, dnsServers, network, True
            )
            if workload_segment[1] != 200:
                current_app.logger.error("Failed to create workload segments" + str(workload_segment[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create workload segments" + str(workload_segment[0].json["msg"]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            worklod_group = createGroup(
                GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW, workload_network_name, False, None
            )
            if worklod_group[1] != 200:
                current_app.logger.error(
                    "Failed to create group "
                    + GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW
                    + " "
                    + str(worklod_group[0].json["msg"])
                )
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create group "
                    + GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW
                    + " "
                    + str(worklod_group[0].json["msg"]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            headers_ = grabNsxtHeaders()
            if headers_[0] is None:
                d = {"responseType": "ERROR", "msg": "Failed to get Nsxt info " + str(headers_[1]), "STATUS_CODE": 500}
                return jsonify(d), 500
            domainName = getDomainName(headers_, "default")
            if domainName[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get Domain name " + str(domainName[1]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            uri = "https://" + headers_[2] + "/policy/api/v1/infra/domains/" + domainName[0] + "/groups"
            output = getList(headers_[1], uri)
            if output[1] != 200:
                current_app.logger.error("Failed to get list of groups " + str(output[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get list of groups " + str(output[0]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            teir1 = getTier1Details(headers_)
            if teir1[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get tier1 details" + str(headers_[1]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            payload = {
                "action": "ALLOW",
                "display_name": FirewallRuleCgw.DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_DNS,
                "logged": False,
                "source_groups": [
                    checkObjectIsPresentAndReturnPath(
                        output[0], GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW
                    )[1],
                    checkObjectIsPresentAndReturnPath(
                        output[0], GroupNameCgw.DISPLAY_NAME_VCF_TKG_Management_Network_Group_CGW
                    )[1],
                ],
                "destination_groups": [
                    checkObjectIsPresentAndReturnPath(output[0], GroupNameCgw.DISPLAY_NAME_VCF_DNS_IPs_Group)[1],
                    checkObjectIsPresentAndReturnPath(output[0], GroupNameCgw.DISPLAY_NAME_VCF_NTP_IPs_Group)[1],
                    checkObjectIsPresentAndReturnPath(
                        output[0], GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW
                    )[1],
                    checkObjectIsPresentAndReturnPath(
                        output[0], GroupNameCgw.DISPLAY_NAME_VCF_CLUSTER_VIP_NETWORK_Group_CGW
                    )[1],
                ],
                "services": [
                    "/infra/services/DNS",
                    "/infra/services/DNS-UDP",
                    "/infra/services/NTP",
                    "/infra/services/" + ServiceName.KUBE_VIP_VCF_SERVICE,
                ],
                "scope": [teir1[0]],
            }
            fw = createFirewallRule(
                Policy_Name.POLICY_NAME, FirewallRuleCgw.DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_DNS, payload
            )
            if fw[1] != 200:
                current_app.logger.error(
                    "Failed to create firewall "
                    + FirewallRuleCgw.DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_DNS
                    + " "
                    + str(fw[0].json["msg"])
                )
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create firewall "
                    + GroupNameCgw.DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_DNS
                    + " "
                    + str(fw[0].json["msg"]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            payload = {
                "action": "ALLOW",
                "display_name": FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_WORKLOAD_to_vCenter,
                "logged": False,
                "source_groups": [
                    checkObjectIsPresentAndReturnPath(
                        output[0], GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW
                    )[1]
                ],
                "destination_groups": [
                    checkObjectIsPresentAndReturnPath(output[0], GroupNameCgw.DISPLAY_NAME_VCF_vCenter_IP_Group)[1]
                ],
                "services": ["/infra/services/HTTPS"],
                "scope": [teir1[0]],
            }
            fw = createFirewallRule(
                Policy_Name.POLICY_NAME, FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_WORKLOAD_to_vCenter, payload
            )
            if fw[1] != 200:
                current_app.logger.error(
                    "Failed to create firewall "
                    + FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_WORKLOAD_to_vCenter
                    + " "
                    + str(fw[0].json["msg"])
                )
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create firewall "
                    + GroupNameCgw.DISPLAY_NAME_VCF_TKG_WORKLOAD_to_vCenter
                    + " "
                    + str(fw[0].json["msg"]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            payload = {
                "action": "ALLOW",
                "display_name": FirewallRuleCgw.DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_to_Internet,
                "logged": False,
                "source_groups": [
                    checkObjectIsPresentAndReturnPath(
                        output[0], GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW
                    )[1]
                ],
                "destination_groups": ["ANY"],
                "services": ["ANY"],
                "scope": [teir1[0]],
            }
            fw = createFirewallRule(
                Policy_Name.POLICY_NAME, FirewallRuleCgw.DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_to_Internet, payload
            )
            if fw[1] != 200:
                current_app.logger.error(
                    "Failed to create firewall "
                    + FirewallRuleCgw.DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_to_Internet
                    + " "
                    + str(fw[0].json["msg"])
                )
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create firewall "
                    + GroupNameCgw.DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_to_Internet
                    + " "
                    + str(fw[0].json["msg"]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            # perform ping test to the gateways
            if ping_test("ping -c 1 " + gatewayAddress.split("/")[0]) != 0:
                current_app.logger.warn(
                    "Ping test failed for " + gatewayAddress + " gateway. It is Recommended to fix this "
                    "before proceeding with deployment"
                )
                time.sleep(30)
            else:
                current_app.logger.info("Ping test passed for gateway - " + gatewayAddress)
        except Exception as e:
            current_app.logger.error("Failed to configure vcf workload " + str(e))
            d = {"responseType": "ERROR", "msg": "Failed to configure vcf workload " + str(e), "STATUS_CODE": 500}
            return jsonify(d), 500
    kubernetes_ova_version = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadKubeVersion"]
    pod_cidr = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadClusterCidr"]
    service_cidr = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadServiceCidr"]
    avi_fqdn = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController01Fqdn"]
    if isAviHaEnabled(env):
        ip = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviClusterFqdn"]
    else:
        ip = avi_fqdn
    if ip is None:
        current_app.logger.error("Failed to get IP of AVI controller")
        d = {"responseType": "ERROR", "msg": "Failed to get ip of avi controller", "STATUS_CODE": 500}
        return jsonify(d), 500
    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        current_app.logger.error("Failed to get csrf from new password")
        d = {"responseType": "ERROR", "msg": "Failed to get csrf from new password", "STATUS_CODE": 500}
        return jsonify(d), 500
    isNonOrchestrated = False
    try:
        mode = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["modeOfDeployment"]
        if mode == "non-orchestrated":
            isNonOrchestrated = True
    except Exception:
        isNonOrchestrated = False
    if isNonOrchestrated:
        config_se = config_service_engines(ip, csrf2, vcenter_ip, vcenter_username, password, data_center, aviVersion)
        if config_se[1] != 200:
            current_app.logger.error("Failed to config service engines " + config_se[0].json["msg"])
            d = {
                "responseType": "ERROR",
                "msg": "Failed to config service engines " + str(config_se[0].json["msg"]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
    create = createResourceFolderAndWait(
        vcenter_ip,
        vcenter_username,
        password,
        cluster_name,
        data_center,
        ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL_VSPHERE,
        ResourcePoolAndFolderName.WORKLOAD_FOLDER_VSPHERE,
        parent_resourcePool,
    )
    if create[1] != 200:
        current_app.logger.error("Failed to create resource pool and folder " + create[0].json["msg"])
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create resource pool " + str(create[0].json["msg"]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
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
    tmc_required = str(request.get_json(force=True)["envSpec"]["saasEndpoints"]["tmcDetails"]["tmcAvailability"])
    tmc_flag = False
    if tmc_required.lower() == "true":
        tmc_flag = True
    elif tmc_required.lower() == "false":
        tmc_flag = False
        current_app.logger.info("TMC registration is deactivated")
    else:
        current_app.logger.error("Wrong TMC selection attribute provided " + tmc_required)
        d = {
            "responseType": "ERROR",
            "msg": "Wrong TMC selection attribute provided " + tmc_required,
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    cluster_plan = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadDeploymentType"]
    if cluster_plan == PLAN.DEV_PLAN:
        controlPlaneNodeCount = "1"
        machineCount = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadWorkerMachineCount"]
    elif cluster_plan == PLAN.PROD_PLAN:
        controlPlaneNodeCount = "3"
        machineCount = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadWorkerMachineCount"]
    else:
        current_app.logger.error("Unsupported control plan provided please specify prod or dev " + cluster_plan)
        d = {
            "responseType": "ERROR",
            "msg": "Unsupported control plan provided please specify prod or dev " + cluster_plan,
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    size = str(request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadSize"])
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
        cpu = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadCpuSize"]
        disk = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadStorageSize"]
        control_plane_mem_gb = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadMemorySize"]
        memory = str(int(control_plane_mem_gb) * 1024)
    else:
        current_app.logger.error(
            "Provided cluster size: " + size + "is not supported, please provide one of: "
            "small/medium/large/extra-large/custom"
        )
        d = {
            "responseType": "ERROR",
            "msg": "Provided cluster size: " + size + "is not supported, please provide one of: "
            "small/medium/large/extra-large/custom",
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    deployWorkload = False
    workload_cluster_name = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadClusterName"]
    management_cluster = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtClusterName"]
    workload_network = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadNetworkName"]
    vsphere_password = password
    _base64_bytes = vsphere_password.encode("ascii")
    _enc_bytes = base64.b64encode(_base64_bytes)
    vsphere_password = _enc_bytes.decode("ascii")
    dhcp = enableDhcpForManagementNetwork(ip, csrf2, workload_network, aviVersion)
    if dhcp[0] is None:
        current_app.logger.error("Failed to enable dhcp " + str(dhcp[1]))
        d = {"responseType": "ERROR", "msg": "Failed to enable dhcp " + str(dhcp[1]), "STATUS_CODE": 500}
        return jsonify(d), 500
    datacenter_path = "/" + data_center
    datastore_path = datacenter_path + "/datastore/" + data_store
    workload_folder_path = datacenter_path + "/vm/" + ResourcePoolAndFolderName.WORKLOAD_FOLDER_VSPHERE
    if parent_resourcePool:
        workload_resource_path = (
            datacenter_path
            + "/host/"
            + cluster_name
            + "/Resources/"
            + parent_resourcePool
            + "/"
            + ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL_VSPHERE
        )
    else:
        workload_resource_path = (
            datacenter_path
            + "/host/"
            + cluster_name
            + "/Resources/"
            + ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL_VSPHERE
        )
    workload_network_path = getNetworkFolder(workload_network, vcenter_ip, vcenter_username, password)
    if not workload_network_path:
        current_app.logger.error("Network folder not found for " + workload_network)
        d = {"responseType": "ERROR", "msg": "Network folder not found for " + workload_network, "STATUS_CODE": 500}
        return jsonify(d), 500

    if Tkg_version.TKG_VERSION == "2.1" and checkTmcEnabled(env):
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
        version_status = getKubeVersionFullName(kubernetes_ova_version)
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

        clusterGroup = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadClusterGroupName"]

        if not clusterGroup:
            clusterGroup = "default"

        workload_network_folder_path = getNetworkPathTMC(workload_network, vcenter_ip, vcenter_username, password)
        if checkWorkloadProxyEnabled(env) and not checkTmcRegister(workload_cluster_name, False):
            proxy_name_state = createProxyCredentialsTMC(env, workload_cluster_name, "true", "workload", register=False)
            if proxy_name_state[1] != 200:
                d = {"responseType": "ERROR", "msg": proxy_name_state[0], "STATUS_CODE": 500}
                return jsonify(d), 500
            proxy_name = "arcas-" + workload_cluster_name + "-tmc-proxy"
            if cluster_plan.lower() == PLAN.PROD_PLAN:
                pass
                # createWorkloadCluster = [
                #     "tmc",
                #     "cluster",
                #     "create",
                #     "-t",
                #     "tkg-vsphere",
                #     "-n",
                #     workload_cluster_name,
                #     "-m",
                #     management_cluster,
                #     "-p",
                #     "default",
                #     "--cluster-group",
                #     clusterGroup,
                #     "--ssh-key",
                #     re,
                #     "--version",
                #     version,
                #     "--datacenter",
                #     datacenter_path,
                #     "--datastore",
                #     datastore_path,
                #     "--folder",
                #     workload_folder_path,
                #     "--resource-pool",
                #     workload_resource_path,
                #     "--workspace-network",
                #     workload_network_folder_path,
                #     "--control-plane-cpu",
                #     cpu,
                #     "--control-plane-disk-gib",
                #     disk,
                #     "--control-plane-memory-mib",
                #     memory,
                #     "--worker-node-count",
                #     machineCount,
                #     "--worker-cpu",
                #     cpu,
                #     "--worker-disk-gib",
                #     disk,
                #     "--worker-memory-mib",
                #     memory,
                #     "--pods-cidr-blocks",
                #     pod_cidr,
                #     "--service-cidr-blocks",
                #     service_cidr,
                #     "--high-availability",
                #     "--proxy-name",
                #     proxy_name,
                # ]
            else:
                pass
                # createWorkloadCluster = [
                #     "tmc",
                #     "cluster",
                #     "create",
                #     "-t",
                #     "tkg-vsphere",
                #     "-n",
                #     workload_cluster_name,
                #     "-m",
                #     management_cluster,
                #     "-p",
                #     "default",
                #     "--cluster-group",
                #     clusterGroup,
                #     "--ssh-key",
                #     re,
                #     "--version",
                #     version,
                #     "--datacenter",
                #     datacenter_path,
                #     "--datastore",
                #     datastore_path,
                #     "--folder",
                #     workload_folder_path,
                #     "--resource-pool",
                #     workload_resource_path,
                #     "--workspace-network",
                #     workload_network_folder_path,
                #     "--control-plane-cpu",
                #     cpu,
                #     "--control-plane-disk-gib",
                #     disk,
                #     "--control-plane-memory-mib",
                #     memory,
                #     "--worker-node-count",
                #     machineCount,
                #     "--worker-cpu",
                #     cpu,
                #     "--worker-disk-gib",
                #     disk,
                #     "--worker-memory-mib",
                #     memory,
                #     "--pods-cidr-blocks",
                #     pod_cidr,
                #     "--service-cidr-blocks",
                #     service_cidr,
                #     "--proxy-name",
                #     proxy_name,
                # ]
        else:
            proxy_name = ""
            # if cluster_plan.lower() == PLAN.PROD_PLAN:
            #     createWorkloadCluster = [
            #         "tmc",
            #         "cluster",
            #         "create",
            #         "-t",
            #         "tkg-vsphere",
            #         "-n",
            #         workload_cluster_name,
            #         "-m",
            #         management_cluster,
            #         "-p",
            #         "default",
            #         "--cluster-group",
            #         clusterGroup,
            #         "--ssh-key",
            #         re,
            #         "--version",
            #         version,
            #         "--datacenter",
            #         datacenter_path,
            #         "--datastore",
            #         datastore_path,
            #         "--folder",
            #         workload_folder_path,
            #         "--resource-pool",
            #         workload_resource_path,
            #         "--workspace-network",
            #         workload_network_folder_path,
            #         "--control-plane-cpu",
            #         cpu,
            #         "--control-plane-disk-gib",
            #         disk,
            #         "--control-plane-memory-mib",
            #         memory,
            #         "--worker-node-count",
            #         machineCount,
            #         "--worker-cpu",
            #         cpu,
            #         "--worker-disk-gib",
            #         disk,
            #         "--worker-memory-mib",
            #         memory,
            #         "--pods-cidr-blocks",
            #         pod_cidr,
            #         "--service-cidr-blocks",
            #         service_cidr,
            #         "--high-availability",
            #     ]
            # else:
            #     createWorkloadCluster = [
            #         "tmc",
            #         "cluster",
            #         "create",
            #         "-t",
            #         "tkg-vsphere",
            #         "-n",
            #         workload_cluster_name,
            #         "-m",
            #         management_cluster,
            #         "-p",
            #         "default",
            #         "--cluster-group",
            #         clusterGroup,
            #         "--ssh-key",
            #         re,
            #         "--version",
            #         version,
            #         "--datacenter",
            #         datacenter_path,
            #         "--datastore",
            #         datastore_path,
            #         "--folder",
            #         workload_folder_path,
            #         "--resource-pool",
            #         workload_resource_path,
            #         "--workspace-network",
            #         workload_network_folder_path,
            #         "--control-plane-cpu",
            #         cpu,
            #         "--control-plane-disk-gib",
            #         disk,
            #         "--control-plane-memory-mib",
            #         memory,
            #         "--worker-node-count",
            #         machineCount,
            #         "--worker-cpu",
            #         cpu,
            #         "--worker-disk-gib",
            #         disk,
            #         "--worker-memory-mib",
            #         memory,
            #         "--pods-cidr-blocks",
            #         pod_cidr,
            #         "--service-cidr-blocks",
            #         service_cidr,
            #     ]

    isCheck = False
    found = False
    if command_status[0] is None:
        if Tkg_version.TKG_VERSION == "2.1" and checkTmcEnabled(env):
            pass
            # current_app.logger.info("Deploying Workload cluster")
            # for i in tqdm(range(150), desc="Waiting for folder to be available in tmc…", ascii=False, ncols=75):
            #     time.sleep(1)
            # current_app.logger.info("Deploying workload cluster")
            # os.putenv(
            #     "TMC_API_TOKEN",
            #     request.get_json(force=True)["envSpec"]["saasEndpoints"]["tmcDetails"]["tmcRefreshToken"],
            # )
            # listOfCmdTmcLogin = ["tmc", "login", "--no-configure", "-name", TmcUser.USER_VSPHERE]
            # runProcess(listOfCmdTmcLogin)
            # command_status = runShellCommandAndReturnOutputAsList(createWorkloadCluster)
            # if command_status[1] != 0:
            #     current_app.logger.error("Failed to run command to create workload cluster " + str(command_status[0]))
            #     d = {
            #         "responseType": "ERROR",
            #         "msg": "Failed to run command to create workload cluster " + str(command_status[0]),
            #         "STATUS_CODE": 500,
            #     }
            #     return jsonify(d), 500
            # else:
            #     current_app.logger.info("Workload cluster is successfully deployed and running " + command_status[0])
            #     deployWorkload = True
    else:
        if not verifyPodsAreRunning(workload_cluster_name, command_status[0], RegexPattern.running):
            isCheck = True
            if not checkTmcEnabled(env):
                current_app.logger.info("Deploying workload cluster, after verification, using tanzu 1.5")
                deploy_status = deployCluster(
                    workload_cluster_name,
                    cluster_plan,
                    data_center,
                    data_store,
                    workload_folder_path,
                    workload_network_path,
                    vsphere_password,
                    workload_resource_path,
                    vcenter_ip,
                    re,
                    vcenter_username,
                    machineCount,
                    size,
                    env,
                    Type.WORKLOAD,
                    vsSpec,
                )
                if deploy_status[0] is None:
                    current_app.logger.error("Failed to deploy workload cluster " + deploy_status[1])
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to deploy workload cluster " + deploy_status[1],
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
            else:
                if checkTmcEnabled(env):
                    current_app.logger.info("Deploying workload cluster, after verification, using tmc")
                    os.putenv(
                        "TMC_API_TOKEN",
                        request.get_json(force=True)["envSpec"]["saasEndpoints"]["tmcDetails"]["tmcRefreshToken"],
                    )
                    listOfCmdTmcLogin = ["tmc", "login", "--no-configure", "-name", TmcUser.USER_VSPHERE]
                    runProcess(listOfCmdTmcLogin)
                    try:
                        osName = str(request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadBaseOs"])
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
                    tmc_url = request.get_json(force=True)["envSpec"]["saasEndpoints"]["tmcDetails"]["tmcInstanceURL"]
                    provisoner = "default"
                    management_url = (
                        tmc_url
                        + "/v1alpha1/managementclusters/"
                        + management_cluster
                        + "/provisioners/"
                        + provisoner
                        + "/tanzukubernetesclusters"
                    )
                    refreshToken = request.get_json(force=True)["envSpec"]["saasEndpoints"]["tmcDetails"][
                        "tmcRefreshToken"
                    ]

                    url = (
                        "https://console.cloud.vmware.com/csp/gateway/am/api/auth/api-tokens/authorize?refresh_token="
                        + refreshToken
                    )
                    headers_ref = {}
                    payload_ref = {}
                    response_login = requests.request("POST", url, headers=headers_ref, data=payload_ref, verify=False)
                    if response_login.status_code != 200:
                        return "login failed using provided TMC refresh token", 500

                    access_token = response_login.json()["access_token"]

                    headers_ = {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Authorization": access_token,
                    }
                    register_payload = tmcBodyClusterCreation(
                        management_cluster,
                        provisoner,
                        workload_cluster_name,
                        clusterGroup,
                        pod_cidr,
                        service_cidr,
                        re,
                        vcenter_ip,
                        cpu,
                        disk,
                        memory,
                        machineCount,
                        AkoType.type_ako_set,
                        version,
                        datacenter_path,
                        datastore_path,
                        workload_folder_path,
                        workload_network_folder_path,
                        workload_resource_path,
                        osName,
                        osVersion,
                        "amd64",
                        templatePath,
                        proxy_name,
                        controlPlaneNodeCount,
                    )
                    modified_payload = json.dumps(register_payload, ensure_ascii=True, sort_keys=True, indent=4)
                    response = requests.request(
                        "POST", management_url, headers=headers_, data=modified_payload, verify=False
                    )
                    if response.status_code != 200:
                        current_app.logger.error("Failed to run command to create shared cluster " + str(response.text))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to run command to create shared cluster " + str(response.text),
                            "STATUS_CODE": 500,
                        }
                        return jsonify(d), 500
                    """command_status_v = runShellCommandAndReturnOutputAsList(createWorkloadCluster)
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
                                "STATUS_CODE": 500
                            }
                            return jsonify(d), 500"""
        else:
            current_app.logger.info("Workload cluster is already deployed and running")
            deployWorkload = True
            found = True
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
        if verifyPodsAreRunning(workload_cluster_name, command_status[0], RegexPattern.running):
            found = True
        while not verifyPodsAreRunning(workload_cluster_name, command_status[0], RegexPattern.running) and count < 60:
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
    """lisOfCommand = ["kubectl", "label", "cluster",
                    workload_cluster_name, AkoType.KEY + "=" + AkoType.type_ako_set]
    status = runShellCommandAndReturnOutputAsList(lisOfCommand)
    if status[1] != 0:
        if not str(status[0]).__contains__("already has a value"):
            current_app.logger.error("Failed to apply ako label " + str(status[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to apply ako label " + str(status[0]),
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
    else:
        current_app.logger.info(status[0])"""
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
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    if tmc_flag:
        if not deployWorkload:
            for i in tqdm(range(180), desc="Waiting…", ascii=False, ncols=75):
                time.sleep(1)

    current_app.logger.info("Ako pods are running on waiting " + str(count_ako * 30))
    connectToWorkload = connectToWorkLoadCluster(env)
    if connectToWorkload[1] != 200:
        current_app.logger.error("Switching context to workload failed " + connectToWorkload[0].json["msg"])
        d = {
            "responseType": "ERROR",
            "msg": "Switching context to workload failed " + connectToWorkload[0].json["msg"],
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    current_app.logger.info(
        "Successfully configured workload cluster and ako pods are running on waiting " + str(count_ako * 30)
    )
    if checkEnableIdentityManagement(env):
        current_app.logger.info("Validating pinniped installation status")
        check_pinniped = checkPinnipedInstalled()
        if check_pinniped[1] != 200:
            current_app.logger.error(check_pinniped[0].json["msg"])
            d = {"responseType": "ERROR", "msg": check_pinniped[0].json["msg"], "STATUS_CODE": 500}
            return jsonify(d), 500
        if env == Env.VSPHERE:
            cluster_admin_users = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadRbacUserRoleSpec"][
                "clusterAdminUsers"
            ]
            admin_users = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadRbacUserRoleSpec"][
                "adminUsers"
            ]
            edit_users = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadRbacUserRoleSpec"][
                "editUsers"
            ]
            view_users = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadRbacUserRoleSpec"][
                "viewUsers"
            ]
        elif env == Env.VCF:
            cluster_admin_users = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadRbacUserRoleSpec"][
                "clusterAdminUsers"
            ]
            admin_users = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadRbacUserRoleSpec"][
                "adminUsers"
            ]
            edit_users = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadRbacUserRoleSpec"][
                "editUsers"
            ]
            view_users = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadRbacUserRoleSpec"][
                "viewUsers"
            ]
        rbac_user_status = createRbacUsers(
            workload_cluster_name,
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
    if (Tkg_version.TKG_VERSION != "1.5") and checkTmcEnabled(env):
        pass
        # isWorkProxy = "false"
        # if checkWorkloadProxyEnabled(env):
        #     isWorkProxy = "true"
        # state = registerWithTmcOnSharedAndWorkload(env, workload_cluster_name, isWorkProxy, "workload")
        # if state[1] != 200:
        #     current_app.logger.error(state[0].json["msg"])
        #     d = {"responseType": "ERROR", "msg": state[0].json["msg"], "STATUS_CODE": 500}
        #     return jsonify(d), 500
    elif checkTmcEnabled(env) and Tkg_version.TKG_VERSION == "2.1":
        current_app.logger.info("Cluster is already deployed via TMC")
        if checkDataProtectionEnabled(env, "workload"):
            is_enabled = enable_data_protection(env, workload_cluster_name, management_cluster)
            if not is_enabled[0]:
                current_app.logger.error(is_enabled[1])
                d = {"responseType": "ERROR", "msg": is_enabled[1], "STATUS_CODE": 500}
                return jsonify(d), 500
            current_app.logger.info(is_enabled[1])
    elif checkTmcEnabled(env):
        current_app.logger.info("Cluster is already deployed via TMC")
    else:
        current_app.logger.info("TMC is deactivated")
        current_app.logger.info("Check whether data protection is to be enabled via Velero on Workload Cluster")
        if checkDataProtectionEnabledVelero(env, "workload"):
            workload_cluster_name = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadClusterName"]
            commands_workload = ["tanzu", "cluster", "kubeconfig", "get", workload_cluster_name, "--admin"]
            kubeContextCommand_workload = grabKubectlCommand(commands_workload, RegexPattern.SWITCH_CONTEXT_KUBECTL)
            if kubeContextCommand_workload is None:
                current_app.logger.error("Failed to get switch to workload cluster context command")
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get switch to workload cluster context command",
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            lisOfSwitchContextCommand_workload = str(kubeContextCommand_workload).split(" ")
            status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand_workload)
            if status[1] != 0:
                current_app.logger.error("Failed to get switch to workload cluster context " + str(status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get switch to workload cluster context " + str(status[0]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            current_app.logger.info("Switched to " + workload_cluster_name + " context")
            is_enabled = enable_data_protection_velero("workload", env)
            if not is_enabled[0]:
                current_app.logger.error("Failed to enable data protection via velero on Workload Cluster")
                current_app.logger.error(is_enabled[1])
                d = {"responseType": "ERROR", "msg": is_enabled[1], "STATUS_CODE": 500}
                return jsonify(d), 500
            current_app.logger.info("Successfully enabled data protection via Velero on Workload Cluster")
            current_app.logger.info(is_enabled[1])
    to = registerTanzuObservability(workload_cluster_name, env, size)
    if to[1] != 200:
        current_app.logger.error(to[0].json["msg"])
        return to[0], to[1]
    tsm = registerTSM(workload_cluster_name, env, size)
    if tsm[1] != 200:
        current_app.logger.error(tsm[0].json["msg"])
        return tsm[0], tsm[1]
    d = {"responseType": "SUCCESS", "msg": "Successfully deployed cluster " + workload_cluster_name, "STATUS_CODE": 200}
    return jsonify(d), 200


def waitForGrepProcess(list1, list2, podName, dir):
    cert_state = grabPipeOutputChagedDir(list1, list2, dir)
    if cert_state[1] != 0:
        current_app.logger.error("Failed to apply " + podName + " " + cert_state[0])
        d = {"responseType": "ERROR", "msg": "Failed to apply " + podName + " " + cert_state[0], "STATUS_CODE": 500}
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
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500, count_cert
    d = {"responseType": "ERROR", "msg": "Failed to apply " + podName + " " + cert_state[0], "STATUS_CODE": 500}

    return jsonify(d), 200, count_cert


def getVipNetworkIpNetMask(ip, csrf2, name, aviVersion):
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
                if re["name"] == name:
                    for sub in re["configured_subnets"]:
                        return str(sub["prefix"]["ip_addr"]["addr"]) + "/" + str(sub["prefix"]["mask"]), "SUCCESS"
            else:
                next_url = None if not response_csrf.json()["next"] else response_csrf.json()["next"]
                while len(next_url) > 0:
                    response_csrf = requests.request("GET", next_url, headers=headers, data=body, verify=False)
                    for re in response_csrf.json()["results"]:
                        if re["name"] == name:
                            for sub in re["configured_subnets"]:
                                return (
                                    str(sub["prefix"]["ip_addr"]["addr"]) + "/" + str(sub["prefix"]["mask"]),
                                    "SUCCESS",
                                )
                    next_url = None if not response_csrf.json()["next"] else response_csrf.json()["next"]

        return "NOT_FOUND", "FAILED"
    except KeyError:
        return "NOT_FOUND", "FAILED"


def createAkoFile(
    ip, cluster_name, wipCidr, tkgMgmtDataPg, cluster_vip_name, workload_network, cluster_vip_cidr, tier1_path, env
):
    if checkAirGappedIsEnabled(env):
        air_gapped_repo = str(
            request.get_json(force=True)["envSpec"]["customRepositorySpec"]["tkgCustomImageRepository"]
        )
        air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
    se_cloud = Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE
    cloud_name = Cloud.CLOUD_NAME_VSPHERE

    workload_nw = dict(networkName=workload_network)
    lis_ = [workload_nw]

    if checkAviL7EnabledForWorkload(env):
        import ipaddress

        net = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadGatewayCidr"]
        network = str(ipaddress.IPv4Network(net, strict=False))
        list_cidrs = [network]
        workload_nw = dict(networkName=workload_network, cidrs=list_cidrs)
        lis_a7 = [workload_nw]
        extra_config = dict(
            cniPlugin="antrea",
            disableStaticRouteSync=True,
            ingress=dict(
                disableIngressClass=False,
                defaultIngressController=False,
                nodeNetworkList=lis_a7,
                serviceType="NodePortLocal",
                shardVSSize="MEDIUM",
            ),
        )
        if env == Env.VCF:
            se_cloud = Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE.replace("vsphere", "nsxt")
            cloud_name = Cloud.CLOUD_NAME_VSPHERE.replace("vsphere", "nsxt")
            extra_config = dict(
                cniPlugin="antrea",
                disableStaticRouteSync=True,
                l4Config=dict(autoFQDN="disabled"),
                layer7Only=False,
                networksConfig=dict(enableRHI=False, nsxtT1LR=tier1_path),
                ingress=dict(
                    disableIngressClass=False, nodeNetworkList=lis_a7, serviceType="NodePortLocal", shardVSSize="MEDIUM"
                ),
            )
    else:
        extra_config = dict(
            cniPlugin="antrea",
            disableStaticRouteSync=True,
            ingress=dict(defaultIngressController=False, disableIngressClass=True, nodeNetworkList=lis_),
        )
        if env == Env.VCF:
            se_cloud = Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE.replace("vsphere", "nsxt")
            cloud_name = Cloud.CLOUD_NAME_VSPHERE.replace("vsphere", "nsxt")
            extra_config = dict(
                cniPlugin="antrea",
                disableStaticRouteSync=True,
                l4Config=dict(autoFQDN="disabled"),
                layer7Only=False,
                networksConfig=dict(enableRHI=False, nsxtT1LR=tier1_path),
                ingress=dict(defaultIngressController=True, disableIngressClass=True, nodeNetworkList=lis_),
            )
    data = dict(
        apiVersion="networking.tkg.tanzu.vmware.com/v1alpha1",
        kind="AKODeploymentConfig",
        metadata=dict(generation=2, name="install-ako-for-workload-set01"),
        spec=dict(
            adminCredentialRef=dict(name="avi-controller-credentials", namespace="tkg-system-networking"),
            certificateAuthorityRef=dict(name="avi-controller-ca", namespace="tkg-system-networking"),
            cloudName=cloud_name,
            clusterSelector=dict(matchLabels=dict(type=AkoType.type_ako_set)),
            controlPlaneNetwork=dict(cidr=cluster_vip_cidr, name=cluster_vip_name),
            controller=ip,
            dataNetwork=dict(cidr=wipCidr, name=tkgMgmtDataPg),
            extraConfigs=extra_config,
            serviceEngineGroup=se_cloud,
        ),
    )
    filePath = os.path.join(Paths.CLUSTER_PATH, cluster_name, "ako_vsphere_workloadset1.yaml")
    with open(filePath, "w") as outfile:
        yaml = ruamel.yaml.YAML()
        yaml.indent(mapping=2, sequence=4, offset=0)
        yaml.dump(data, outfile)


def changeNetworks(vcenter_ip, vcenter_username, password, engine_name):
    os.putenv("GOVC_URL", "https://" + vcenter_ip + "/sdk")
    os.putenv("GOVC_USERNAME", vcenter_username)
    os.putenv("GOVC_PASSWORD", password)
    os.putenv("GOVC_INSECURE", "true")
    workload_network_name = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadNetworkName"]
    change_VM_Net = ["govc", "vm.network.change", "-vm=" + engine_name, "-net", workload_network_name, "ethernet-2"]
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
        d = {"responseType": "ERROR", "msg": "Failed to apply " + podName + " " + cert_state[0], "STATUS_CODE": 500}
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
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500, count_cert
    d = {"responseType": "ERROR", "msg": "Failed to apply " + podName + " " + cert_state[0], "STATUS_CODE": 500}
    return jsonify(d), 200, count_cert


def create_archostrated(
    ip_, vcenter_ip, vcenter_username, password, data_center, data_store, cluster_name, workload_vip, aviVersion, env
):
    govc_client = GovcClient(current_app.config, LocalCmdHelper())
    ip = govc_client.get_vm_ip(ip_, datacenter_name=data_center)
    if ip is None:
        current_app.logger.error("Failed to get IP of AVI controller")
        d = {"responseType": "ERROR", "msg": "Failed to get IP of AVI controller", "STATUS_CODE": 500}
        return jsonify(d), 500
    ip = ip[0]
    workload_cluster_name = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadClusterName"]
    workload_cluster_path = Paths.CLUSTER_PATH + workload_cluster_name
    if not createClusterFolder(workload_cluster_name):
        d = {"responseType": "ERROR", "msg": "Failed to create directory: " + workload_cluster_path, "STATUS_CODE": 500}
        return jsonify(d), 500
    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        current_app.logger.error("Failed to get csrf from new password")
        d = {"responseType": "ERROR", "msg": "Failed to get csrf from new password", "STATUS_CODE": 500}
        return jsonify(d), 500
    get_cloud = getCloudStatus(ip, csrf2, aviVersion, Cloud.CLOUD_NAME.replace("vmc", "vsphere"))
    if get_cloud[0] is None:
        current_app.logger.error("Failed to get cloud status " + str(get_cloud[1]))
        d = {"responseType": "ERROR", "msg": "Failed to get cloud status " + str(get_cloud[1]), "STATUS_CODE": 500}
        return jsonify(d), 500

    if get_cloud[0] == "NOT_FOUND":
        current_app.logger.error("Requested cloud is not created")
        d = {"responseType": "ERROR", "msg": "Requested cloud is not created", "STATUS_CODE": 500}
        return jsonify(d), 500
    else:
        cloud_url = get_cloud[0]
    get_wip = getVipNetwork(ip, csrf2, workload_vip, aviVersion)
    if get_wip[0] is None:
        current_app.logger.error("Failed to get service engine VIP network " + str(get_wip[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get service engine VIP network " + str(get_wip[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500

    if get_wip[0] == "NOT_FOUND":
        current_app.logger.info("Creating New VIP network " + workload_vip)
        vip_net = createVipNetwork(ip, csrf2, cloud_url, workload_vip, Type.WORKLOAD, aviVersion)
        if vip_net[0] is None:
            current_app.logger.error("Failed to create VIP network " + str(vip_net[1]))
            d = {"responseType": "ERROR", "msg": "Failed to create VIP network " + str(vip_net[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
        wip_url = vip_net[0]
        current_app.logger.info("Created New VIP network " + workload_vip)
    else:
        wip_url = get_wip[0]
    get_se_cloud = getSECloudStatus(ip, csrf2, aviVersion, Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE)
    if get_se_cloud[0] is None:
        current_app.logger.error("Failed to get service engine cloud status " + str(get_se_cloud[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get service engine cloud status " + str(get_se_cloud[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500

    if get_se_cloud[0] == "NOT_FOUND":
        current_app.logger.info("Creating New service engine cloud " + Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE)
        cloud_se = createSECloud_Arch(
            ip, csrf2, cloud_url, Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE, aviVersion, "Workload"
        )
        if cloud_se[0] is None:
            current_app.logger.error("Failed to create service engine cloud " + str(cloud_se[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create  service engine cloud " + str(cloud_se[1]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        se_cloud_url = cloud_se[0]
    else:
        se_cloud_url = get_se_cloud[0]
    get_ipam = getIpam(ip, csrf2, Cloud.IPAM_NAME_VSPHERE, aviVersion)
    if get_ipam[0] is None or get_ipam[0] == "NOT_FOUND":
        current_app.logger.error("Failed to get service engine Ipam " + str(get_ipam[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get service engine Ipam " + str(get_ipam[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    else:
        ipam_url = get_ipam[0]
    ipam = getIPamDetails(ip, csrf2, ipam_url, wip_url, aviVersion)
    if ipam[0] is None:
        current_app.logger.error("Failed to get service engine Ipam Details " + str(ipam[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get service engine Ipam Details  " + str(ipam[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    vm_state = checkVmPresent(vcenter_ip, vcenter_username, password, ip_)
    if vm_state is None:
        current_app.logger.error("Avi controller not found ")
        d = {"responseType": "ERROR", "msg": "Avi controller not found ", "STATUS_CODE": 500}
        return jsonify(d), 500
    avi_uuid = vm_state.config.uuid
    current_app.config["se_ova_path"] = "/tmp/" + avi_uuid + ".ova"
    new_cloud_status = updateIpamWithDataNetwork(ip, csrf2, ipam_url, aviVersion)
    if new_cloud_status[0] is None:
        current_app.logger.error("Failed to update Ipam " + str(new_cloud_status[1]))
        d = {"responseType": "ERROR", "msg": "Failed to update Ipam" + str(new_cloud_status[1]), "STATUS_CODE": 500}
        return jsonify(d), 500
    # if not validateNetworkAvailable(SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT, vcenter_ip, vcenter_username,
    # password):
    # current_app.logger.error("Failed to find the network " + SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT)
    # d = {
    # "responseType": "ERROR",
    # "msg": "Failed to find the network " + SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT,
    # "STATUS_CODE": 500
    # }
    # return jsonify(d), 500
    dep = controllerDeployment(
        ip,
        csrf2,
        data_center,
        data_store,
        cluster_name,
        vcenter_ip,
        vcenter_username,
        password,
        se_cloud_url,
        "./vsphere/workloadConfig/se.json",
        "detailsOfServiceEngine3.json",
        "detailsOfServiceEngine4.json",
        ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME.replace("vmc", "vsphere"),
        ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME2.replace("vmc", "vsphere"),
        3,
        Type.WORKLOAD,
        1,
        aviVersion,
    )
    if dep[1] != 200:
        current_app.logger.error("Controller deployment failed" + str(dep[0]))
        d = {"responseType": "ERROR", "msg": "Controller deployment failed " + str(dep[0]), "STATUS_CODE": 500}
        return jsonify(d), 500
    management_cluster = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtClusterName"]
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
    data_network_workload = request.get_json(force=True)["tkgWorkloadDataNetwork"]["tkgWorkloadDataNetworkName"]
    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        current_app.logger.error("Failed to get csrf from new password")
        d = {"responseType": "ERROR", "msg": "Failed to get csrf from new password", "STATUS_CODE": 500}
        return jsonify(d), 500
    wip = getVipNetworkIpNetMask(ip, csrf2, data_network_workload, aviVersion)
    if wip[0] is None or wip[0] == "NOT_FOUND":
        current_app.logger.error("Failed to get wip netmask ")
        d = {"responseType": "ERROR", "msg": "Failed to get wip netmask ", "STATUS_CODE": 500}
        return jsonify(d), 500

    cluster_vip_name = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"][
        "tkgClusterVipNetworkName"
    ]
    cluster_vip_cidr_ = getVipNetworkIpNetMask(ip, csrf2, cluster_vip_name, aviVersion)
    if env == Env.VCF:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0],
        }
        status, value = getCloudConnectUser(ip, headers)
        nsxt_cred = value["nsxUUid"]
        tier1_id, status_tier1 = fetchTier1GatewayId(ip, headers, nsxt_cred)
        if tier1_id is None:
            current_app.logger.error("Failed to get Tier 1 details " + str(status_tier1))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get Tier 1 details " + str(status_tier1),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        tier1 = status_tier1
    else:
        tier1 = ""
    workload_network_name = request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadNetworkName"]
    workload_cluster = workload_cluster_name
    createAkoFile(
        ip,
        workload_cluster,
        wip[0],
        data_network_workload,
        cluster_vip_name,
        workload_network_name,
        cluster_vip_cidr_[0],
        tier1,
        env,
    )
    workload_cluster_path = Paths.CLUSTER_PATH + workload_cluster_name
    lisOfCommand = [
        "kubectl",
        "apply",
        "-f",
        workload_cluster_path + "/ako_vsphere_workloadset1.yaml",
        "--validate=false",
    ]
    status = runShellCommandAndReturnOutputAsList(lisOfCommand)
    if status[1] != 0:
        if not str(status[0]).__contains__("already has a value"):
            current_app.logger.error("Failed to apply Ako" + str(status[0]))
            d = {"responseType": "ERROR", "msg": "Failed to apply Ako " + str(status[0]), "STATUS_CODE": 500}
            return jsonify(d), 500
        current_app.logger.info("Applied Ako successfully")
    d = {"responseType": "SUCCESS", "msg": "Successfully configured workload cluster", "STATUS_CODE": 200}
    return jsonify(d), 200


def config_service_engines(ip, csrf2, vcenter_ip, vcenter_username, password, data_center, aviVersion):
    govc_client = GovcClient(current_app.config, LocalCmdHelper())
    count = 0
    found = False
    seIp3 = None
    while count < 120:
        try:
            current_app.logger.info("Waited " + str(10 * count) + "s to get controller 3 ip, retrying")
            seIp3 = govc_client.get_vm_ip(
                ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME.replace("vmc", "vsphere"), datacenter_name=data_center
            )
            if seIp3 is not None:
                found = True
                seIp3 = seIp3[0]
                break
        except Exception:
            pass
        time.sleep(10)
        count = count + 1

    if not found:
        current_app.logger.error("Controller 3 is not up, failed to get IP")
        d = {"responseType": "ERROR", "msg": "Controller 3 is not up, failed to get IP", "STATUS_CODE": 500}
        return jsonify(d), 500
    count = 0
    found = False
    seIp4 = None
    while count < 120:
        try:
            current_app.logger.info("Waited " + str(10 * count) + "s to get controller 4 ip, retrying")
            seIp4 = govc_client.get_vm_ip(
                ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME2.replace("vmc", "vsphere"), datacenter_name=data_center
            )
            if seIp4 is not None:
                found = True
                seIp4 = seIp4[0]
                break
        except Exception:
            pass
        time.sleep(10)
        count = count + 1

    if not found:
        current_app.logger.error("Controller 4 is not up, failed to get IP")
        d = {"responseType": "ERROR", "msg": "Controller 4 is not up, failed to get IP ", "STATUS_CODE": 500}
        return jsonify(d), 500
    urlFromServiceEngine1 = listAllServiceEngine(
        ip,
        csrf2,
        3,
        seIp3,
        ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME.replace("vmc", "vsphere"),
        vcenter_ip,
        vcenter_username,
        password,
        aviVersion,
    )
    if urlFromServiceEngine1[0] is None:
        current_app.logger.error("Failed to get service engine 3 details" + str(urlFromServiceEngine1[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to  get service engine details " + str(urlFromServiceEngine1[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    urlFromServiceEngine2 = listAllServiceEngine(
        ip,
        csrf2,
        3,
        seIp4,
        ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME2.replace("vmc", "vsphere"),
        vcenter_ip,
        vcenter_username,
        password,
        aviVersion,
    )
    if urlFromServiceEngine2[0] is None:
        current_app.logger.error("Failed to get service engine 4 details" + str(urlFromServiceEngine2[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get service engine details " + str(urlFromServiceEngine2[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    details1 = getDetailsOfServiceEngine(
        ip, csrf2, urlFromServiceEngine1[0], "detailsOfServiceEngine3.json", aviVersion
    )
    if details1[0] is None:
        current_app.logger.error("Failed to get details of engine 3" + str(details1[1]))
        d = {"responseType": "ERROR", "msg": "Failed to get details of engine 3" + str(details1[1]), "STATUS_CODE": 500}
        return jsonify(d), 500
    details2 = getDetailsOfServiceEngine(
        ip, csrf2, urlFromServiceEngine2[0], "detailsOfServiceEngine4.json", aviVersion
    )
    if details2[0] is None:
        current_app.logger.error("Failed to get details of engine 4 " + str(details2[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to  get details of engine 4 " + str(details2[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    get_se_cloud = getSECloudStatus(ip, csrf2, aviVersion, Cloud.SE_WORKLOAD_GROUP_NAME.replace("vmc", "vsphere"))
    if get_se_cloud[0] is None:
        current_app.logger.error("Failed to get service engine cloud status " + str(get_se_cloud[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get se cloud status " + str(get_se_cloud[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500

    if get_se_cloud[0] == "NOT_FOUND":
        current_app.logger.error("Failed to get service engine cloud " + str(get_se_cloud[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create  get service engine cloud " + str(get_se_cloud[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    else:
        se_cloud_url = get_se_cloud[0]
    change = changeNetworks(
        vcenter_ip, vcenter_username, password, ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME.replace("vmc", "vsphere")
    )
    if change[1] != 200:
        current_app.logger.error("Failed to change Network " + str(change[0]))
        d = {"responseType": "ERROR", "msg": "Failed to change Network " + str(change[0]), "STATUS_CODE": 500}
        return jsonify(d), 500

    se_engines = changeSeGroupAndSetInterfaces(
        ip,
        csrf2,
        urlFromServiceEngine1[0],
        se_cloud_url,
        "detailsOfServiceEngine3.json",
        vcenter_ip,
        vcenter_username,
        password,
        ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME.replace("vmc", "vsphere"),
        Type.WORKLOAD,
        2,
        aviVersion,
    )
    if se_engines[0] is None:
        current_app.logger.error(
            "Failed to change service engine group and set interfaces engine 3" + str(se_engines[1])
        )
        d = {
            "responseType": "ERROR",
            "msg": "Failed to change service engine group and set interfaces engine 3" + str(se_engines[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    change = changeNetworks(
        vcenter_ip,
        vcenter_username,
        password,
        ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME2.replace("vmc", "vsphere"),
    )
    if change[1] != 200:
        current_app.logger.error("Failed to change Network for service engine controller 4 " + str(change[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to change Network for service engine controller 4 " + str(change[0]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    se_engines = changeSeGroupAndSetInterfaces(
        ip,
        csrf2,
        urlFromServiceEngine2[0],
        se_cloud_url,
        "detailsOfServiceEngine4.json",
        vcenter_ip,
        vcenter_username,
        password,
        ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME2.replace("vmc", "vsphere"),
        Type.WORKLOAD,
        2,
        aviVersion,
    )
    if se_engines[0] is None:
        current_app.logger.error(
            "Failed to change service engine group and set interfaces engine 4" + str(se_engines[1])
        )
        d = {
            "responseType": "ERROR",
            "msg": "Failed to change service engine group and set interfaces engine 4" + str(se_engines[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    current_app.logger.info("Configured service engines successfully ")
    d = {"responseType": "ERROR", "msg": "Configured service engines successfully", "STATUS_CODE": 200}
    return jsonify(d), 200
