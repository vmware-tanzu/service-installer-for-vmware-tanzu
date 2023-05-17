# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import base64
import json
import logging
import os
import sys
import time

import requests
from flask import Blueprint, current_app, jsonify, request
from jinja2 import Template
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from ruamel import yaml
from tqdm import tqdm

from common.certificate_base64 import getBase64CertWriteToFile
from common.common_utilities import (
    VrfType,
    addStaticRoute,
    checkAirGappedIsEnabled,
    checkAndWaitForAllTheServiceEngineIsUp,
    checkEnableIdentityManagement,
    checkMgmtProxyEnabled,
    checkPinnipedDexServiceStatus,
    checkPinnipedInstalled,
    checkPinnipedServiceStatus,
    checkTmcEnabled,
    configureKubectl,
    create_virtual_service,
    createClusterFolder,
    createRbacUsers,
    createSubscribedLibrary,
    disable_proxy,
    downloadAndPushKubernetesOvaMarketPlace,
    envCheck,
    get_avi_version,
    getCloudStatus,
    getClusterID,
    getClusterStatusOnTanzu,
    getSECloudStatus,
    getVipNetworkIpNetMask,
    getVrfAndNextRoutId,
    grabHostFromUrl,
    grabPortFromUrl,
    isAviHaEnabled,
    isEnvTkgm,
    isEnvTkgs_ns,
    isEnvTkgs_wcp,
    loadBomFile,
    obtain_avi_version,
    obtain_second_csrf,
    preChecks,
    registerTMCTKGs,
    registerWithTmc,
    runSsh,
    switchToManagementContext,
    update_template_in_ova,
)
from common.model.vsphereSpec import VsphereMasterSpec
from common.operation.constants import (
    AkoType,
    Cloud,
    ControllerLocation,
    Env,
    KubernetesOva,
    NSXtCloud,
    Paths,
    RegexPattern,
    ResourcePoolAndFolderName,
    Tkg_version,
    Type,
)
from common.operation.ShellHelper import (
    grabKubectlCommand,
    runProcess,
    runShellCommandAndReturnOutputAsList,
    runShellCommandWithPolling,
    verifyPodsAreRunning,
)
from common.operation.vcenter_operations import (
    checkforIpAddress,
    checkVmPresent,
    create_folder,
    createResourcePool,
    destroy_vm,
    getMacAddresses,
    getSi,
)
from common.replace_value import (
    generateVsphereConfiguredSubnets,
    generateVsphereConfiguredSubnetsForSe,
    generateVsphereConfiguredSubnetsForSeandVIP,
    replaceMac,
    replaceSe,
    replaceSeGroup,
    replaceValueSysConfig,
)
from common.util.file_helper import FileHelper
from common.util.ssl_helper import get_base64_cert
from vmc.managementConfig.management_config import (
    downloadSeOva,
    generateSeOva,
    generateToken,
    getClusterUUid,
    getConnectedStatus,
    getDetailsOfServiceEngine,
    getVipNetwork,
    updateNewCloudSeGroup,
)
from vsphere.managementConfig.vsphere_tkgs_management_config import (
    configTkgsCloud,
    configureTkgConfiguration,
    enableWCP,
)

logger = logging.getLogger(__name__)
vsphere_management_config = Blueprint("vsphere_management_config", __name__, static_folder="managementConfig")
sys.path.append(".../")
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


@vsphere_management_config.route("/api/tanzu/vsphere/tkgmgmt", methods=["POST"])
def configManagementCluster():
    config_cloud = configCloud()
    if config_cloud[1] != 200:
        current_app.logger.error(str(config_cloud[0].json["msg"]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to Config management cluster " + str(config_cloud[0].json["msg"]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    config_mgmt = configTkgMgmt()
    if config_mgmt[1] != 200:
        current_app.logger.error(str(config_mgmt[0].json["msg"]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to Config management cluster " + str(config_mgmt[0].json["msg"]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    d = {"responseType": "SUCCESS", "msg": "Management cluster configured Successfully", "STATUS_CODE": 200}
    current_app.logger.info("Management cluster configured Successfully")
    return jsonify(d), 200


@vsphere_management_config.route("/api/tanzu/vsphere/tkgmgmt/alb/config", methods=["POST"])
def configCloud():
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
    aviVersion = get_avi_version(env)
    password = current_app.config["VC_PASSWORD"]
    vcenter_username = current_app.config["VC_USER"]
    vcenter_ip = current_app.config["VC_IP"]
    cluster_name = current_app.config["VC_CLUSTER"]
    data_center = current_app.config["VC_DATACENTER"]
    data_store = current_app.config["VC_DATASTORE"]
    req = True
    refToken = request.get_json(force=True)["envSpec"]["marketplaceSpec"]["refreshToken"]
    license_type = "enterprise"
    if env == Env.VSPHERE:
        if not (isEnvTkgs_wcp(env) or isEnvTkgs_ns(env)):
            license_type = str(request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["typeOfLicense"])
        else:
            license_type = str(request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["typeOfLicense"])
    if refToken and (env == Env.VSPHERE or env == Env.VCF):
        if not (isEnvTkgs_wcp(env) or isEnvTkgs_ns(env)):
            kubernetes_ova_os = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtBaseOs"]
            kubernetes_ova_version = KubernetesOva.KUBERNETES_OVA_LATEST_VERSION
            current_app.logger.info("Kubernetes OVA configs for management cluster")
            down_status = downloadAndPushKubernetesOvaMarketPlace(env, kubernetes_ova_version, kubernetes_ova_os)
            if down_status[0] is None:
                current_app.logger.error(down_status[1])
                d = {"responseType": "ERROR", "msg": down_status[1], "STATUS_CODE": 500}
                return jsonify(d), 500
    else:
        current_app.logger.info("MarketPlace refresh token is not provided, skipping the download of kubernetes ova")
    if isEnvTkgs_wcp(env):
        avi_fqdn = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviController01Fqdn"]
        # ip_ = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviClusterIp"]
        if isAviHaEnabled(env):
            aviClusterFqdn = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviClusterFqdn"]

    else:
        avi_fqdn = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController01Fqdn"]
        aviClusterFqdn = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviClusterFqdn"]
    # if not avi_fqdn:
    #     controller_name = ControllerLocation.CONTROLLER_NAME_VSPHERE
    # else:
    #     controller_name = avi_fqdn
    if isAviHaEnabled(env):
        ip = aviClusterFqdn
    else:
        ip = avi_fqdn
    if ip is None:
        current_app.logger.error("Failed to get IP of AVI controller")
        d = {"responseType": "ERROR", "msg": "Failed to get IP of avi controller", "STATUS_CODE": 500}
        return jsonify(d), 500
    isNonOrchestrated = False
    try:
        mode = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["modeOfDeployment"]
        if mode == "non-orchestrated":
            isNonOrchestrated = True
    except Exception:
        isNonOrchestrated = False
    if isNonOrchestrated:
        status = config_orchestrated(
            env,
            vcenter_ip,
            vcenter_username,
            password,
            data_center,
            data_store,
            cluster_name,
            aviVersion,
            license_type=license_type,
        )
        if status[1] != 200:
            current_app.logger.error("Failed to configure management cluster " + str(status[0].json["msg"]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to config management cluster " + str(status[0].json["msg"]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
    else:
        csrf2 = obtain_second_csrf(ip, env)
        if csrf2 is None:
            current_app.logger.error("Failed to get csrf from new set password")
            d = {"responseType": "ERROR", "msg": "Failed to get csrf from new set password", "STATUS_CODE": 500}
            return jsonify(d), 500
        deployed_avi_version = obtain_avi_version(ip, env)
        if deployed_avi_version[0] is None:
            current_app.logger.error("Failed to login and obtain avi version" + str(deployed_avi_version[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to login and obtain avi version " + deployed_avi_version[1],
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        aviVersion = deployed_avi_version[0]
        default = waitForCloudPlacementReady(ip, csrf2, "Default-Cloud", aviVersion)
        if default[0] is None:
            current_app.logger.error("Failed to get default cloud status")
            d = {"responseType": "ERROR", "msg": "Failed to get default cloud status", "STATUS_CODE": 500}
            return jsonify(d), 500
        if isEnvTkgs_wcp(env):
            configTkgs = configTkgsCloud(ip, csrf2, aviVersion, license_type=license_type)
            if configTkgs[0] is None:
                current_app.logger.error("Failed to config tkgs " + str(configTkgs[1]))
                d = {"responseType": "ERROR", "msg": "Failed to config tkgs " + str(configTkgs[1]), "STATUS_CODE": 500}
                return jsonify(d), 500
        else:
            cloudName = Cloud.CLOUD_NAME_VSPHERE
            if env == Env.VCF:
                cloudName = Cloud.CLOUD_NAME_VSPHERE.replace("vsphere", "nsxt")
            get_cloud = getCloudStatus(ip, csrf2, aviVersion, cloudName)
            if get_cloud[0] is None:
                current_app.logger.error("Failed to get cloud status " + str(get_cloud[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get cloud status " + str(get_cloud[1]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500

            isGen = False
            if get_cloud[0] == "NOT_FOUND":
                if req:
                    for i in tqdm(range(60), desc="Waiting…", ascii=False, ncols=75):
                        time.sleep(1)
                isGen = True
                if env == Env.VCF:
                    current_app.logger.info("Creating New cloud " + cloudName)
                    cloud = createNsxtCloud(ip, csrf2, aviVersion)
                    if cloud[0] is None:
                        current_app.logger.error("Failed to create cloud " + str(cloud[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to create cloud " + str(cloud[1]),
                            "STATUS_CODE": 500,
                        }
                        return jsonify(d), 500
                else:
                    current_app.logger.info("Creating New cloud " + Cloud.CLOUD_NAME_VSPHERE)
                    cloud = createNewCloud(ip, csrf2, aviVersion, license_type=license_type)
                    if cloud[0] is None:
                        current_app.logger.error("Failed to create cloud " + str(cloud[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to create cloud " + str(cloud[1]),
                            "STATUS_CODE": 500,
                        }
                        return jsonify(d), 500
                cloud_url = cloud[0]
            else:
                cloud_url = get_cloud[0]
            if isGen:
                for i in tqdm(range(60), desc="Waiting…", ascii=False, ncols=75):
                    time.sleep(1)
            mgmt_pg = request.get_json(force=True)["tkgComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkName"]
            get_management = getNetworkUrl(ip, csrf2, mgmt_pg, aviVersion)
            if get_management[0] is None:
                current_app.logger.error("Failed to get management network " + str(get_management[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get management network " + str(get_management[1]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            startIp = request.get_json(force=True)["tkgComponentSpec"]["aviMgmtNetwork"]["aviMgmtServiceIpStartRange"]
            endIp = request.get_json(force=True)["tkgComponentSpec"]["aviMgmtNetwork"]["aviMgmtServiceIpEndRange"]
            prefixIpNetmask = seperateNetmaskAndIp(
                request.get_json(force=True)["tkgComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkGatewayCidr"]
            )
            if env == Env.VSPHERE:
                getManagementDetails = getNetworkDetails(
                    ip,
                    csrf2,
                    get_management[0],
                    startIp,
                    endIp,
                    prefixIpNetmask[0],
                    prefixIpNetmask[1],
                    aviVersion,
                    env,
                )
                if getManagementDetails[0] is None:
                    current_app.logger.error("Failed to get management network details " + str(getManagementDetails[2]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get management network details " + str(getManagementDetails[2]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                if getManagementDetails[0] == "AlreadyConfigured":
                    current_app.logger.info("Ip pools are already configured.")
                    if env == Env.VSPHERE:
                        vim_ref = getManagementDetails[2]["vim_ref"]
                    ip_pre = getManagementDetails[2]["subnet_ip"]
                    mask = getManagementDetails[2]["subnet_mask"]
                else:
                    update_resp = updateNetworkWithIpPools(
                        ip, csrf2, get_management[0], "managementNetworkDetails.json", aviVersion
                    )
                    if update_resp[0] != 200:
                        current_app.logger.error("Failed to update management network ip pools " + str(update_resp[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to update management network ip pools " + str(update_resp[1]),
                            "STATUS_CODE": 500,
                        }
                        return jsonify(d), 500
                    if env == Env.VSPHERE:
                        vim_ref = update_resp[2]["vimref"]
                    mask = update_resp[2]["subnet_mask"]
                    ip_pre = update_resp[2]["subnet_ip"]
            if env == Env.VSPHERE:
                new_cloud_status = getDetailsOfNewCloud(ip, csrf2, cloud_url, vim_ref, ip_pre, mask, aviVersion)
                if new_cloud_status[0] is None:
                    current_app.logger.error("Failed to get new cloud details" + str(new_cloud_status[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get new cloud details " + str(new_cloud_status[1]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                updateNewCloudStatus = updateNewCloud(ip, csrf2, cloud_url, aviVersion)
                if updateNewCloudStatus[0] is None:
                    current_app.logger.error("Failed to update cloud " + str(updateNewCloudStatus[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to update cloud " + str(updateNewCloudStatus[1]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                mgmt_data_pg = request.get_json(force=True)["tkgMgmtDataNetwork"]["tkgMgmtDataNetworkName"]
                get_management_data_pg = getNetworkUrl(ip, csrf2, mgmt_data_pg, aviVersion)
                if get_management_data_pg[0] is None:
                    current_app.logger.error(
                        "Failed to get management data network details " + str(get_management_data_pg[1])
                    )
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get management data network details " + str(get_management_data_pg[1]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                startIp = request.get_json(force=True)["tkgMgmtDataNetwork"]["tkgMgmtAviServiceIpStartRange"]
                endIp = request.get_json(force=True)["tkgMgmtDataNetwork"]["tkgMgmtAviServiceIpEndRange"]
                prefixIpNetmask = seperateNetmaskAndIp(
                    request.get_json(force=True)["tkgMgmtDataNetwork"]["tkgMgmtDataNetworkGatewayCidr"]
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
                        "Failed to get management data network details " + str(getManagementDetails_data_pg[2])
                    )
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get management data network details " + str(getManagementDetails_data_pg[2]),
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
                        current_app.logger.error("Failed to update management network details " + str(update_resp[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to update management network details " + str(update_resp[1]),
                            "STATUS_CODE": 500,
                        }
                        return jsonify(d), 500
            mgmt_pg = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"][
                "tkgClusterVipNetworkName"
            ]
            get_vip = getNetworkUrl(ip, csrf2, mgmt_pg, aviVersion)
            if get_vip[0] is None:
                d = {"responseType": "ERROR", "msg": "Failed to get vip network " + str(get_vip[1]), "STATUS_CODE": 500}
                return jsonify(d), 500
            vip_pool = updateVipNetworkIpPools(ip, csrf2, get_vip, aviVersion)
            if vip_pool[1] != 200:
                current_app.logger.error(str(vip_pool[0].json["msg"]))
                d = {"responseType": "ERROR", "msg": str(vip_pool[0].json["msg"]), "STATUS_CODE": 500}
                return jsonify(d), 500
            if env == Env.VSPHERE:
                get_ipam = getIpam(ip, csrf2, Cloud.IPAM_NAME_VSPHERE, aviVersion)
                if get_ipam[0] is None:
                    current_app.logger.error("Failed to get service engine Ipam " + str(get_ipam[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get service engine Ipam " + str(get_ipam[1]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500

                isGen = False
                if get_ipam[0] == "NOT_FOUND":
                    isGen = True
                    current_app.logger.info("Creating IPam " + Cloud.IPAM_NAME_VSPHERE)
                    ipam = createIpam(
                        ip,
                        csrf2,
                        get_management[0],
                        get_management_data_pg[0],
                        get_vip[0],
                        Cloud.IPAM_NAME_VSPHERE,
                        aviVersion,
                    )
                    if ipam[0] is None:
                        current_app.logger.error("Failed to create Ipam " + str(ipam[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to create Ipam " + str(ipam[1]),
                            "STATUS_CODE": 500,
                        }
                        return jsonify(d), 500
                    ipam_url = ipam[0]
                else:
                    ipam_url = get_ipam[0]

                new_cloud_status = getDetailsOfNewCloudAddIpam(ip, csrf2, cloud_url, ipam_url, aviVersion)
                if new_cloud_status[0] is None:
                    current_app.logger.error("Failed to get new cloud details" + str(new_cloud_status[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get new cloud details " + str(new_cloud_status[1]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                updateIpam_re = updateIpam(ip, csrf2, cloud_url, aviVersion)
                if updateIpam_re[0] is None:
                    current_app.logger.error("Failed to update Ipam to cloud " + str(updateIpam_re[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to update Ipam to cloud " + str(updateIpam_re[1]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                cluster_name = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterCluster"]
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
            seGroupName = Cloud.SE_GROUP_NAME_VSPHERE
            if env == Env.VCF:
                seGroupName = Cloud.SE_GROUP_NAME_VSPHERE.replace("vsphere", "nsxt")
            get_se_cloud = getSECloudStatus(ip, csrf2, aviVersion, seGroupName)
            if get_se_cloud[0] is None:
                current_app.logger.error("Failed to get service engine cloud status " + str(get_se_cloud[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get service engine cloud status " + str(get_se_cloud[1]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500

            isGen = False
            if get_se_cloud[0] == "NOT_FOUND":
                isGen = True
                current_app.logger.info("Creating New service engine cloud " + seGroupName)
                if env == Env.VCF:
                    nsx_cloud_info = configureVcenterInNSXTCloud(ip, csrf2, cloud_url, aviVersion)
                    if nsx_cloud_info[0] is None:
                        current_app.logger.error("Failed to configure vcenter in cloud " + str(nsx_cloud_info[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to configure vcenter in cloud " + str(nsx_cloud_info[1]),
                            "STATUS_CODE": 500,
                        }
                        return jsonify(d), 500
                    cloud_se = createNsxtSECloud(
                        ip, csrf2, cloud_url, seGroupName, nsx_cloud_info[1], aviVersion, "Mgmt"
                    )
                else:
                    cloud_se = createSECloud(
                        ip,
                        csrf2,
                        cloud_url,
                        seGroupName,
                        cluster_status[0],
                        data_store,
                        aviVersion,
                        "Mgmt",
                        license_type=license_type,
                    )
                if cloud_se[0] is None:
                    current_app.logger.error("Failed to create service engine cloud " + str(cloud_se[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to create service engine cloud " + str(cloud_se[1]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                se_cloud_url = cloud_se[0]
            else:
                se_cloud_url = get_se_cloud[0]
            current_app.logger.info(f"SE cloud url is {se_cloud_url}")
            clo = Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE
            if env == Env.VCF:
                clo = Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE.replace("vsphere", "nsxt")
            get_se_cloud_workload = getSECloudStatus(ip, csrf2, aviVersion, clo)
            if get_se_cloud_workload[0] is None:
                current_app.logger.error("Failed to get service engine cloud status " + str(get_se_cloud_workload[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get service engine cloud status " + str(get_se_cloud_workload[1]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500

            isGen = False
            if get_se_cloud_workload[0] == "NOT_FOUND":
                isGen = True
                current_app.logger.info("Creating New service engine cloud " + clo)
                cloud_se_workload = createSECloud_Arch(
                    ip, csrf2, cloud_url, clo, aviVersion, "Workload", license_type=license_type
                )
                if cloud_se_workload[0] is None:
                    current_app.logger.error("Failed to create service engine cloud " + str(cloud_se_workload[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to create service engine cloud " + str(cloud_se_workload[1]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                se_cloud_url_workload = cloud_se_workload[0]
            else:
                se_cloud_url_workload = get_se_cloud_workload[0]
            current_app.logger.error(f"SE workload cloud url {se_cloud_url_workload}")
            if env == Env.VSPHERE:
                mgmt_name = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtNetworkName"]
                dhcp = enableDhcpForManagementNetwork(ip, csrf2, mgmt_name, aviVersion)
                if dhcp[0] is None:
                    current_app.logger.error("Failed to enable dhcp " + str(dhcp[1]))
                    d = {"responseType": "ERROR", "msg": "Failed to enable dhcp " + str(dhcp[1]), "STATUS_CODE": 500}
                    return jsonify(d), 500
            # if env == Env.VCF:
            # shared_service_name = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
            # 'tkgSharedserviceNetworkName']
            # dhcp = enableDhcpForSharedNetwork(ip, csrf2, shared_service_name, aviVersion)
            # if dhcp[0] is None:
            # current_app.logger.error("Failed to enable dhcp " + str(dhcp[1]))
            # d = {
            # "responseType": "ERROR",
            # "msg": "Failed to enable dhcp " + str(dhcp[1]),
            # "STATUS_CODE": 500
            # }
            # return jsonify(d), 500
            cloudName = Cloud.CLOUD_NAME_VSPHERE
            if env == Env.VCF:
                cloudName = Cloud.CLOUD_NAME_VSPHERE.replace("vsphere", "nsxt")
            with open("./newCloudInfo.json", "r") as file2:
                new_cloud_json = json.load(file2)
            uuid = None
            try:
                uuid = new_cloud_json["uuid"]
            except Exception:
                for re in new_cloud_json["results"]:
                    if re["name"] == cloudName:
                        uuid = re["uuid"]
            if uuid is None:
                return None, "NOT_FOUND"
            prefixIpNetmask_vip = seperateNetmaskAndIp(
                request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"][
                    "tkgClusterVipNetworkGatewayCidr"
                ]
            )
            tier1 = ""
            vrf_url = ""
            if env == Env.VSPHERE:
                ipNetMask = seperateNetmaskAndIp(
                    request.get_json(force=True)["tkgComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkGatewayCidr"]
                )
                vrf = getVrfAndNextRoutId(ip, csrf2, uuid, VrfType.MANAGEMENT, ipNetMask[0], aviVersion)
                if vrf[0] is None or vrf[1] == "NOT_FOUND":
                    current_app.logger.error("Vrf not found " + str(vrf[1]))
                    d = {"responseType": "ERROR", "msg": "Vrf not found " + str(vrf[1]), "STATUS_CODE": 500}
                    return jsonify(d), 500
                if vrf[1] != "Already_Configured":
                    ad = addStaticRoute(ip, csrf2, vrf[0], ipNetMask[0], vrf[1], aviVersion)
                    if ad[0] is None:
                        current_app.logger.error("Failed to add static route " + str(ad[1]))
                        d = {"responseType": "ERROR", "msg": "Vrf not found " + str(ad[1]), "STATUS_CODE": 500}
                        return jsonify(d), 500
                """prefixIpNetmask_vip = seperateNetmaskAndIp(
                    request.get_json(force=True)['tkgComponentSpec']["tkgClusterVipNetwork"][
                        "tkgClusterVipNetworkGatewayCidr"])
                list_ = [prefixIpNetmask[0], prefixIpNetmask_vip[0]]
                for l in list_:
                    vrf = getVrfAndNextRoutId(ip, csrf2, uuid, VrfType.GLOBAL, l, aviVersion)
                    if vrf[0] is None or vrf[1] == "NOT_FOUND":
                        current_app.logger.error("Vrf not found " + str(vrf[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Vrf not found " + str(vrf[1]),
                            "STATUS_CODE": 500
                        }
                        return jsonify(d), 500
                    if vrf[1] != "Already_Configured":
                        ad = addStaticRoute(ip, csrf2, vrf[0], l, vrf[1], aviVersion)
                        if ad[0] is None:
                            current_app.logger.error("Failed to add static route " + str(ad[1]))
                            d = {
                                "responseType": "ERROR",
                                "msg": "Vrf not found " + str(ad[1]),
                                "STATUS_CODE": 500
                            }
                            return jsonify(d), 500"""
            else:
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
                vrf_avi_mgmt = getVrfAndNextRoutId(ip, csrf2, uuid, VrfType.GLOBAL, prefixIpNetmask[0], aviVersion)
                if vrf_avi_mgmt[0] is None or vrf_avi_mgmt[1] == "NOT_FOUND":
                    current_app.logger.error("AVI mgmt Vrf not found " + str(vrf_avi_mgmt[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "AVI mgmt Vrf not found " + str(vrf_avi_mgmt[1]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                if vrf_avi_mgmt[1] != "Already_Configured":
                    ad = addStaticRoute(ip, csrf2, vrf_avi_mgmt[0], prefixIpNetmask[0], vrf_avi_mgmt[1], aviVersion)
                    if ad[0] is None:
                        current_app.logger.error("Failed to add static route " + str(ad[1]))
                        d = {"responseType": "ERROR", "msg": "Vrf not found " + str(ad[1]), "STATUS_CODE": 500}
                        return jsonify(d), 500
                teir1name = str(request.get_json(force=True)["envSpec"]["vcenterDetails"]["nsxtTier1RouterDisplayName"])
                vrf_vip = getVrfAndNextRoutId(ip, csrf2, uuid, teir1name, prefixIpNetmask_vip[0], aviVersion)
                if vrf_vip[0] is None or vrf_vip[1] == "NOT_FOUND":
                    current_app.logger.error("Cluster vip Vrf not found " + str(vrf_vip[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Cluster vip Vrf not found " + str(vrf_vip[1]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                if vrf_vip[1] != "Already_Configured":
                    ad = addStaticRoute(ip, csrf2, vrf_vip[0], prefixIpNetmask_vip[0], vrf_vip[1], aviVersion)
                    if ad[0] is None:
                        current_app.logger.error("Failed to add static route " + str(ad[1]))
                        d = {"responseType": "ERROR", "msg": "Vrf not found " + str(ad[1]), "STATUS_CODE": 500}
                        return jsonify(d), 500
                vrf_url = vrf_vip[0]
                getManagementDetails = getNsxTNetworkDetails(
                    ip, csrf2, get_management[0], startIp, endIp, prefixIpNetmask[0], prefixIpNetmask[1], aviVersion
                )
                if getManagementDetails[0] is None:
                    current_app.logger.error(
                        "Failed to get AVI management network details " + str(getManagementDetails[2])
                    )
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get AVI management network details " + str(getManagementDetails[2]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                if getManagementDetails[0] == "AlreadyConfigured":
                    current_app.logger.info("Ip pools are already configured.")
                    # vim_ref = getManagementDetails[2]["vim_ref"]
                    ip_pre = getManagementDetails[2]["subnet_ip"]
                    mask = getManagementDetails[2]["subnet_mask"]
                else:
                    update_resp = updateNetworkWithIpPools(
                        ip, csrf2, get_management[0], "managementNetworkDetails.json", aviVersion
                    )
                    if update_resp[0] != 200:
                        current_app.logger.error("Failed to update management network ip pools " + str(update_resp[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to update management network ip pools " + str(update_resp[1]),
                            "STATUS_CODE": 500,
                        }
                        return jsonify(d), 500
                    # vim_ref = update_resp[2]["vimref"]
                    mask = update_resp[2]["subnet_mask"]
                    ip_pre = update_resp[2]["subnet_ip"]
                ipam_name = Cloud.IPAM_NAME_VSPHERE.replace("vsphere", "nsxt")
                get_ipam = getIpam(ip, csrf2, ipam_name, aviVersion)
                if get_ipam[0] is None:
                    current_app.logger.error("Failed to get service engine Ipam " + str(get_ipam[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get service engine Ipam " + str(get_ipam[1]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500

                isGen = False
                if get_ipam[0] == "NOT_FOUND":
                    current_app.logger.info("Creating IPam " + ipam_name)
                    ipam = createIpam_nsxtCloud(ip, csrf2, get_management[0], get_vip[0], ipam_name, aviVersion)
                    if ipam[0] is None:
                        current_app.logger.error("Failed to create Ipam " + str(ipam[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to create Ipam " + str(ipam[1]),
                            "STATUS_CODE": 500,
                        }
                        return jsonify(d), 500
                    ipam_url = ipam[0]
                else:
                    ipam_url = get_ipam[0]
                dns_profile_name = "tkg-nsxt-dns"
                search_domain = request.get_json(force=True)["envSpec"]["infraComponents"]["searchDomains"]
                get_dns = getIpam(ip, csrf2, dns_profile_name, aviVersion)
                if get_dns[0] is None:
                    current_app.logger.error("Failed to get service engine Ipam " + str(get_dns[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get service engine ipam " + str(get_dns[1]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                if get_dns[0] == "NOT_FOUND":
                    dns = createDns_nsxtCloud(ip, csrf2, search_domain, dns_profile_name, aviVersion)
                    if dns[0] is None:
                        current_app.logger.error("Failed to create Nsxt dns " + str(dns[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to create Nsxt dns " + str(dns[1]),
                            "STATUS_CODE": 500,
                        }
                        return jsonify(d), 500
                    dnsurl = dns[0]
                else:
                    current_app.logger.info("Dns already created")
                    dnsurl = get_dns[0]
                ipam_asso = associate_ipam_nsxtCloud(ip, csrf2, aviVersion, uuid, ipam_url, dnsurl)
                if ipam_asso[0] is None:
                    current_app.logger.error("Failed to associate Ipam and dns to cloud " + str(ipam_asso[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to associate Ipam and dns to cloud " + str(ipam_asso[1]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
            default = waitForCloudPlacementReady(ip, csrf2, cloudName, aviVersion)
            if default[0] is None:
                current_app.logger.error("Failed to get " + cloudName + " cloud status")
                d = {"responseType": "ERROR", "msg": "Failed to get " + cloudName + " cloud status", "STATUS_CODE": 500}
                return jsonify(d), 500
            virtual_service, error = create_virtual_service(
                ip, csrf2, uuid, seGroupName, get_vip[0], 2, tier1, vrf_url, aviVersion
            )
            if virtual_service is None:
                current_app.logger.error("Failed to create virtual service " + str(error))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create virtual service " + str(error),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            current_app.logger.debug(f"Gen {isGen}")
    current_app.logger.info("Configured management cluster cloud successfully")
    d = {"responseType": "SUCCESS", "msg": "Configured management cluster cloud successfully", "STATUS_CODE": 200}
    return jsonify(d), 200


@vsphere_management_config.route("/api/tanzu/vsphere/enablewcp", methods=["POST"])
def enable_wcp():
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
    if not isEnvTkgs_wcp(env):
        current_app.logger.error("Wrong env provided, wcp can be only enabled on TKGS")
        d = {"responseType": "ERROR", "msg": "Wrong env provided, wcp can be only enabled on TKGS", "STATUS_CODE": 500}
        return jsonify(d), 500
    # aviVersion = get_avi_version(env)
    password = current_app.config["VC_PASSWORD"]
    vcenter_username = current_app.config["VC_USER"]
    vcenter_ip = current_app.config["VC_IP"]

    subs_lib_name = request.get_json(force=True)["tkgsComponentSpec"]["tkgsMgmtNetworkSpec"][
        "subscribedContentLibraryName"
    ]
    if not subs_lib_name:
        cLib = createSubscribedLibrary(vcenter_ip, vcenter_username, password, env)
        if cLib[0] is None:
            current_app.logger.error("Failed to create content library " + str(cLib[1]))
            d = {"responseType": "ERROR", "msg": "Failed to create content library " + str(cLib[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
    avi_fqdn = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviController01Fqdn"]
    if not avi_fqdn:
        controller_name = ControllerLocation.CONTROLLER_NAME_VSPHERE
    else:
        controller_name = avi_fqdn
    current_app.logger.info(f"controller name {controller_name}")
    if isAviHaEnabled(env):
        ip = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviClusterFqdn"]
    else:
        ip = avi_fqdn
    if ip is None:
        current_app.logger.error("Failed to get IP of AVI controller")
        d = {"responseType": "ERROR", "msg": "Failed to get IP of AVI controller", "STATUS_CODE": 500}
        return jsonify(d), 500
    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        current_app.logger.error("Failed to get csrf from new set password")
        d = {"responseType": "ERROR", "msg": "Failed to get csrf from new set password", "STATUS_CODE": 500}
        return jsonify(d), 500

    avi_ip = checkforIpAddress(getSi(vcenter_ip, vcenter_username, password), avi_fqdn)
    if avi_ip is None:
        current_app.logger.error("Failed to get IP of AVI controller")
        d = {"responseType": "ERROR", "msg": "Failed to get IP of AVI controller", "STATUS_CODE": 500}
        return jsonify(d), 500
    deployed_avi_version = obtain_avi_version(avi_ip, env)
    if deployed_avi_version[0] is None:
        current_app.logger.error("Failed to login and obtain AVI version" + str(deployed_avi_version[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to login and obtain AVI version " + deployed_avi_version[1],
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    aviVersion = deployed_avi_version[0]

    enable = enableWCP(ip, csrf2, aviVersion)
    if enable[0] is None:
        current_app.logger.error("Failed to enable WCP " + str(enable[1]))
        d = {"responseType": "ERROR", "msg": "Failed to configure WCP " + str(enable[1]), "STATUS_CODE": 500}
        return jsonify(d), 500
    isUp = checkAndWaitForAllTheServiceEngineIsUp(ip, Cloud.DEFAULT_CLOUD_NAME_VSPHERE, env, aviVersion)
    if isUp[0] is None:
        current_app.logger.error("All service engines are not up, check your network configuration " + str(isUp[1]))
        d = {
            "responseType": "ERROR",
            "msg": "All service engines are not up, check your network configuration " + str(isUp[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    current_app.logger.info("Setting up kubectl Vsphere plugin...")
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

    header = {"Accept": "application/json", "Content-Type": "application/json", "vmware-api-session-id": session_id}
    cluster_name = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterCluster"]
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

    status = False
    count = 0
    while count < 15 and not status:
        configure_kubectl = configureKubectl(cluster_endpoint)
        if configure_kubectl[1] != 200:
            current_app.logger.info("Getting connection timeout error. Waited " + str(count * 60) + "s")
            current_app.logger.info("Waiting for 1 min status == ready")
            count = count + 1
            time.sleep(60)
        else:
            status = True

    if count >= 15 and not status:
        current_app.logger.error(configure_kubectl[0])
        d = {"responseType": "ERROR", "msg": configure_kubectl[0], "STATUS_CODE": 500}
        return jsonify(d), 500

    current_app.logger.info("Configured Wcp successfully")
    configTkgs, message = configureTkgConfiguration(vcenter_username, password, cluster_endpoint)
    if configTkgs is None:
        d = {
            "responseType": "ERROR",
            "msg": "Failed to configure TKGS service configuration " + str(message),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500

    if checkTmcEnabled(env):
        tmc_register_response = registerTMCTKGs(vcenter_ip, vcenter_username, password)
        if tmc_register_response[1] != 200:
            current_app.logger.error("Supervisor cluster TMC registration failed " + str(tmc_register_response[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Supervisor cluster TMC registration failed " + str(tmc_register_response[0]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        else:
            current_app.logger.info("TMC registration successful")
    else:
        current_app.logger.info("Skipping TMC registration, as tmcAvailability is set to False")
    d = {"responseType": "SUCCESS", "msg": "Configured WCP successfully", "STATUS_CODE": 200}
    return jsonify(d), 200


def updateIpam(ip, csrf2, newCloudUrl, aviVersion):
    with open("./detailsOfNewCloudIpam.json", "r") as file2:
        new_cloud_json = json.load(file2)
    json_object = json.dumps(new_cloud_json, indent=4)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    response_csrf = requests.request("PUT", newCloudUrl, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        return response_csrf.json(), "SUCCESS"


def enableDhcpForManagementNetwork(ip, csrf2, name, aviVersion):
    getNetwork = getNetworkUrl(ip, csrf2, name, aviVersion)
    if getNetwork[0] is None:
        current_app.logger.error("Failed to get network url " + name)
        d = {"responseType": "ERROR", "msg": "Failed to get network url " + name, "STATUS_CODE": 500}
        return jsonify(d), 500
    details = getNetworkDetailsDhcp(ip, csrf2, getNetwork[0], aviVersion)
    if details[0] is None:
        current_app.logger.error("Failed to get network details " + details[1])
        d = {"responseType": "ERROR", "msg": "Failed to get network details " + details[1], "STATUS_CODE": 500}
        return jsonify(d), 500
    with open("./managementNetworkDetailsDhcp.json", "r") as openfile:
        json_object = json.load(openfile)
    json_object_m = json.dumps(json_object, indent=4)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    response_csrf = requests.request("PUT", getNetwork[0], headers=headers, data=json_object_m, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    return "SUCCESS", 200


def enableDhcpForSharedNetwork(ip, csrf2, name, aviVersion):
    getNetwork = getNetworkUrl(ip, csrf2, name, aviVersion)
    if getNetwork[0] is None:
        current_app.logger.error("Failed to get network url " + name)
        d = {"responseType": "ERROR", "msg": "Failed to get network url " + name, "STATUS_CODE": 500}
        return jsonify(d), 500
    details = getNetworkDetailsSharedDhcp(ip, csrf2, getNetwork[0], aviVersion)
    if details[0] is None:
        current_app.logger.error("Failed to get network details " + details[1])
        d = {"responseType": "ERROR", "msg": "Failed to get network details " + details[1], "STATUS_CODE": 500}
        return jsonify(d), 500
    with open("./sharedNetworkDetailsDhcp.json", "r") as openfile:
        json_object = json.load(openfile)
    json_object_m = json.dumps(json_object, indent=4)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    response_csrf = requests.request("PUT", getNetwork[0], headers=headers, data=json_object_m, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    return "SUCCESS", 200


def getClusterUrl(ip, csrf2, cluster_name, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    url = "https://" + ip + "/api/vimgrclusterruntime"
    payload = {}
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        if str(cluster_name).__contains__("/"):
            cluster_name = cluster_name[cluster_name.rindex("/") + 1 :]
        for cluster in response_csrf.json()["results"]:
            if cluster["name"] == cluster_name:
                return cluster["url"], "SUCCESS"

        return "NOT_FOUND", "FAILED"


@vsphere_management_config.route("/api/tanzu/vsphere/tkgmgmt/config", methods=["POST"])
def configTkgMgmt():
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
    parent_resourcepool = current_app.config["RESOURCE_POOL"]
    try:
        isCreated5 = createResourcePool(
            vcenter_ip,
            vcenter_username,
            password,
            cluster_name,
            ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE,
            parent_resourcepool,
            data_center,
        )
        if isCreated5 is not None:
            current_app.logger.info("Created resource pool " + ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE)
    except Exception as e:
        current_app.logger.error("Failed to create resource pool " + str(e))
        d = {"responseType": "ERROR", "msg": "Failed to create resource pool " + str(e), "STATUS_CODE": 500}
        return jsonify(d), 500
    try:
        isCreated3 = create_folder(
            vcenter_ip,
            vcenter_username,
            password,
            data_center,
            ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder_VSPHERE,
        )
        if isCreated3 is not None:
            current_app.logger.info("Created folder " + ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder_VSPHERE)

    except Exception as e:
        current_app.logger.error("Failed to create folder " + str(e))
        d = {"responseType": "ERROR", "msg": "Failed to create folder " + str(e), "STATUS_CODE": 500}
        return jsonify(d), 500
    avi_fqdn = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController01Fqdn"]
    if isAviHaEnabled(env):
        ip = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviClusterFqdn"]
    else:
        ip = avi_fqdn
    if ip is None:
        current_app.logger.error("Failed to get IP of AVI controller")
        d = {"responseType": "ERROR", "msg": "Failed to get IP of AVI controller", "STATUS_CODE": 500}
        return jsonify(d), 500
    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        current_app.logger.error("Failed to get csrf from new password")
        d = {"responseType": "ERROR", "msg": "Failed to get csrf from new password", "STATUS_CODE": 500}
        return jsonify(d), 500
    if env == Env.VSPHERE:
        data_network = request.get_json(force=True)["tkgMgmtDataNetwork"]["tkgMgmtDataNetworkName"]
    else:
        data_network = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"][
            "tkgClusterVipNetworkName"
        ]
    get_wip = getVipNetworkIpNetMask(ip, csrf2, data_network, aviVersion)
    if get_wip[0] is None or get_wip[0] == "NOT_FOUND":
        current_app.logger.error("Failed to get se VIP network IP and netmask " + str(get_wip[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get VIP network IP and netmask " + str(get_wip[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    management_cluster = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtClusterName"]
    avi_ip = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController01Ip"]
    avi_fqdn = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController01Fqdn"]
    if not avi_ip:
        controller_fqdn = ip
    elif not avi_fqdn:
        controller_fqdn = avi_fqdn
    else:
        controller_fqdn = ip
    if not createClusterFolder(management_cluster):
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create directory: " + Paths.CLUSTER_PATH + management_cluster,
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    current_app.logger.info(
        "The config files for management cluster will be located at: " + Paths.CLUSTER_PATH + management_cluster
    )
    current_app.logger.info("Deploying Management Cluster " + management_cluster)
    deploy_status = deployManagementCluster(
        management_cluster,
        controller_fqdn,
        data_center,
        data_store,
        cluster_name,
        data_network,
        get_wip[0],
        vcenter_ip,
        vcenter_username,
        aviVersion,
        password,
        env,
        vsSpec,
    )
    if deploy_status[0] is None:
        current_app.logger.error("Failed to deploy management cluster " + deploy_status[1])
        d = {
            "responseType": "ERROR",
            "msg": "Failed to deploy management cluster " + deploy_status[1],
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    command = ["tanzu", "plugin", "sync"]
    runShellCommandAndReturnOutputAsList(command)
    if checkEnableIdentityManagement(env):
        podRunninng = ["tanzu", "cluster", "list", "--include-management-cluster", "-A"]
        command_status = runShellCommandAndReturnOutputAsList(podRunninng)
        if not verifyPodsAreRunning(management_cluster, command_status[0], RegexPattern.running):
            current_app.logger.error(management_cluster + " is not deployed")
            d = {"responseType": "ERROR", "msg": management_cluster + " is not deployed", "STATUS_CODE": 500}
            return jsonify(d), 500
        switch = switchToManagementContext(management_cluster)
        if switch[1] != 200:
            current_app.logger.info(switch[0].json["msg"])
            d = {"responseType": "ERROR", "msg": switch[0].json["msg"], "STATUS_CODE": 500}
            return jsonify(d), 500
        if checkEnableIdentityManagement(env):
            current_app.logger.info("Validating pinniped installation status")
            check_pinniped = checkPinnipedInstalled()
            if check_pinniped[1] != 200:
                current_app.logger.error(check_pinniped[0].json["msg"])
                d = {"responseType": "ERROR", "msg": check_pinniped[0].json["msg"], "STATUS_CODE": 500}
                return jsonify(d), 500
            current_app.logger.info("Validating pinniped service status")
            check_pinniped_svc = checkPinnipedServiceStatus()
            if check_pinniped_svc[1] != 200:
                current_app.logger.error(check_pinniped_svc[0])
                d = {"responseType": "ERROR", "msg": check_pinniped_svc[0], "STATUS_CODE": 500}
                return jsonify(d), 500
            current_app.logger.info("Successfully validated Pinniped service status")
            identity_mgmt_type = str(
                request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["identityManagementType"]
            )
            if identity_mgmt_type.lower() == "ldap":
                check_pinniped_dexsvc = checkPinnipedDexServiceStatus()
                if check_pinniped_dexsvc[1] != 200:
                    current_app.logger.error(check_pinniped_dexsvc[0])
                    d = {"responseType": "ERROR", "msg": check_pinniped_dexsvc[0], "STATUS_CODE": 500}
                    return jsonify(d), 500
                current_app.logger.info("External IP for Pinniped is set as: " + check_pinniped_svc[0])

            cluster_admin_users = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"][
                "tkgMgmtRbacUserRoleSpec"
            ]["clusterAdminUsers"]
            admin_users = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"][
                "tkgMgmtRbacUserRoleSpec"
            ]["adminUsers"]
            edit_users = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"][
                "tkgMgmtRbacUserRoleSpec"
            ]["editUsers"]
            view_users = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"][
                "tkgMgmtRbacUserRoleSpec"
            ]["viewUsers"]
            rbac_user_status = createRbacUsers(
                management_cluster,
                isMgmt=True,
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

    tmc_required = str(request.get_json(force=True)["envSpec"]["saasEndpoints"]["tmcDetails"]["tmcAvailability"])
    if tmc_required.lower() == "true":
        current_app.logger.info("TMC registration is enabled")
    elif tmc_required.lower() == "false":
        current_app.logger.info("TMC registration is deactivated")
    else:
        current_app.logger.error("Wrong TMC selection attribute provided " + tmc_required)
        d = {
            "responseType": "ERROR",
            "msg": "Wrong TMC selection attribute provided " + tmc_required,
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    if not checkAirGappedIsEnabled(env):
        if checkTmcEnabled(env):
            if Tkg_version.TKG_VERSION == "2.1":
                current_app.logger.info("TMC registration on management cluster is supported on tanzu 1.5")
                clusterGroup = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"][
                    "tkgMgmtClusterGroupName"
                ]
                if not clusterGroup:
                    clusterGroup = "default"
                if checkMgmtProxyEnabled(env):
                    state = registerWithTmc(management_cluster, env, "true", "management", clusterGroup)
                else:
                    state = registerWithTmc(management_cluster, env, "false", "management", clusterGroup)
                if state[0] is None:
                    current_app.logger.error("Failed to register on TMC " + state[1])
                    d = {"responseType": "ERROR", "msg": "Failed to register on TMC " + state[1], "STATUS_CODE": 500}
                    return jsonify(d), 500
    if checkAirGappedIsEnabled(env):
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
        air_gapped_repo = str(
            request.get_json(force=True)["envSpec"]["customRepositorySpec"]["tkgCustomImageRepository"]
        )
        air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
        bom = loadBomFile()
        if bom is None:
            current_app.logger.error("Failed to load bom")
            d = {"responseType": "ERROR", "msg": "Failed to load BOM", "STATUS_CODE": 500}
            return jsonify(d), 500
        # code commented as kube_rbac_proxy tag has been removed from TKG 2.1.0 bom
        # try:
        #     tag = bom['components']['kube_rbac_proxy'][0]['images']['kubeRbacProxyControllerImage']['tag']
        # except Exception as e:
        #     current_app.logger.error("Failed to load bom key " + str(e))
        #     d = {
        #         "responseType": "ERROR",
        #         "msg": "Failed to load BOM key " + str(e),
        #         "STATUS_CODE": 500
        #     }
        #     return jsonify(d), 500
        # kube = air_gapped_repo + "/kube-rbac-proxy:" + tag
        # spec = "{\"spec\": {\"template\": {\"spec\": {\"containers\": [{\"name\": \"kube-rbac-proxy\",\"image\": \""
        # + kube + "\"}]}}}}"
        # command = ["kubectl", "patch", "deployment", "ako-operator-controller-manager", "-n", "tkg-system-networking",
        #            "--patch", spec]
        # status = runShellCommandAndReturnOutputAsList(command)
        # if status[1] != 0:
        #     current_app.logger.error("Failed to patch ako operator " + str(status[0]))
        #     d = {
        #         "responseType": "ERROR",
        #         "msg": "Failed to patch ako operator " + str(status[0]),
        #         "STATUS_CODE": 500
        #     }
        #     return jsonify(d), 500
    d = {"responseType": "SUCCESS", "msg": "Successfully configured management cluster ", "STATUS_CODE": 200}
    return jsonify(d), 200


def referenceTkgMNetwork(ip, csrf2, url, aviVersion):
    reference_TKG_Mgmt_Network_ipNetmask = seperateNetmaskAndIp(
        request.get_json(force=True)["tkgComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkGatewayCidr"]
    )
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    body = {
        "vcenter_dvs": True,
        "dhcp_enabled": False,
        "exclude_discovered_subnets": False,
        "synced_from_se": False,
        "ip6_autocfg_enabled": False,
        "cloud_ref": url,
        "configured_subnets": [
            {
                "prefix": {
                    "ip_addr": {"addr": reference_TKG_Mgmt_Network_ipNetmask[0], "type": "V4"},
                    "mask": reference_TKG_Mgmt_Network_ipNetmask[1],
                }
            }
        ],
        "name": Cloud.mgmtVipNetwork,
    }
    json_object = json.dumps(body, indent=4)
    url = "https://" + ip + "/api/network"
    response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        return 200, "SUCCESS"


def waitForCloudPlacementReady(ip, csrf2, name, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    url = "https://" + ip + "/api/cloud"
    body = {}
    response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    uuid = None
    for se in response_csrf.json()["results"]:
        if se["name"] == name:
            uuid = se["uuid"]
            break
    if uuid is None:
        return None, "Failed", "Error"
    status_url = "https://" + ip + "/api/cloud/" + uuid + "/status"
    count = 0
    response_csrf = None
    while count < 60:
        response_csrf = requests.request("GET", status_url, headers=headers, data=body, verify=False)
        if response_csrf.status_code != 200:
            return None, "Failed", "Error"
        try:
            current_app.logger.info(name + " cloud state " + response_csrf.json()["state"])
            if response_csrf.json()["state"] == "CLOUD_STATE_PLACEMENT_READY":
                break
        except Exception:
            pass
        count = count + 1
        time.sleep(10)
        current_app.logger.info("Waited for " + str(count * 10) + "s retrying")
    if response_csrf is None:
        current_app.logger.info("Waited for " + str(count * 10) + "s default cloud status")
        return None, "Failed", "ERROR"

    return "SUCCESS", "READY", response_csrf.json()["state"]


def createNewCloud(ip, csrf2, aviVersion, license_type="enterprise"):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    datacenter = current_app.config["VC_DATACENTER"]
    if str(datacenter).__contains__("/"):
        dc = datacenter[datacenter.rindex("/") + 1 :]
    else:
        dc = datacenter
    library, status_lib = fetchContentLibrary(ip, headers, "")
    if library is None:
        return None, status_lib
    true_content_lib_body = {
        "vcenter_configuration": {
            "privilege": "WRITE_ACCESS",
            "deactivate_vm_discovery": False,
            "use_content_lib": True,
            "content_lib": {"id": status_lib},
            "vcenter_url": current_app.config["VC_IP"],
            "username": current_app.config["VC_USER"],
            "password": current_app.config["VC_PASSWORD"],
            "datacenter": dc,
        }
    }
    false_content_lib_body = {
        "vcenter_configuration": {
            "privilege": "WRITE_ACCESS",
            "deactivate_vm_discovery": False,
            "vcenter_url": current_app.config["VC_IP"],
            "username": current_app.config["VC_USER"],
            "password": current_app.config["VC_PASSWORD"],
            "datacenter": dc,
            "use_content_lib": False,
        }
    }
    content_lib_body = false_content_lib_body if license_type == "essentials" else true_content_lib_body
    body = {
        "name": Cloud.CLOUD_NAME_VSPHERE,
        "vtype": "CLOUD_VCENTER",
        "vcenter_configuration": {
            "privilege": "WRITE_ACCESS",
            "deactivate_vm_discovery": False,
            "vcenter_url": current_app.config["VC_IP"],
            "username": current_app.config["VC_USER"],
            "password": current_app.config["VC_PASSWORD"],
            "datacenter": dc,
        },
        "dhcp_enabled": False,
        "mtu": 1500,
        "prefer_static_routes": False,
        "enable_vip_static_routes": False,
        "state_based_dns_registration": True,
        "ip6_autocfg_enabled": False,
        "dns_resolution_on_se": False,
        "enable_vip_on_all_interfaces": False,
        "autoscale_polling_interval": 60,
        "vmc_deployment": False,
        "license_type": "LIC_CORES",
    }
    body.update(content_lib_body)
    json_object = json.dumps(body, indent=4)
    url = "https://" + ip + "/api/cloud"
    response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        os.system("rm -rf newCloudInfo.json")
        with open("./newCloudInfo.json", "w") as outfile:
            json.dump(response_csrf.json(), outfile)
        return response_csrf.json()["url"], "SUCCESS"


def getNetworkUrl(ip, csrf2, name, aviVersion):
    with open("./newCloudInfo.json", "r") as file2:
        new_cloud_json = json.load(file2)
    uuid = None
    try:
        uuid = new_cloud_json["uuid"]
    except Exception:
        env = envCheck()
        env = env[0]
        cloud_name = Cloud.CLOUD_NAME_VSPHERE
        if env == Env.VCF:
            cloud_name = Cloud.CLOUD_NAME_VSPHERE.replace("vsphere", "nsxt")
        for re in new_cloud_json["results"]:
            if re["name"] == cloud_name:
                uuid = re["uuid"]
    if uuid is None:
        return None, "Failed", "ERROR"
    url = "https://" + ip + "/api/network-inventory/?cloud_ref.uuid=" + uuid
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    payload = {}
    count = 0
    response_csrf = None
    try:
        while count < 60:
            response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
            if response_csrf.status_code == 200:
                if response_csrf.json()["count"] > 1:
                    break
            count = count + 1
            time.sleep(10)
            current_app.logger.info("Waited for " + str(count * 10) + "s retrying")
        if response_csrf is None:
            current_app.logger.info("Waited for " + str(count * 10) + "s but service engine is not up")
            return None, "Failed", "ERROR"
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        elif count >= 59:
            return None, "NOT_FOUND", "TIME_OUT"
        else:
            for se in response_csrf.json()["results"]:
                if se["config"]["name"] == name:
                    return se["config"]["url"], se["config"]["uuid"], "FOUND", "SUCCESS"
            else:
                next_url = None if not response_csrf.json()["next"] else response_csrf.json()["next"]
                while len(next_url) > 0:
                    response_csrf = requests.request("GET", next_url, headers=headers, data=payload, verify=False)
                    for se in response_csrf.json()["results"]:
                        if se["config"]["name"] == name:
                            return se["config"]["url"], se["config"]["uuid"], "FOUND", "SUCCESS"
                    next_url = None if not response_csrf.json()["next"] else response_csrf.json()["next"]
        return None, "NOT_FOUND", "Failed"
    except KeyError:
        return None, "NOT_FOUND", "Failed"


def getNetworkDetailsDhcp(ip, csrf2, managementNetworkUrl, aviVersion):
    url = managementNetworkUrl
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    payload = {}
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
    if response_csrf.status_code != 200:
        return None, "Failed"
    os.system("rm -rf managementNetworkDetailsDhcp.json")
    with open("./managementNetworkDetailsDhcp.json", "w") as outfile:
        json.dump(response_csrf.json(), outfile)
    replaceValueSysConfig("managementNetworkDetailsDhcp.json", "dhcp_enabled", "name", "true")
    return "SUCCESS", 200


def getNetworkDetailsSharedDhcp(ip, csrf2, managementNetworkUrl, aviVersion):
    url = managementNetworkUrl
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    payload = {}
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
    if response_csrf.status_code != 200:
        return None, "Failed"
    os.system("rm -rf sharedNetworkDetailsDhcp.json")
    with open("./sharedNetworkDetailsDhcp.json", "w") as outfile:
        json.dump(response_csrf.json(), outfile)
    replaceValueSysConfig("sharedNetworkDetailsDhcp.json", "dhcp_enabled", "name", "true")
    return "SUCCESS", 200


def getNetworkDetails(ip, csrf2, managementNetworkUrl, startIp, endIp, prefixIp, netmask, aviVersion, env="vsphere"):
    url = managementNetworkUrl
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    payload = {}
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
    details = {}
    if response_csrf.status_code != 200:
        details["error"] = response_csrf.text
        return None, "Failed", details
    try:
        add = response_csrf.json()["configured_subnets"][0]["prefix"]["ip_addr"]["addr"]
        details["subnet_ip"] = add
        details["vim_ref"] = response_csrf.json()["vimgrnw_ref"]
        details["subnet_mask"] = response_csrf.json()["configured_subnets"][0]["prefix"]["mask"]
        return "AlreadyConfigured", 200, details
    except Exception:
        current_app.logger.info("Ip pools are not configured, configuring it")

    os.system("rm -rf managementNetworkDetails.json")
    with open("./managementNetworkDetails.json", "w") as outfile:
        json.dump(response_csrf.json(), outfile)

    if env == Env.VSPHERE:
        generateVsphereConfiguredSubnets("managementNetworkDetails.json", startIp, endIp, prefixIp, int(netmask))
    else:
        generateVsphereConfiguredSubnetsForSeandVIP(
            "managementNetworkDetails.json", startIp, endIp, prefixIp, int(netmask)
        )

    return "SUCCESS", 200, details


def getNsxTNetworkDetails(ip, csrf2, managementNetworkUrl, startIp, endIp, prefixIp, netmask, aviVersion):
    url = managementNetworkUrl
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    payload = {}
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
    details = {}
    if response_csrf.status_code != 200:
        details["error"] = response_csrf.text
        return None, "Failed", details
    os.system("rm -rf managementNetworkDetails.json")
    with open("./managementNetworkDetails.json", "w") as outfile:
        json.dump(response_csrf.json(), outfile)
    with open("./managementNetworkDetails.json") as f:
        data = json.load(f)
    dic = dict(dhcp_enabled=False)
    data.update(dic)
    with open("./managementNetworkDetails.json", "w") as f:
        json.dump(data, f)
    generateVsphereConfiguredSubnetsForSe("managementNetworkDetails.json", startIp, endIp, prefixIp, int(netmask))
    try:
        add = response_csrf.json()["configured_subnets"][0]["prefix"]["ip_addr"]["addr"]
        details["subnet_ip"] = add
        # vim_ref has been removed for NSX-T cloud
        details["subnet_mask"] = response_csrf.json()["configured_subnets"][0]["prefix"]["mask"]
        return "AlreadyConfigured", 200, details
    except Exception:
        current_app.logger.info("Ip pools are not configured, configuring it")
    return "SUCCESS", 200, details


def getNetworkDetailsVip(ip, csrf2, vipNetworkUrl, startIp, endIp, prefixIp, netmask, aviVersion, env="vsphere"):
    url = vipNetworkUrl
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    payload = {}
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
    details = {}
    if response_csrf.status_code != 200:
        details["error"] = response_csrf.text
        return None, "Failed", details
    try:
        add = response_csrf.json()["configured_subnets"][0]["prefix"]["ip_addr"]["addr"]
        details["subnet_ip"] = add
        details["subnet_mask"] = response_csrf.json()["configured_subnets"][0]["prefix"]["mask"]
        details["vim_ref"] = response_csrf.json()["vimgrnw_ref"]
        return "AlreadyConfigured", 200, details
    except Exception:
        current_app.logger.info("Ip pools are not configured, configuring it")

    os.system("rm -rf vipNetworkDetails.json")
    with open("./vipNetworkDetails.json", "w") as outfile:
        json.dump(response_csrf.json(), outfile)
    if env == Env.VSPHERE:
        generateVsphereConfiguredSubnets("vipNetworkDetails.json", startIp, endIp, prefixIp, int(netmask))
    else:
        generateVsphereConfiguredSubnetsForSeandVIP("vipNetworkDetails.json", startIp, endIp, prefixIp, int(netmask))
    return "SUCCESS", 200, details


def getNSXTNetworkDetailsVip(ip, csrf2, vipNetworkUrl, startIp, endIp, prefixIp, netmask, aviVersion):
    url = vipNetworkUrl
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    payload = {}
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
    details = {}
    if response_csrf.status_code != 200:
        details["error"] = response_csrf.text
        return None, "Failed", details
    try:
        add = response_csrf.json()["configured_subnets"][0]["prefix"]["ip_addr"]["addr"]
        details["subnet_ip"] = add
        # vim_ref has been removed for NSX-T cloud
        details["subnet_mask"] = response_csrf.json()["configured_subnets"][0]["prefix"]["mask"]
        return "AlreadyConfigured", 200, details
    except Exception:
        current_app.logger.info("Ip pools are not configured configuring it")
    # update attributes
    os.system("rm -rf vipNetworkDetails.json")
    with open("./vipNetworkDetails.json", "w") as outfile:
        json.dump(response_csrf.json(), outfile)
    with open("./vipNetworkDetails.json") as f:
        data = json.load(f)
    dic = dict(dhcp_enabled=False)
    data.update(dic)
    with open("./vipNetworkDetails.json", "w") as f:
        json.dump(data, f)
    generateVsphereConfiguredSubnetsForSeandVIP("vipNetworkDetails.json", startIp, endIp, prefixIp, int(netmask))
    return "SUCCESS", 200, details


def updateNetworkWithIpPools(ip, csrf2, managementNetworkUrl, fileName, aviVersion):
    with open(fileName, "r") as openfile:
        json_object = json.load(openfile)
    json_object_m = json.dumps(json_object, indent=4)
    env = envCheck()
    env = env[0]
    url = managementNetworkUrl
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    details = {}
    response_csrf = requests.request("PUT", url, headers=headers, data=json_object_m, verify=False)
    if response_csrf.status_code != 200:
        count = 0
        if response_csrf.text.__contains__(
            "Cannot edit network properties till network sync from Service Engines is complete"
        ):
            while count < 10:
                time.sleep(60)
                response_csrf = requests.request("PUT", url, headers=headers, data=json_object_m, verify=False)
                if response_csrf.status_code == 200:
                    break
                current_app.logger.info("waited for " + str(count * 60) + "s sync to complete")
                count = count + 1
        else:
            return 500, response_csrf.text, details
    details["subnet_ip"] = response_csrf.json()["configured_subnets"][0]["prefix"]["ip_addr"]["addr"]
    details["subnet_mask"] = response_csrf.json()["configured_subnets"][0]["prefix"]["mask"]
    if env == Env.VSPHERE:
        details["vimref"] = response_csrf.json()["vimgrnw_ref"]
    return 200, "SUCCESS", details


def getSeNewBody(newCloudUrl, seGroupName, clusterUrl, dataStore, se_name_prefix, license_type):
    if str(dataStore).__contains__("/"):
        dataStore = dataStore[dataStore.rindex("/") + 1 :]

    enterprise_body = {
        "ha_mode": "HA_MODE_SHARED_PAIR",
        "hm_on_standby": True,
        "dedicated_dispatcher_core": False,
        "disable_gro": True,
        "self_se_election": True,
        "objsync_config": {"objsync_cpu_limit": 30, "objsync_reconcile_interval": 10, "objsync_hub_elect_interval": 60},
        "app_cache_percent": 10,
        "license_tier": "ENTERPRISE",
    }
    essentials_body = {
        "ha_mode": "HA_MODE_LEGACY_ACTIVE_STANDBY",
        "hm_on_standby": False,
        "self_se_election": False,
        "app_cache_percent": 0,
        "license_tier": "ESSENTIALS",
    }

    body = {
        "max_vs_per_se": 10,
        "min_scaleout_per_vs": 2,
        "max_scaleout_per_vs": 4,
        "max_se": 10,
        "vcpus_per_se": 2,
        "memory_per_se": 4096,
        "disk_per_se": 15,
        "max_cpu_usage": 80,
        "min_cpu_usage": 30,
        "se_deprovision_delay": 120,
        "auto_rebalance": False,
        "se_name_prefix": se_name_prefix,
        "vs_host_redundancy": True,
        "vcenter_folder": "AviSeFolder",
        "vcenter_datastores_include": True,
        "vcenter_datastore_mode": "VCENTER_DATASTORE_SHARED",
        "cpu_reserve": False,
        "mem_reserve": True,
        "algo": "PLACEMENT_ALGO_PACKED",
        "buffer_se": 0,
        "active_standby": False,
        "placement_mode": "PLACEMENT_MODE_AUTO",
        "se_dos_profile": {"thresh_period": 5},
        "auto_rebalance_interval": 300,
        "aggressive_failure_detection": False,
        "realtime_se_metrics": {"enabled": False, "duration": 30},
        "vs_scaleout_timeout": 600,
        "vs_scalein_timeout": 30,
        "connection_memory_percentage": 50,
        "extra_config_multiplier": 0,
        "vs_scalein_timeout_for_upgrade": 30,
        "log_disksz": 10000,
        "os_reserved_memory": 0,
        "per_app": False,
        "distribute_load_active_standby": False,
        "auto_redistribute_active_standby_load": False,
        "cpu_socket_affinity": False,
        "num_flow_cores_sum_changes_to_ignore": 8,
        "least_load_core_selection": True,
        "extra_shared_config_memory": 0,
        "se_tunnel_mode": 0,
        "se_vs_hb_max_vs_in_pkt": 256,
        "se_vs_hb_max_pkts_in_batch": 64,
        "se_thread_multiplier": 1,
        "async_ssl": False,
        "async_ssl_threads": 1,
        "se_udp_encap_ipc": 0,
        "se_tunnel_udp_port": 1550,
        "archive_shm_limit": 8,
        "significant_log_throttle": 100,
        "udf_log_throttle": 100,
        "non_significant_log_throttle": 100,
        "ingress_access_mgmt": "SG_INGRESS_ACCESS_ALL",
        "ingress_access_data": "SG_INGRESS_ACCESS_ALL",
        "se_sb_dedicated_core": False,
        "se_probe_port": 7,
        "se_sb_threads": 1,
        "ignore_rtt_threshold": 5000,
        "waf_mempool": True,
        "waf_mempool_size": 64,
        "host_gateway_monitor": False,
        "vss_placement": {"num_subcores": 4, "core_nonaffinity": 2},
        "flow_table_new_syn_max_entries": 0,
        "disable_csum_offloads": False,
        "disable_tso": False,
        "enable_hsm_priming": False,
        "distribute_queues": False,
        "vss_placement_enabled": False,
        "enable_multi_lb": False,
        "n_log_streaming_threads": 1,
        "free_list_size": 1024,
        "max_rules_per_lb": 150,
        "max_public_ips_per_lb": 30,
        "minimum_connection_memory": 20,
        "shm_minimum_config_memory": 4,
        "heap_minimum_config_memory": 8,
        "disable_se_memory_check": False,
        "memory_for_config_update": 15,
        "num_dispatcher_cores": 0,
        "ssl_preprocess_sni_hostname": True,
        "se_dpdk_pmd": 0,
        "se_use_dpdk": 0,
        "min_se": 1,
        "se_pcap_reinit_frequency": 0,
        "se_pcap_reinit_threshold": 0,
        "disable_avi_securitygroups": False,
        "se_flow_probe_retries": 2,
        "vs_switchover_timeout": 300,
        "config_debugs_on_all_cores": False,
        "vs_se_scaleout_ready_timeout": 60,
        "vs_se_scaleout_additional_wait_time": 0,
        "se_dp_hm_drops": 0,
        "disable_flow_probes": False,
        "dp_aggressive_hb_frequency": 100,
        "dp_aggressive_hb_timeout_count": 10,
        "bgp_state_update_interval": 60,
        "max_memory_per_mempool": 64,
        "app_learning_memory_percent": 0,
        "datascript_timeout": 1000000,
        "se_pcap_lookahead": False,
        "enable_gratarp_permanent": False,
        "gratarp_permanent_periodicity": 10,
        "reboot_on_panic": True,
        "se_flow_probe_retry_timer": 40,
        "se_lro": True,
        "se_tx_batch_size": 64,
        "se_pcap_pkt_sz": 69632,
        "se_pcap_pkt_count": 0,
        "distribute_vnics": False,
        "se_dp_vnic_queue_stall_event_sleep": 0,
        "se_dp_vnic_queue_stall_timeout": 10000,
        "se_dp_vnic_queue_stall_threshold": 2000,
        "se_dp_vnic_restart_on_queue_stall_count": 3,
        "se_dp_vnic_stall_se_restart_window": 3600,
        "se_pcap_qdisc_bypass": True,
        "se_rum_sampling_nav_percent": 1,
        "se_rum_sampling_res_percent": 100,
        "se_rum_sampling_nav_interval": 1,
        "se_rum_sampling_res_interval": 2,
        "se_kni_burst_factor": 0,
        "max_queues_per_vnic": 1,
        "se_rl_prop": {"msf_num_stages": 1, "msf_stage_size": 16384},
        "app_cache_threshold": 5,
        "core_shm_app_learning": False,
        "core_shm_app_cache": False,
        "pcap_tx_mode": "PCAP_TX_AUTO",
        "se_dp_max_hb_version": 2,
        "resync_time_interval": 65536,
        "use_hyperthreaded_cores": True,
        "se_hyperthreaded_mode": "SE_CPU_HT_AUTO",
        "compress_ip_rules_for_each_ns_subnet": True,
        "se_vnic_tx_sw_queue_size": 256,
        "se_vnic_tx_sw_queue_flush_frequency": 0,
        "transient_shared_memory_max": 30,
        "log_malloc_failure": True,
        "se_delayed_flow_delete": True,
        "se_txq_threshold": 2048,
        "se_mp_ring_retry_count": 500,
        "dp_hb_frequency": 100,
        "dp_hb_timeout_count": 10,
        "pcap_tx_ring_rd_balancing_factor": 10,
        "use_objsync": True,
        "se_ip_encap_ipc": 0,
        "se_l3_encap_ipc": 0,
        "handle_per_pkt_attack": True,
        "per_vs_admission_control": False,
        "objsync_port": 9001,
        "se_dp_isolation": False,
        "se_dp_isolation_num_non_dp_cpus": 0,
        "cloud_ref": newCloudUrl,
        "vcenter_datastores": [{"datastore_name": dataStore}],
        "service_ip_subnets": [],
        "auto_rebalance_criteria": [],
        "auto_rebalance_capacity_per_se": [],
        "vcenter_clusters": {"include": True, "cluster_refs": [clusterUrl]},
        "license_type": "LIC_CORES",
        "se_bandwidth_type": "SE_BANDWIDTH_UNLIMITED",
        "name": seGroupName,
    }
    body_update = essentials_body if license_type == "essentials" else enterprise_body
    body.update(body_update)
    return json.dumps(body, indent=4)


def createSECloud(
    ip, csrf2, newCloudUrl, seGroupName, clusterUrl, dataStore, aviVersion, se_name_prefix, license_type="enterprise"
):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    # body = {
    #     "max_vs_per_se": 10,
    #     "min_scaleout_per_vs": 1,
    #     "max_scaleout_per_vs": 4,
    #     "max_se": 2,
    #     "vcpus_per_se": 2,
    #     "memory_per_se": 4096,
    #     "disk_per_se": 15,
    #     "max_cpu_usage": 80,
    #     "min_cpu_usage": 30,
    #     "se_deprovision_delay": 120,
    #     "auto_rebalance": False,
    #     "se_name_prefix": se_name_prefix,
    #     "vs_host_redundancy": True,
    #     "vcenter_folder": "AviSeFolder",
    #     "vcenter_datastores_include": True,
    #     "vcenter_datastore_mode": "VCENTER_DATASTORE_SHARED",
    #     "cpu_reserve": False,
    #     "mem_reserve": True,
    #     "ha_mode": "HA_MODE_LEGACY_ACTIVE_STANDBY",
    #     "algo": "PLACEMENT_ALGO_PACKED",
    #     "buffer_se": 1,
    #     "active_standby": False,
    #     "placement_mode": "PLACEMENT_MODE_AUTO",
    #     "se_dos_profile": {"thresh_period": 5},
    #     "auto_rebalance_interval": 300,
    #     "aggressive_failure_detection": False,
    #     "realtime_se_metrics": {"enabled": False, "duration": 30},
    #     "vs_scaleout_timeout": 600,
    #     "vs_scalein_timeout": 30,
    #     "connection_memory_percentage": 50,
    #     "extra_config_multiplier": 0,
    #     "vs_scalein_timeout_for_upgrade": 30,
    #     "log_disksz": 10000,
    #     "os_reserved_memory": 0,
    #     "hm_on_standby": False,
    #     "per_app": False,
    #     "distribute_load_active_standby": False,
    #     "auto_redistribute_active_standby_load": False,
    #     "dedicated_dispatcher_core": False,
    #     "cpu_socket_affinity": False,
    #     "num_flow_cores_sum_changes_to_ignore": 8,
    #     "least_load_core_selection": True,
    #     "extra_shared_config_memory": 0,
    #     "se_tunnel_mode": 0,
    #     "se_vs_hb_max_vs_in_pkt": 256,
    #     "se_vs_hb_max_pkts_in_batch": 64,
    #     "se_thread_multiplier": 1,
    #     "async_ssl": False,
    #     "async_ssl_threads": 1,
    #     "se_udp_encap_ipc": 0,
    #     "se_tunnel_udp_port": 1550,
    #     "archive_shm_limit": 8,
    #     "significant_log_throttle": 100,
    #     "udf_log_throttle": 100,
    #     "non_significant_log_throttle": 100,
    #     "ingress_access_mgmt": "SG_INGRESS_ACCESS_ALL",
    #     "ingress_access_data": "SG_INGRESS_ACCESS_ALL",
    #     "se_sb_dedicated_core": False,
    #     "se_probe_port": 7,
    #     "se_sb_threads": 1,
    #     "ignore_rtt_threshold": 5000,
    #     "waf_mempool": True,
    #     "waf_mempool_size": 64,
    #     "host_gateway_monitor": False,
    #     "vss_placement": {"num_subcores": 4, "core_nonaffinity": 2},
    #     "flow_table_new_syn_max_entries": 0,
    #     "disable_csum_offloads": False,
    #     "disable_gro": True,
    #     "disable_tso": False,
    #     "enable_hsm_priming": False,
    #     "distribute_queues": False,
    #     "vss_placement_enabled": False,
    #     "enable_multi_lb": False,
    #     "n_log_streaming_threads": 1,
    #     "free_list_size": 1024,
    #     "max_rules_per_lb": 150,
    #     "max_public_ips_per_lb": 30,
    #     "self_se_election": True,
    #     "minimum_connection_memory": 20,
    #     "shm_minimum_config_memory": 4,
    #     "heap_minimum_config_memory": 8,
    #     "disable_se_memory_check": False,
    #     "memory_for_config_update": 15,
    #     "num_dispatcher_cores": 0,
    #     "ssl_preprocess_sni_hostname": True,
    #     "se_dpdk_pmd": 0,
    #     "se_use_dpdk": 0,
    #     "min_se": 1,
    #     "se_pcap_reinit_frequency": 0,
    #     "se_pcap_reinit_threshold": 0,
    #     "disable_avi_securitygroups": False,
    #     "se_flow_probe_retries": 2,
    #     "vs_switchover_timeout": 300,
    #     "config_debugs_on_all_cores": False,
    #     "vs_se_scaleout_ready_timeout": 60,
    #     "vs_se_scaleout_additional_wait_time": 0,
    #     "se_dp_hm_drops": 0,
    #     "disable_flow_probes": False,
    #     "dp_aggressive_hb_frequency": 100,
    #     "dp_aggressive_hb_timeout_count": 10,
    #     "bgp_state_update_interval": 60,
    #     "max_memory_per_mempool": 64,
    #     "app_cache_percent": 0,
    #     "app_learning_memory_percent": 0,
    #     "datascript_timeout": 1000000,
    #     "se_pcap_lookahead": False,
    #     "enable_gratarp_permanent": False,
    #     "gratarp_permanent_periodicity": 10,
    #     "reboot_on_panic": True,
    #     "se_flow_probe_retry_timer": 40,
    #     "se_lro": True,
    #     "se_tx_batch_size": 64,
    #     "se_pcap_pkt_sz": 69632,
    #     "se_pcap_pkt_count": 0,
    #     "distribute_vnics": False,
    #     "se_dp_vnic_queue_stall_event_sleep": 0,
    #     "se_dp_vnic_queue_stall_timeout": 10000,
    #     "se_dp_vnic_queue_stall_threshold": 2000,
    #     "se_dp_vnic_restart_on_queue_stall_count": 3,
    #     "se_dp_vnic_stall_se_restart_window": 3600,
    #     "se_pcap_qdisc_bypass": True,
    #     "se_rum_sampling_nav_percent": 1,
    #     "se_rum_sampling_res_percent": 100,
    #     "se_rum_sampling_nav_interval": 1,
    #     "se_rum_sampling_res_interval": 2,
    #     "se_kni_burst_factor": 0,
    #     "max_queues_per_vnic": 1,
    #     "se_rl_prop": {"msf_num_stages": 1, "msf_stage_size": 16384},
    #     "app_cache_threshold": 5,
    #     "core_shm_app_learning": False,
    #     "core_shm_app_cache": False,
    #     "pcap_tx_mode": "PCAP_TX_AUTO",
    #     "se_dp_max_hb_version": 2,
    #     "resync_time_interval": 65536,
    #     "use_hyperthreaded_cores": True,
    #     "se_hyperthreaded_mode": "SE_CPU_HT_AUTO",
    #     "compress_ip_rules_for_each_ns_subnet": True,
    #     "se_vnic_tx_sw_queue_size": 256,
    #     "se_vnic_tx_sw_queue_flush_frequency": 0,
    #     "transient_shared_memory_max": 30,
    #     "log_malloc_failure": True,
    #     "se_delayed_flow_delete": True,
    #     "se_txq_threshold": 2048,
    #     "se_mp_ring_retry_count": 500,
    #     "dp_hb_frequency": 100,
    #     "dp_hb_timeout_count": 10,
    #     "pcap_tx_ring_rd_balancing_factor": 10,
    #     "use_objsync": True,
    #     "se_ip_encap_ipc": 0,
    #     "se_l3_encap_ipc": 0,
    #     "handle_per_pkt_attack": True,
    #     "per_vs_admission_control": False,
    #     "objsync_port": 9001,
    #     "se_dp_isolation": False,
    #     "se_dp_isolation_num_non_dp_cpus": 0,
    #     "cloud_ref": newCloudUrl,
    #     "vcenter_datastores": [{"datastore_name": dataStore}],
    #     "service_ip_subnets": [],
    #     "auto_rebalance_criteria": [],
    #     "auto_rebalance_capacity_per_se": [],
    #     "vcenter_clusters": {"include": True, "cluster_refs": [clusterUrl]},
    #     "license_tier": "ESSENTIALS",
    #     "license_type": "LIC_CORES",
    #     "se_bandwidth_type": "SE_BANDWIDTH_UNLIMITED",
    #     "name": seGroupName,
    # }
    json_object = getSeNewBody(newCloudUrl, seGroupName, clusterUrl, dataStore, se_name_prefix, license_type)
    url = "https://" + ip + "/api/serviceenginegroup"
    response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        return response_csrf.json()["url"], "SUCCESS"


def createNsxtSECloud(ip, csrf2, newCloudUrl, seGroupName, nsx_cloud_info, aviVersion, se_name_prefix):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    body = {
        "max_vs_per_se": 10,
        "min_scaleout_per_vs": 2,
        "max_scaleout_per_vs": 4,
        "max_se": 10,
        "vcpus_per_se": 2,
        "memory_per_se": 4096,
        "disk_per_se": 40,
        "se_deprovision_delay": 120,
        "auto_rebalance": False,
        "se_name_prefix": se_name_prefix,
        "vs_host_redundancy": True,
        "vcenter_folder": "AviSeFolder",
        "vcenter_datastores_include": False,
        "vcenter_datastore_mode": "VCENTER_DATASTORE_ANY",
        "cpu_reserve": False,
        "mem_reserve": True,
        "ha_mode": "HA_MODE_SHARED_PAIR",
        "algo": "PLACEMENT_ALGO_PACKED",
        "buffer_se": 1,
        "active_standby": False,
        "placement_mode": "PLACEMENT_MODE_AUTO",
        "use_hyperthreaded_cores": True,
        "se_hyperthreaded_mode": "SE_CPU_HT_AUTO",
        "vs_scaleout_timeout": 600,
        "vs_scalein_timeout": 30,
        "vss_placement": {"num_subcores": 4, "core_nonaffinity": 2},
        "realtime_se_metrics": {"enabled": False, "duration": 30},
        "se_dos_profile": {"thresh_period": 5},
        "distribute_vnics": False,
        "cloud_ref": newCloudUrl,
        "vcenter_datastores": [],
        "license_tier": "ENTERPRISE",
        "license_type": "LIC_CORES",
        "se_bandwidth_type": "SE_BANDWIDTH_UNLIMITED",
        "name": seGroupName,
        "vcenters": [
            {
                "vcenter_ref": nsx_cloud_info["vcenter_url"],
                "nsxt_clusters": {"include": True, "cluster_ids": [nsx_cloud_info["cluster"]]},
                "clusters": [],
            }
        ],
    }
    url = "https://" + ip + "/api/serviceenginegroup"
    json_object = json.dumps(body, indent=4)
    response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        return response_csrf.json()["url"], "SUCCESS"


def getIpam(ip, csrf2, name, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    body = {}
    url = "https://" + ip + "/api/ipamdnsproviderprofile"
    response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        json_object = json.dumps(response_csrf.json(), indent=4)
        with open("./ipam_details.json", "w") as outfile:
            outfile.write(json_object)
        for re in response_csrf.json()["results"]:
            if re["name"] == name:
                return re["url"], "SUCCESS"
    return "NOT_FOUND", "SUCCESS"


def createIpam(ip, csrf2, managementNetworkUrl, managementDataNetwork, vip_network, name, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    body = {
        "name": name,
        "internal_profile": {
            "ttl": 30,
            "usable_networks": [
                {"nw_ref": managementNetworkUrl},
                {"nw_ref": managementDataNetwork},
                {"nw_ref": vip_network},
            ],
        },
        "allocate_ip_in_vrf": False,
        "type": "IPAMDNS_TYPE_INTERNAL",
        "gcp_profile": {"match_se_group_subnet": False, "use_gcp_network": False},
        "azure_profile": {"use_enhanced_ha": False, "use_standard_alb": False},
    }
    json_object = json.dumps(body, indent=4)
    url = "https://" + ip + "/api/ipamdnsproviderprofile"
    response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        return response_csrf.json()["url"], "SUCCESS"


def updateIpam_profile(ip, csrf2, network_name, aviVersion):
    with open("./ipam_details.json", "r") as file2:
        ipam_json = json.load(file2)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    for ipam in ipam_json["results"]:
        if ipam["name"] == Cloud.IPAM_NAME_VSPHERE:
            ipam_obj = ipam
            break
    ipam_url = ipam_obj["url"]
    response_csrf = requests.request("GET", ipam_url, headers=headers, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    update = response_csrf.json()
    networks = []
    get_network_pg = getNetworkUrl(ip, csrf2, network_name, aviVersion)
    if get_network_pg[0] is None:
        current_app.logger.error("Failed to get  network details " + str(get_network_pg[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get network details " + str(get_network_pg[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    for usable in update["internal_profile"]["usable_networks"]:
        if usable["nw_ref"] == str(get_network_pg[0]):
            return "Already configured", "SUCCESS"
        networks.append(usable)
    network_url = get_network_pg[0]
    networks.append({"nw_ref": network_url})
    update["internal_profile"]["usable_networks"] = networks
    with open("./ipam_details_get.json", "w") as file2:
        json.dump(update, file2)
    with open("./ipam_details_get.json", "r") as file2:
        updated_body = json.load(file2)
    json_object = json.dumps(updated_body, indent=4)
    response_csrf = requests.request("PUT", ipam_url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        return response_csrf.json()["url"], "SUCCESS"


def getDetailsOfNewCloud(ip, csrf2, newCloudUrl, vim_ref, captured_ip, captured_mask, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    payload = {}
    url = newCloudUrl
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        json_object = json.dumps(response_csrf.json(), indent=4)
        os.system("rm -rf detailsOfNewCloud.json")
        with open("./detailsOfNewCloud.json", "w") as outfile:
            outfile.write(json_object)
        replaceValueSysConfig("detailsOfNewCloud.json", "vcenter_configuration", "management_network", vim_ref)
        ip_val = dict(ip_addr=dict(addr=captured_ip, type="V4"), mask=captured_mask)
        replaceValueSysConfig("detailsOfNewCloud.json", "vcenter_configuration", "management_ip_subnet", ip_val)
        return response_csrf.json(), "SUCCESS"


def getDetailsOfNewCloudAddIpam(ip, csrf2, newCloudUrl, ipamUrl, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    payload = {}
    url = newCloudUrl
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        json_object = json.dumps(response_csrf.json(), indent=4)
        os.system("rm -rf detailsOfNewCloudIpam.json")
        with open("./detailsOfNewCloudIpam.json", "w") as outfile:
            outfile.write(json_object)
        with open("detailsOfNewCloudIpam.json") as f:
            data = json.load(f)
        data["ipam_provider_ref"] = ipamUrl
        with open("detailsOfNewCloudIpam.json", "w") as f:
            json.dump(data, f)
        return response_csrf.json(), "SUCCESS"


def updateNewCloud(ip, csrf2, newCloudUrl, aviVersion):
    with open("./detailsOfNewCloud.json", "r") as file2:
        new_cloud_json = json.load(file2)
    json_object = json.dumps(new_cloud_json, indent=4)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    response_csrf = requests.request("PUT", newCloudUrl, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        return response_csrf.json(), "SUCCESS"


def generateConfigYaml(
    ip, datacenter, datastoreName, cluster_name, wpName, wipIpNetmask, _vcenter_ip, _vcenter_username, _password, env
):
    getBase64CertWriteToFile(ip, "443")
    with open("cert.txt", "r") as file2:
        cert = file2.readline()
    yaml_str = """\
    AVI_CA_DATA_B64: %s
    AVI_CLOUD_NAME: %s
    AVI_CONTROLLER: %s
    AVI_DATA_NETWORK: %s
    AVI_DATA_NETWORK_CIDR: %s
    AVI_ENABLE: "true"
    AVI_LABELS: |
        '%s': '%s'
    AVI_PASSWORD: <encoded:%s>
    AVI_SERVICE_ENGINE_GROUP: %s
    AVI_USERNAME: admin
    CLUSTER_CIDR: %s
    CLUSTER_NAME: %s
    CLUSTER_PLAN: %s
    ENABLE_CEIP_PARTICIPATION: "true"
    ENABLE_MHC: "true"
    IDENTITY_MANAGEMENT_TYPE: none
    INFRASTRUCTURE_PROVIDER: vsphere
    SERVICE_CIDR: %s
    TKG_HTTP_PROXY_ENABLED: %s
    DEPLOY_TKG_ON_VSPHERE7: "true"
    VSPHERE_DATACENTER: /%s
    VSPHERE_DATASTORE: %s
    VSPHERE_FOLDER: %s
    VSPHERE_NETWORK: %s
    VSPHERE_PASSWORD: <encoded:%s>
    VSPHERE_RESOURCE_POOL: %s
    VSPHERE_SERVER: %s
    VSPHERE_SSH_AUTHORIZED_KEY: %s
    VSPHERE_USERNAME: %s
    CONTROLPLANE_SIZE: %s
    WORKER_SIZE: %s
    VSPHERE_INSECURE: "true"
    AVI_CONTROL_PLANE_HA_PROVIDER: "true"
    ENABLE_AUDIT_LOGGING: "true"
    OS_ARCH: amd64
    OS_NAME: %s
    OS_VERSION: %s
    AVI_MANAGEMENT_CLUSTER_VIP_NETWORK_NAME: %s
    AVI_MANAGEMENT_CLUSTER_VIP_NETWORK_CIDR: %s
    """
    str_enc_avi = str(request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviPasswordBase64"])
    base64_bytes = str_enc_avi.encode("ascii")
    enc_bytes = base64.b64decode(base64_bytes)
    password_avi = enc_bytes.decode("ascii").rstrip("\n")
    _base64_bytes = password_avi.encode("ascii")
    _enc_bytes = base64.b64encode(_base64_bytes)
    str_enc_avi = _enc_bytes.decode("ascii")
    management_cluster = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtClusterName"]
    datastore_path = "/" + datacenter + "/datastore/" + datastoreName
    vsphere_folder_path = "/" + datacenter + "/vm/" + ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder_VSPHERE
    mgmt_network = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtNetworkName"]
    parent_resourcePool = request.get_json(force=True)["envSpec"]["vcenterDetails"]["resourcePoolName"]
    if parent_resourcePool:
        vsphere_rp = (
            "/"
            + datacenter
            + "/host/"
            + cluster_name
            + "/Resources/"
            + parent_resourcePool
            + "/"
            + ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE
        )
    else:
        vsphere_rp = (
            "/" + datacenter + "/host/" + cluster_name + "/Resources/" + ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE
        )
    str_enc = str(_password)
    _base64_bytes = str_enc.encode("ascii")
    _enc_bytes = base64.b64encode(_base64_bytes)
    vc_p = _enc_bytes.decode("ascii")
    vcenter_passwd = vc_p
    vcenter_ip = _vcenter_ip
    vcenter_username = _vcenter_username
    avi_cluster_vip_name = str(
        request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"]["tkgClusterVipNetworkName"]
    )
    with open("vip_ip.txt", "r") as e:
        vip_ip = e.read()
    avi_cluster_vip_network_gateway_cidr = vip_ip
    control_plan = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtDeploymentType"]
    size = str(request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtSize"])
    clustercidr = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtClusterCidr"]
    servicecidr = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtServiceCidr"]
    try:
        osName = str(request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtBaseOs"])
        if osName == "photon":
            osVersion = "3"
        elif osName == "ubuntu":
            osVersion = "20.04"
        else:
            raise Exception("Wrong os name provided")
    except Exception as e:
        raise Exception("Keyword " + str(e) + "  not found in input file")
    if size.lower() == "small":
        current_app.logger.debug("Recommended size for Management cluster nodes is: medium/large/extra-large/custom")
        pass
    elif size.lower() == "medium":
        pass
    elif size.lower() == "large":
        pass
    elif size.lower() == "extra-large":
        pass
    else:
        current_app.logger.error(
            "Provided cluster size: " + size + "is not supported, please provide one of: medium/large/extra-large"
        )
        d = {
            "responseType": "ERROR",
            "msg": "Provided cluster size: "
            + size
            + "is not supported, please provide one of: medium/large/extra-large/custom",
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    ssh_key = runSsh(vcenter_username)
    file_name = "management_cluster_vsphere.yaml"
    with open(file_name, "w") as outfile:
        if checkMgmtProxyEnabled(env):
            yaml_str_proxy = """
    TKG_HTTP_PROXY: %s
    TKG_HTTPS_PROXY: %s
    TKG_NO_PROXY: %s
            """
            proxy_str = yaml_str + yaml_str_proxy
            httpProxy = str(request.get_json(force=True)["envSpec"]["proxySpec"]["tkgMgmt"]["httpProxy"])
            httpsProxy = str(request.get_json(force=True)["envSpec"]["proxySpec"]["tkgMgmt"]["httpsProxy"])
            noProxy = str(request.get_json(force=True)["envSpec"]["proxySpec"]["tkgMgmt"]["noProxy"])
            noProxy = noProxy.strip("\n").strip(" ").strip("\r")
            formatted = proxy_str % (
                cert,
                Cloud.CLOUD_NAME_VSPHERE,
                ip,
                wpName,
                wipIpNetmask,
                AkoType.KEY,
                AkoType.VALUE,
                str_enc_avi,
                Cloud.SE_GROUP_NAME_VSPHERE,
                clustercidr,
                management_cluster,
                control_plan,
                servicecidr,
                "true",
                datacenter,
                datastore_path,
                vsphere_folder_path,
                mgmt_network,
                vcenter_passwd,
                vsphere_rp,
                vcenter_ip,
                ssh_key,
                vcenter_username,
                size.lower(),
                size.lower(),
                osName,
                osVersion,
                avi_cluster_vip_name,
                avi_cluster_vip_network_gateway_cidr,
                httpProxy,
                httpsProxy,
                noProxy,
            )
        elif checkAirGappedIsEnabled(env):
            yaml_str_airgapped = """
    TKG_CUSTOM_IMAGE_REPOSITORY: %s
            """
            airgapped_str = yaml_str + yaml_str_airgapped
            air_gapped_repo = str(
                request.get_json(force=True)["envSpec"]["customRepositorySpec"]["tkgCustomImageRepository"]
            )
            air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
            os.putenv("TKG_BOM_IMAGE_TAG", Tkg_version.TAG)
            os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY", air_gapped_repo)
            isSelfsinged = str(
                request.get_json(force=True)["envSpec"]["customRepositorySpec"]["tkgCustomImageRepositoryPublicCaCert"]
            )
            if isSelfsinged.lower() == "false":
                s = """
    TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY: "False"
    TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE: %s
                """
                os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False")
                airgapped_str = airgapped_str + s
                # url = air_gapped_repo[: air_gapped_repo.find("/")]
                getBase64CertWriteToFile(grabHostFromUrl(air_gapped_repo), grabPortFromUrl(air_gapped_repo))
                with open("cert.txt", "r") as file2:
                    repo_cert = file2.readline()
                repo_certificate = repo_cert
                os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE", repo_certificate)
                formatted = airgapped_str % (
                    cert,
                    Cloud.CLOUD_NAME_VSPHERE,
                    ip,
                    wpName,
                    wipIpNetmask,
                    AkoType.KEY,
                    AkoType.VALUE,
                    str_enc_avi,
                    Cloud.SE_GROUP_NAME_VSPHERE,
                    clustercidr,
                    management_cluster,
                    control_plan,
                    servicecidr,
                    "false",
                    datacenter,
                    datastore_path,
                    vsphere_folder_path,
                    mgmt_network,
                    vcenter_passwd,
                    vsphere_rp,
                    vcenter_ip,
                    ssh_key,
                    vcenter_username,
                    size.lower(),
                    size.lower(),
                    osName,
                    osVersion,
                    avi_cluster_vip_name,
                    avi_cluster_vip_network_gateway_cidr,
                    air_gapped_repo,
                    repo_certificate,
                )
            else:
                s = """
    TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY: "False"
                """
                os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False")
                airgapped_str = airgapped_str + s
                formatted = airgapped_str % (
                    cert,
                    Cloud.CLOUD_NAME_VSPHERE,
                    ip,
                    wpName,
                    wipIpNetmask,
                    AkoType.KEY,
                    AkoType.VALUE,
                    str_enc_avi,
                    Cloud.SE_GROUP_NAME_VSPHERE,
                    clustercidr,
                    management_cluster,
                    control_plan,
                    servicecidr,
                    "false",
                    datacenter,
                    datastore_path,
                    vsphere_folder_path,
                    mgmt_network,
                    vcenter_passwd,
                    vsphere_rp,
                    vcenter_ip,
                    ssh_key,
                    vcenter_username,
                    size.lower(),
                    size.lower(),
                    osName,
                    osVersion,
                    avi_cluster_vip_name,
                    avi_cluster_vip_network_gateway_cidr,
                    air_gapped_repo,
                )
        else:
            disable_proxy()
            formatted = yaml_str % (
                cert,
                Cloud.CLOUD_NAME_VSPHERE,
                ip,
                wpName,
                wipIpNetmask,
                AkoType.KEY,
                AkoType.VALUE,
                str_enc_avi,
                Cloud.SE_GROUP_NAME_VSPHERE,
                clustercidr,
                management_cluster,
                control_plan,
                servicecidr,
                "false",
                datacenter,
                datastore_path,
                vsphere_folder_path,
                mgmt_network,
                vcenter_passwd,
                vsphere_rp,
                vcenter_ip,
                ssh_key,
                vcenter_username,
                size.lower(),
                size.lower(),
                osName,
                osVersion,
                avi_cluster_vip_name,
                avi_cluster_vip_network_gateway_cidr,
            )
        data1 = yaml.load(formatted, Loader=yaml.RoundTripLoader)
        yaml.dump(data1, outfile, Dumper=yaml.RoundTripDumper, indent=2)


def templateMgmtDeployYaml(
    ip,
    datacenter,
    avi_version,
    data_store,
    cluster_name,
    wpName,
    wipIpNetmask,
    vcenter_ip,
    vcenter_username,
    password,
    env,
    vsSpec,
):
    tkg_cluster_vip_network_name = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"][
        "tkgClusterVipNetworkName"
    ]
    cluster_vip_cidr = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"][
        "tkgClusterVipNetworkGatewayCidr"
    ]
    mgmt_group_name = Cloud.SE_GROUP_NAME_VSPHERE
    workload_group_name = Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE
    tier1_path = ""
    if env == Env.VCF:
        mgmt_group_name = Cloud.SE_GROUP_NAME_VSPHERE.replace("vsphere", "nsxt")
        workload_group_name = Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE.replace("vsphere", "nsxt")
        csrf2 = obtain_second_csrf(ip, env)
        if csrf2 is None:
            current_app.logger.error("Failed to get csrf from new set password")
            d = {"responseType": "ERROR", "msg": "Failed to get csrf from new set password", "STATUS_CODE": 500}
            return jsonify(d), 500
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": avi_version,
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
        tier1_path = status_tier1
    deploy_yaml = FileHelper.read_resource(Paths.TKG_MGMT_SPEC_J2)
    t = Template(deploy_yaml)
    datastore_path = "/" + datacenter + "/datastore/" + data_store
    vsphere_folder_path = "/" + datacenter + "/vm/" + ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder_VSPHERE
    str_enc = str(password)
    _base64_bytes = str_enc.encode("ascii")
    _enc_bytes = base64.b64encode(_base64_bytes)
    vcenter_passwd = _enc_bytes.decode("ascii")
    management_cluster = vsSpec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtClusterName
    os.system("rm -rf " + Paths.CLUSTER_PATH + management_cluster + "/management_cluster_vsphere.yaml")
    parent_resourcePool = vsSpec.envSpec.vcenterDetails.resourcePoolName
    if parent_resourcePool:
        vsphere_rp = (
            "/"
            + datacenter
            + "/host/"
            + cluster_name
            + "/Resources/"
            + parent_resourcePool
            + "/"
            + ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE
        )
    else:
        vsphere_rp = (
            "/" + datacenter + "/host/" + cluster_name + "/Resources/" + ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE
        )
    datacenter = "/" + datacenter
    ssh_key = runSsh(vcenter_username)
    size = vsSpec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtSize
    control_plane_vcpu = ""
    control_plane_disk_gb = ""
    control_plane_mem_mb = ""
    proxyCert = ""
    try:
        proxyCert_raw = request.get_json(force=True)["envSpec"]["proxySpec"]["tkgMgmt"]["proxyCert"]
        base64_bytes = base64.b64encode(proxyCert_raw.encode("utf-8"))
        proxyCert = str(base64_bytes, "utf-8")
        isProxy = "true"
    except Exception:
        isProxy = "false"
        current_app.logger.info("Proxy certificate for  Management is not provided")
    ciep = str(request.get_json(force=True)["envSpec"]["ceipParticipation"])
    if size.lower() == "small":
        current_app.logger.debug("Recommended size for Management cluster nodes is: medium/large/extra-large/custom")
        pass
    elif size.lower() == "medium":
        pass
    elif size.lower() == "large":
        pass
    elif size.lower() == "extra-large":
        pass
    elif size.lower() == "custom":
        control_plane_vcpu = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtCpuSize"]
        control_plane_disk_gb = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"][
            "tkgMgmtStorageSize"
        ]
        control_plane_mem_gb = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"][
            "tkgMgmtMemorySize"
        ]
        control_plane_mem_mb = str(int(control_plane_mem_gb) * 1024)
    else:
        current_app.logger.error(
            "Provided cluster size: "
            + size
            + "is not supported, please provide one of: medium/large/extra-large/custom"
        )
        d = {
            "responseType": "ERROR",
            "msg": "Provided cluster size: "
            + size
            + "is not supported, please provide one of: medium/large/extra-large/custom",
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    try:
        osName = str(request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtBaseOs"])
        if osName == "photon":
            osVersion = "3"
        elif osName == "ubuntu":
            osVersion = "20.04"
        else:
            raise Exception("Wrong os name provided")
    except Exception as e:
        raise Exception("Keyword " + str(e) + "  not found in input file")
    with open("vip_ip.txt", "r") as e:
        vip_ip = e.read()
    tkg_cluster_vip_network_cidr = vip_ip
    air_gapped_repo = ""
    repo_certificate = ""
    if checkAirGappedIsEnabled(env):
        air_gapped_repo = vsSpec.envSpec.customRepositorySpec.tkgCustomImageRepository
        air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
        os.putenv("TKG_BOM_IMAGE_TAG", Tkg_version.TAG)
        os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY", air_gapped_repo)
        os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False")
        getBase64CertWriteToFile(grabHostFromUrl(air_gapped_repo), grabPortFromUrl(air_gapped_repo))
        with open("cert.txt", "r") as file2:
            repo_cert = file2.readline()
        repo_certificate = repo_cert
        os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE", repo_certificate)
    # compliant deployment flogs for TKGm deployment
    if isEnvTkgm(env) or env == Env.VCF:
        compliant_flag = request.get_json(force=True)["envSpec"]["compliantSpec"]["compliantDeployment"]
        if compliant_flag.lower() == "true":
            if osName != "ubuntu":
                raise Exception("Wrong os name provided for complaint deployment, please use ubuntu as OS")
            current_app.logger.info("Performing compliant enable deployment.")
            os.putenv("TKG_CUSTOM_COMPATIBILITY_IMAGE_PATH", "fips/tkg-compatibility")
            # copy fips enabled overlays
            os.system(f"cp -rf common/overlays/04_user_customizations/  {Env.UPDATED_YTT_FILE_LOCATION}/")
            # remove old bom
            current_app.logger.info("Customized FIPS enabled overlay has been copied.")
            os.system(f"rm -r {Env.BOM_FILE_LOCATION}/")
            os.system(f"rm -r {Env.COMPATIBILITY_FILE_LOCATION}/")
            os.system(f"rm -r {Env.CACHE_FILE_LOCATION}/")
            # fetch new bom for fips deployment
            listOfCmd = ["tanzu", "plugin", "sync"]
            runProcess(listOfCmd)
            listOfCmd = ["tanzu", "config", "init"]
            runProcess(listOfCmd)
            update_template_in_ova()
        else:
            os.putenv("TKG_CUSTOM_COMPATIBILITY_IMAGE_PATH", "tkg-compatibility")
    if checkEnableIdentityManagement(env):
        try:
            identity_mgmt_type = str(
                request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["identityManagementType"]
            )
            if identity_mgmt_type.lower() == "oidc":
                oidc_provider_client_id = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["oidcSpec"][
                        "oidcClientId"
                    ]
                )
                oidc_provider_client_secret = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["oidcSpec"][
                        "oidcClientSecret"
                    ]
                )
                oidc_provider_groups_claim = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["oidcSpec"][
                        "oidcGroupsClaim"
                    ]
                )
                oidc_provider_issuer_url = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["oidcSpec"][
                        "oidcIssuerUrl"
                    ]
                )
                # TODO: check if provider name is required -- NOT REQUIRED
                # oidc_provider_name = str(request.get_json(force=True))
                oidc_provider_scopes = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["oidcSpec"]["oidcScopes"]
                )
                oidc_provider_username_claim = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["oidcSpec"][
                        "oidcUsernameClaim"
                    ]
                )
                FileHelper.write_to_file(
                    t.render(
                        config=vsSpec,
                        avi_cert=get_base64_cert(ip),
                        ip=ip,
                        wpName=wpName,
                        wipIpNetmask=wipIpNetmask,
                        ceip=ciep,
                        isProxyCert=isProxy,
                        proxyCert=proxyCert,
                        avi_label_key=AkoType.KEY,
                        avi_label_value=AkoType.VALUE,
                        cluster_name=management_cluster,
                        data_center=datacenter,
                        datastore_path=datastore_path,
                        vsphere_folder_path=vsphere_folder_path,
                        vcenter_passwd=vcenter_passwd,
                        vsphere_rp=vsphere_rp,
                        vcenter_ip=vcenter_ip,
                        ssh_key=ssh_key,
                        vcenter_username=vcenter_username,
                        size_controlplane=size.lower(),
                        size_worker=size.lower(),
                        tkg_cluster_vip_network_cidr=tkg_cluster_vip_network_cidr,
                        air_gapped_repo=air_gapped_repo,
                        repo_certificate=repo_certificate,
                        osName=osName,
                        osVersion=osVersion,
                        avi_version=avi_version,
                        env=env,
                        tier1_path=tier1_path,
                        vip_cidr=cluster_vip_cidr,
                        tkg_cluster_vip_network_name=tkg_cluster_vip_network_name,
                        management_group=mgmt_group_name,
                        workload_group=workload_group_name,
                        size=size,
                        control_plane_vcpu=control_plane_vcpu,
                        control_plane_disk_gb=control_plane_disk_gb,
                        control_plane_mem_mb=control_plane_mem_mb,
                        identity_mgmt_type=identity_mgmt_type,
                        oidc_provider_client_id=oidc_provider_client_id,
                        oidc_provider_client_secret=oidc_provider_client_secret,
                        oidc_provider_groups_claim=oidc_provider_groups_claim,
                        oidc_provider_issuer_url=oidc_provider_issuer_url,
                        oidc_provider_scopes=oidc_provider_scopes,
                        oidc_provider_username_claim=oidc_provider_username_claim,
                    ),
                    Paths.CLUSTER_PATH + management_cluster + "/management_cluster_vsphere.yaml",
                )
            # TODO: add ldap code here
            elif identity_mgmt_type.lower() == "ldap":
                ldap_endpoint_ip = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["ldapSpec"][
                        "ldapEndpointIp"
                    ]
                )
                ldap_endpoint_port = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["ldapSpec"][
                        "ldapEndpointPort"
                    ]
                )
                str_enc = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["ldapSpec"][
                        "ldapBindPWBase64"
                    ]
                )
                base64_bytes = str_enc.encode("ascii")
                enc_bytes = base64.b64decode(base64_bytes)
                ldap_endpoint_bind_pw = enc_bytes.decode("ascii").rstrip("\n")
                ldap_bind_dn = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["ldapSpec"]["ldapBindDN"]
                )
                ldap_user_search_base_dn = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["ldapSpec"][
                        "ldapUserSearchBaseDN"
                    ]
                )
                ldap_user_search_filter = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["ldapSpec"][
                        "ldapUserSearchFilter"
                    ]
                )
                ldap_user_search_uname = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["ldapSpec"][
                        "ldapUserSearchUsername"
                    ]
                )
                ldap_grp_search_base_dn = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["ldapSpec"][
                        "ldapGroupSearchBaseDN"
                    ]
                )
                ldap_grp_search_filter = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["ldapSpec"][
                        "ldapGroupSearchFilter"
                    ]
                )
                ldap_grp_search_user_attr = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["ldapSpec"][
                        "ldapGroupSearchUserAttr"
                    ]
                )
                ldap_grp_search_grp_attr = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["ldapSpec"][
                        "ldapGroupSearchGroupAttr"
                    ]
                )
                ldap_grp_search_name_attr = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["ldapSpec"][
                        "ldapGroupSearchNameAttr"
                    ]
                )
                ldap_root_ca_data = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["ldapSpec"][
                        "ldapRootCAData"
                    ]
                )
                if not ldap_user_search_base_dn:
                    current_app.logger.error("Please provide ldapUserSearchBaseDN for installing pinniped")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Please provide ldapUserSearchBaseDN for installing pinniped",
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                if not ldap_grp_search_base_dn:
                    current_app.logger.error("Please provide ldapGroupSearchBaseDN for installing pinniped")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Please provide ldapGroupSearchBaseDN for installing pinniped",
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                base64_bytes = base64.b64encode(ldap_root_ca_data.encode("utf-8"))
                ldap_root_ca_data_base64 = str(base64_bytes, "utf-8")
                FileHelper.write_to_file(
                    t.render(
                        config=vsSpec,
                        avi_cert=get_base64_cert(ip),
                        ip=ip,
                        wpName=wpName,
                        wipIpNetmask=wipIpNetmask,
                        ceip=ciep,
                        isProxyCert=isProxy,
                        proxyCert=proxyCert,
                        avi_label_key=AkoType.KEY,
                        avi_label_value=AkoType.VALUE,
                        cluster_name=management_cluster,
                        data_center=datacenter,
                        datastore_path=datastore_path,
                        vsphere_folder_path=vsphere_folder_path,
                        vcenter_passwd=vcenter_passwd,
                        vsphere_rp=vsphere_rp,
                        vcenter_ip=vcenter_ip,
                        ssh_key=ssh_key,
                        vcenter_username=vcenter_username,
                        size_controlplane=size.lower(),
                        size_worker=size.lower(),
                        tkg_cluster_vip_network_cidr=tkg_cluster_vip_network_cidr,
                        air_gapped_repo=air_gapped_repo,
                        repo_certificate=repo_certificate,
                        osName=osName,
                        osVersion=osVersion,
                        avi_version=avi_version,
                        env=env,
                        tier1_path=tier1_path,
                        vip_cidr=cluster_vip_cidr,
                        tkg_cluster_vip_network_name=tkg_cluster_vip_network_name,
                        management_group=mgmt_group_name,
                        workload_group=workload_group_name,
                        size=size,
                        control_plane_vcpu=control_plane_vcpu,
                        control_plane_disk_gb=control_plane_disk_gb,
                        control_plane_mem_mb=control_plane_mem_mb,
                        identity_mgmt_type=identity_mgmt_type,
                        ldap_endpoint_ip=ldap_endpoint_ip,
                        ldap_endpoint_port=ldap_endpoint_port,
                        ldap_endpoint_bind_pw=ldap_endpoint_bind_pw,
                        ldap_bind_dn=ldap_bind_dn,
                        ldap_user_search_base_dn=ldap_user_search_base_dn,
                        ldap_user_search_filter=ldap_user_search_filter,
                        ldap_user_search_uname=ldap_user_search_uname,
                        ldap_grp_search_base_dn=ldap_grp_search_base_dn,
                        ldap_grp_search_filter=ldap_grp_search_filter,
                        ldap_grp_search_user_attr=ldap_grp_search_user_attr,
                        ldap_grp_search_grp_attr=ldap_grp_search_grp_attr,
                        ldap_grp_search_name_attr=ldap_grp_search_name_attr,
                        ldap_root_ca_data_base64=ldap_root_ca_data_base64,
                    ),
                    Paths.CLUSTER_PATH + management_cluster + "/management_cluster_vsphere.yaml",
                )
            #     TODO: Read param
            else:
                raise Exception("Wrong Identity Management type provided, accepted values are: oidc or ldap")
        except Exception as e:
            raise Exception("Keyword " + str(e) + "  not found in input file")
    else:
        FileHelper.write_to_file(
            t.render(
                config=vsSpec,
                avi_cert=get_base64_cert(ip),
                ip=ip,
                wpName=wpName,
                wipIpNetmask=wipIpNetmask,
                avi_label_key=AkoType.KEY,
                avi_label_value=AkoType.VALUE,
                cluster_name=management_cluster,
                data_center=datacenter,
                datastore_path=datastore_path,
                ceip=ciep,
                isProxyCert=isProxy,
                proxyCert=proxyCert,
                vsphere_folder_path=vsphere_folder_path,
                vcenter_passwd=vcenter_passwd,
                vsphere_rp=vsphere_rp,
                vcenter_ip=vcenter_ip,
                ssh_key=ssh_key,
                vcenter_username=vcenter_username,
                size_controlplane=size.lower(),
                size_worker=size.lower(),
                avi_version=avi_version,
                env=env,
                tier1_path=tier1_path,
                vip_cidr=cluster_vip_cidr,
                tkg_cluster_vip_network_name=tkg_cluster_vip_network_name,
                management_group=mgmt_group_name,
                workload_group=workload_group_name,
                tkg_cluster_vip_network_cidr=tkg_cluster_vip_network_cidr,
                air_gapped_repo=air_gapped_repo,
                repo_certificate=repo_certificate,
                osName=osName,
                osVersion=osVersion,
                size=size,
                control_plane_vcpu=control_plane_vcpu,
                control_plane_disk_gb=control_plane_disk_gb,
                control_plane_mem_mb=control_plane_mem_mb,
            ),
            Paths.CLUSTER_PATH + management_cluster + "/management_cluster_vsphere.yaml",
        )


def deployManagementCluster(
    management_cluster,
    ip,
    data_center,
    data_store,
    cluster_name,
    wpName,
    wipIpNetmask,
    vcenter_ip,
    vcenter_username,
    avi_version,
    password,
    env,
    vsSpec,
):
    try:
        if not getClusterStatusOnTanzu(management_cluster, "management"):
            os.system("rm -rf kubeconfig.yaml")
            templateMgmtDeployYaml(
                ip,
                data_center,
                avi_version,
                data_store,
                cluster_name,
                wpName,
                wipIpNetmask,
                vcenter_ip,
                vcenter_username,
                password,
                env,
                vsSpec,
            )
            # generateConfigYaml(ip, data_center, data_store, cluster_name, wpName, wipIpNetmask, vcenter_ip,
            #                    vcenter_username,
            #                    password, env)
            current_app.logger.info("Deploying management cluster")
            os.putenv("DEPLOY_TKG_ON_VSPHERE7", "true")
            listOfCmd = [
                "tanzu",
                "management-cluster",
                "create",
                "-y",
                "--file",
                Paths.CLUSTER_PATH + management_cluster + "/management_cluster_vsphere.yaml",
                "-v",
                "6",
            ]
            runProcess(listOfCmd)
            listOfCmdKube = [
                "tanzu",
                "management-cluster",
                "kubeconfig",
                "get",
                management_cluster,
                "--admin",
                "--export-file",
                "kubeconfig.yaml",
            ]
            runProcess(listOfCmdKube)
            current_app.logger.info("Waiting for 1 min for status==ready")
            time.sleep(60)
            return "SUCCESS", 200
        else:
            return "SUCCESS", 200
    except Exception as e:
        return None, str(e)


def seperateNetmaskAndIp(cidr):
    return str(cidr).split("/")


def updateVipNetworkIpPools(ip, csrf2, get_vip, aviVersion):
    try:
        env = envCheck()
        env = env[0]
        startIp = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"]["tkgClusterVipIpStartRange"]
        endIp = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"]["tkgClusterVipIpEndRange"]
        prefixIpNetmask = seperateNetmaskAndIp(
            request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"]["tkgClusterVipNetworkGatewayCidr"]
        )

        if env == Env.VCF:
            getVIPNetworkDetails = getNSXTNetworkDetailsVip(
                ip, csrf2, get_vip[0], startIp, endIp, prefixIpNetmask[0], prefixIpNetmask[1], aviVersion
            )
        else:
            getVIPNetworkDetails = getNetworkDetailsVip(
                ip, csrf2, get_vip[0], startIp, endIp, prefixIpNetmask[0], prefixIpNetmask[1], aviVersion, env
            )
        if getVIPNetworkDetails[0] is None:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get VIP network details " + str(getVIPNetworkDetails[2]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        if getVIPNetworkDetails[0] == "AlreadyConfigured":
            current_app.logger.info("Vip Ip pools are already configured.")
            ip_pre = getVIPNetworkDetails[2]["subnet_ip"] + "/" + str(getVIPNetworkDetails[2]["subnet_mask"])
        else:
            update_resp = updateNetworkWithIpPools(ip, csrf2, get_vip[0], "vipNetworkDetails.json", aviVersion)
            if update_resp[0] != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to update VIP network ip pools " + str(update_resp[1]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            ip_pre = update_resp[2]["subnet_ip"] + "/" + str(update_resp[2]["subnet_mask"])
        with open("vip_ip.txt", "w") as e:
            e.write(ip_pre)
        d = {"responseType": "SUCCESS", "msg": "Updated VIP IP pools successfully", "STATUS_CODE": 200}
        return jsonify(d), 200
    except Exception as e:
        d = {"responseType": "ERROR", "msg": "Failed to update VIP IP pools " + str(e), "STATUS_CODE": 500}
        return jsonify(d), 500


def getCloudConnectUser(ip, headers):
    url = "https://" + ip + "/api/cloudconnectoruser"
    payload = {}
    try:
        response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
        if response_csrf.status_code != 200:
            return "API_FAILURE", response_csrf.text
        vcenterCred = False
        nsxCred = False
        uuid = {}
        list_ = response_csrf.json()["results"]
        if len(list_) == 0:
            return "EMPTY", "EMPTY"
        for result in list_:
            if result["name"] == NSXtCloud.VCENTER_CREDENTIALS:
                uuid["vcenterUUId"] = result["uuid"]
                uuid["vcenter_user_url"] = result["url"]
                vcenterCred = True
            if result["name"] == NSXtCloud.NSXT_CREDENTIALS:
                uuid["nsxUUid"] = result["uuid"]
                uuid["nsx_user_url"] = result["url"]
                nsxCred = True
        if vcenterCred and nsxCred:
            return "BOTH_CRED_CREATED", uuid
        found = False
        if vcenterCred:
            found = True
            tuple_ = "VCENTER_CRED_FOUND", uuid["vcenterUUId"], uuid["vcenter_user_url"]
        if nsxCred:
            found = True
            tuple_ = "NSX_CRED_FOUND", uuid["nsxUUid"], uuid["nsx_user_url"]
        if found:
            return "ONE_CRED_FOUND", tuple_
        return "NO_CRED_FOUND", "NO_CRED_FOUND"
    except Exception as e:
        return "EXCEPTION", "Failed " + str(e)


def createCloudConnectUser(ip, headers):
    url = "https://" + ip + "/api/cloudconnectoruser"
    try:
        vcenter_username = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterSsoUser"]
        str_enc = str(request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterSsoPasswordBase64"])
        base64_bytes = str_enc.encode("ascii")
        enc_bytes = base64.b64decode(base64_bytes)
        password = enc_bytes.decode("ascii").rstrip("\n")

        str_enc_nsx = str(request.get_json(force=True)["envSpec"]["vcenterDetails"]["nsxtUserPasswordBase64"])
        base64_bytes_nsx = str_enc_nsx.encode("ascii")
        enc_bytes_nsx = base64.b64decode(base64_bytes_nsx)
        password_nsx = enc_bytes_nsx.decode("ascii").rstrip("\n")
        nsx_user = request.get_json(force=True)["envSpec"]["vcenterDetails"]["nsxtUser"]
        list_body = []
        body_nsx = {
            "name": NSXtCloud.NSXT_CREDENTIALS,
            "nsxt_credentials": {"username": nsx_user, "password": password_nsx},
        }
        body_vcenter = {
            "name": NSXtCloud.VCENTER_CREDENTIALS,
            "vcenter_credentials": {"username": vcenter_username, "password": password},
        }
        status_ = {}
        body_vcenter = json.dumps(body_vcenter, indent=4)
        body_nsx = json.dumps(body_nsx, indent=4)
        cloud_user, status = getCloudConnectUser(ip, headers)
        if str(cloud_user) == "EXCEPTION" or str(cloud_user) == "API_FAILURE":
            return None, status
        if str(status) == "NO_CRED_FOUND" or str(status) == "EMPTY":
            current_app.logger.info("Creating Nsx and vcenter credential")
            list_body.append(body_vcenter)
            list_body.append(body_nsx)
        if str(cloud_user) == "ONE_CRED_FOUND":
            if str(status[0]) == "VCENTER_CRED_FOUND":
                current_app.logger.info("Creating Nsx credentials")
                status_["vcenterUUId"] = status[1]["uuid"]
                list_body.append(body_nsx)
            elif str(status[0]) == "NSX_CRED_FOUND":
                current_app.logger.info("Creating Vcenter credentials")
                status_["nsxUUid"] = status[1]["uuid"]
                list_body.append(body_vcenter)
        if str(cloud_user) != "BOTH_CRED_CREATED":
            for body in list_body:
                response_csrf = requests.request("POST", url, headers=headers, data=body, verify=False)
                if response_csrf.status_code != 201:
                    return None, response_csrf.text
                try:
                    # nsx = response_csrf.json()["nsxt_credentials"]
                    status_["nsxUUid"] = response_csrf.json()["uuid"]
                except Exception:
                    pass
                try:
                    # vcenter = response_csrf.json()["vcenter_credentials"]
                    status_["vcenterUUId"] = response_csrf.json()["uuid"]
                except Exception:
                    pass
                time.sleep(10)
            if len(status_) < 2:
                return None, "INSUFFICIENT_ITEMS " + str(status_)
            return "SUCCESS", status_
        else:
            return "SUCCESS", status
    except Exception as e:
        return None, str(e)


def fetchContentLibrary(ip, headers, vcenter_credential):
    try:
        vc_Content_Library_name = request.get_json(force=True)["envSpec"]["vcenterDetails"]["contentLibraryName"]
        if not vc_Content_Library_name:
            vc_Content_Library_name = ControllerLocation.CONTROLLER_CONTENT_LIBRARY
        vCenter = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterAddress"]
        vCenterUser = current_app.config["VC_USER"]
        vCenterPassword = current_app.config["VC_PASSWORD"]
        url = "https://" + ip + "/api/vimgrvcenterruntime/retrieve/contentlibraries"
        body = {
            "host": vCenter,
            "username": vCenterUser,
            "password": vCenterPassword,
        }
        json_object = json.dumps(body, indent=4)
        response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        for library in response_csrf.json()["resource"]["vcenter_clibs"]:
            if library["name"] == vc_Content_Library_name:
                return "Success", library["id"]
        return None, "CONTENT_LIBRARY_NOT_FOUND"
    except Exception as e:
        return None, str(e)


def fetchTier1GatewayId(ip, headers, nsxt_credential):
    try:
        url = "https://" + ip + "/api/nsxt/tier1s"
        teir1name = str(request.get_json(force=True)["envSpec"]["vcenterDetails"]["nsxtTier1RouterDisplayName"])
        address = str(request.get_json(force=True)["envSpec"]["vcenterDetails"]["nsxtAddress"])
        body = {"host": address, "credentials_uuid": nsxt_credential}
        json_object = json.dumps(body, indent=4)
        response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        for library in response_csrf.json()["resource"]["nsxt_tier1routers"]:
            if library["name"] == teir1name:
                return "Success", library["id"]
        return None, "TIER1_GATEWAY_ID_NOT_FOUND"
    except Exception as e:
        return None, str(e)


def fetchTransportZoneId(ip, headers, nsxt_credential):
    try:
        url = "https://" + ip + "/api/nsxt/transportzones"
        overlay = str(request.get_json(force=True)["envSpec"]["vcenterDetails"]["nsxtOverlay"])
        address = str(request.get_json(force=True)["envSpec"]["vcenterDetails"]["nsxtAddress"])
        body = {"host": address, "credentials_uuid": nsxt_credential}
        json_object = json.dumps(body, indent=4)
        response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        for library in response_csrf.json()["resource"]["nsxt_transportzones"]:
            if library["name"] == overlay and library["tz_type"] == "OVERLAY":
                return "Success", library["id"]
        return None, "TRANSPORT_ZONE_ID_NOT_FOUND"
    except Exception as e:
        return None, str(e)


def fetchVcenterId(ip, headers, nsxt_credential, tz_id):
    try:
        url = "https://" + ip + "/api/nsxt/vcenters"
        address = str(request.get_json(force=True)["envSpec"]["vcenterDetails"]["nsxtAddress"])
        address_vc = str(request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterAddress"])
        body = {"host": address, "credentials_uuid": nsxt_credential, "transport_zone_id": tz_id}
        json_object = json.dumps(body, indent=4)
        import socket

        try:
            vc_ip = socket.gethostbyname(address_vc)
        except Exception as e:
            return None, str(e)
        response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        for library in response_csrf.json()["resource"]["vcenter_ips"]:
            if library["vcenter_ip"]["addr"] == vc_ip:
                return "Success", library["vcenter_ip"]["addr"]
        return None, "VC_NOT_FOUND"
    except Exception as e:
        return None, str(e)


def fetchSegmentsId(ip, headers, nsxt_credential, tz_id, tier1_id):
    try:
        url = "https://" + ip + "/api/nsxt/segments"
        address = str(request.get_json(force=True)["envSpec"]["vcenterDetails"]["nsxtAddress"])
        body = {"host": address, "credentials_uuid": nsxt_credential, "transport_zone_id": tz_id, "tier1_id": tier1_id}
        json_object = json.dumps(body, indent=4)
        response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        segId = {}
        avi_mgmt = request.get_json(force=True)["tkgComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkName"]
        tkg_cluster_vip_name = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"][
            "tkgClusterVipNetworkName"
        ]
        for library in response_csrf.json()["resource"]["nsxt_segments"]:
            if library["name"] == avi_mgmt:
                segId["avi_mgmt"] = library["id"]
            elif library["name"] == tkg_cluster_vip_name:
                segId["cluster_vip"] = library["id"]
            if len(segId) == 2:
                break
        if len(segId) < 2:
            return None, "SEGMENT_NOT_FOUND " + str(segId)
        return "Success", segId
    except Exception as e:
        return None, str(e)


def createNsxtCloud(ip, csrf2, aviVersion):
    try:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0],
        }
        cloud_connect_user, cred = createCloudConnectUser(ip, headers)
        if cloud_connect_user is None:
            return None, cred
        nsxt_cred = cred["nsxUUid"]
        zone, status_zone = fetchTransportZoneId(ip, headers, nsxt_cred)
        if zone is None:
            return None, status_zone
        tier1_id, status_tier1 = fetchTier1GatewayId(ip, headers, nsxt_cred)
        if tier1_id is None:
            return None, status_tier1
        tz_id, status_tz = fetchTransportZoneId(ip, headers, nsxt_cred)
        if tz_id is None:
            return None, status_tz
        seg_id, status_seg = fetchSegmentsId(ip, headers, nsxt_cred, status_tz, status_tier1)
        if seg_id is None:
            return None, status_seg
        status, value = getCloudConnectUser(ip, headers)
        address = str(request.get_json(force=True)["envSpec"]["vcenterDetails"]["nsxtAddress"])
        if isinstance(value, tuple):
            nsx_url = value[2]
        else:
            nsx_url = value["nsx_user_url"]
        body = {
            "dhcp_enabled": True,
            "dns_resolution_on_se": False,
            "enable_vip_on_all_interfaces": False,
            "enable_vip_static_routes": False,
            "ip6_autocfg_enabled": False,
            "maintenance_mode": False,
            "mtu": 1500,
            "nsxt_configuration": {
                "site_id": "default",
                "domain_id": "default",
                "enforcementpoint_id": "default",
                "automate_dfw_rules": False,
                "data_network_config": {
                    "transport_zone": status_zone,
                    "tz_type": "OVERLAY",
                    "tier1_segment_config": {
                        "segment_config_mode": "TIER1_SEGMENT_MANUAL",
                        "manual": {
                            "tier1_lrs": [{"segment_id": status_seg["cluster_vip"], "tier1_lr_id": status_tier1}]
                        },
                    },
                },
                "management_network_config": {
                    "transport_zone": status_zone,
                    "tz_type": "OVERLAY",
                    "overlay_segment": {"segment_id": status_seg["avi_mgmt"], "tier1_lr_id": status_tier1},
                },
                "nsxt_credentials_ref": nsx_url,
                "nsxt_url": address,
            },
            "obj_name_prefix": Cloud.CLOUD_NAME_VSPHERE.replace("vsphere", "nsxt"),
            "name": Cloud.CLOUD_NAME_VSPHERE.replace("vsphere", "nsxt"),
            "prefer_static_routes": False,
            "state_based_dns_registration": True,
            "vmc_deployment": False,
            "vtype": "CLOUD_NSXT",
        }
        json_object = json.dumps(body, indent=4)
        url = "https://" + ip + "/api/cloud"
        response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
        if response_csrf.status_code != 201:
            return None, response_csrf.text
        else:
            os.system("rm -rf newCloudInfo.json")
            with open("./newCloudInfo.json", "w") as outfile:
                json.dump(response_csrf.json(), outfile)
            return response_csrf.json()["url"], "SUCCESS"
    except Exception as e:
        return None, str(e)


def configureVcenterInNSXTCloud(ip, csrf2, cloud_url, aviVersion):
    VC_NAME = "SIVT_VC"
    url = "https://" + ip + "/api/vcenterserver"
    try:
        with open("./newCloudInfo.json", "r") as file2:
            new_cloud_json = json.load(file2)
        cloud = Cloud.CLOUD_NAME_VSPHERE.replace("vsphere", "nsxt")
        uuid = None
        try:
            uuid = new_cloud_json["uuid"]
        except Exception:
            for re in new_cloud_json["results"]:
                if re["name"] == cloud:
                    uuid = re["uuid"]
        if uuid is None:
            current_app.logger.error(cloud + " cloud not found")
            return None, cloud + "NOT_FOUND"
        get_url = "https://" + ip + "/api/vcenterserver/?cloud_ref.uuid=" + uuid
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0],
        }
        payload = {}
        response_csrf = requests.request("GET", get_url, headers=headers, data=payload, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        vc_info = {}
        found = False
        try:
            for vc in response_csrf.json()["results"]:
                if vc["name"] == VC_NAME:
                    vc_info["vcenter_url"] = vc["url"]
                    vc_info["vc_uuid"] = vc["uuid"]
                    found = True
                    break
        except Exception:
            found = False
        if found:
            cluster_url = "https://" + ip + "/api/nsxt/clusters"
            payload = {"cloud_uuid": uuid, "vcenter_uuid": vc_info["vc_uuid"]}
            payload = json.dumps(payload, indent=4)
            response_csrf = requests.request("POST", cluster_url, headers=headers, data=payload, verify=False)
            if response_csrf.status_code != 200:
                return None, response_csrf.text
            cluster_name = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterCluster"]
            for cluster in response_csrf.json()["resource"]["nsxt_clusters"]:
                if cluster["name"] == cluster_name:
                    vc_info["cluster"] = cluster["vc_mobj_id"]
                    break
            return "SUCCESS", vc_info
        else:
            cloud_connect_user, cred = createCloudConnectUser(ip, headers)
            if cloud_connect_user is None:
                return None, cred
            vcenter_credential = cred["vcenterUUId"]
            nsxt_credential = cred["nsxUUid"]
            vc_Content_Library_name = request.get_json(force=True)["envSpec"]["vcenterDetails"]["contentLibraryName"]
            if not vc_Content_Library_name:
                vc_Content_Library_name = ControllerLocation.CONTROLLER_CONTENT_LIBRARY
            library, status_lib = fetchContentLibrary(ip, headers, vcenter_credential)
            if library is None:
                return None, status_lib
            tz_id, status_tz = fetchTransportZoneId(ip, headers, nsxt_credential)
            if tz_id is None:
                return None, status_tz
            vc_id, status_vc = fetchVcenterId(ip, headers, nsxt_credential, status_tz)
            if vc_id is None:
                return None, status_vc
            payload = {
                "cloud_ref": cloud_url,
                "content_lib": {"id": status_lib, "name": vc_Content_Library_name},
                "name": VC_NAME,
                "tenant_ref": "https://" + ip + "/api/tenant/admin",
                "vcenter_credentials_ref": "https://" + ip + "/api/cloudconnectoruser/" + vcenter_credential,
                "vcenter_url": status_vc,
            }
            payload = json.dumps(payload, indent=4)
            response_csrf = requests.request("POST", url, headers=headers, data=payload, verify=False)
            if response_csrf.status_code != 201:
                return None, response_csrf.text
            vc_info["vcenter_url"] = response_csrf.json()["url"]
            vc_info["vc_uuid"] = response_csrf.json()["uuid"]
            cluster_url = "https://" + ip + "/api/nsxt/clusters"
            payload = {"cloud_uuid": uuid, "vcenter_uuid": vc_info["vc_uuid"]}
            payload = json.dumps(payload, indent=4)
            response_csrf = requests.request("POST", cluster_url, headers=headers, data=payload, verify=False)
            if response_csrf.status_code != 200:
                return None, response_csrf.text
            cluster_name = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterCluster"]
            for cluster in response_csrf.json()["resource"]["nsxt_clusters"]:
                if cluster["name"] == cluster_name:
                    vc_info["cluster"] = cluster["vc_mobj_id"]
                    break
            return "SUCCESS", vc_info
    except Exception as e:
        return None, str(e)


def createIpam_nsxtCloud(ip, csrf2, managementNetworkUrl, vipNetwork, ipam_name, aviVersion):
    try:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0],
        }
        body = {
            "internal_profile": {"usable_networks": [{"nw_ref": managementNetworkUrl}, {"nw_ref": vipNetwork}]},
            "allocate_ip_in_vrf": False,
            "type": "IPAMDNS_TYPE_INTERNAL",
            "name": ipam_name,
        }
        json_object = json.dumps(body, indent=4)
        url = "https://" + ip + "/api/ipamdnsproviderprofile"
        response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
        if response_csrf.status_code != 201:
            return None, response_csrf.text
        else:
            return response_csrf.json()["url"], response_csrf.json()["uuid"], "SUCCESS"
    except Exception as e:
        current_app.logger.error(str(e))
        return None, "Exception occurred while creation ipam profile for NSXT-T Cloud"


def createDns_nsxtCloud(ip, csrf2, dns_domain, dns_profile_name, aviVersion):
    try:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0],
        }
        body = {
            "internal_profile": {"ttl": 30, "dns_service_domain": [{"pass_through": True, "domain_name": dns_domain}]},
            "type": "IPAMDNS_TYPE_INTERNAL_DNS",
            "name": dns_profile_name,
        }
        json_object = json.dumps(body, indent=4)
        url = "https://" + ip + "/api/ipamdnsproviderprofile"
        response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
        if response_csrf.status_code != 201:
            return None, response_csrf.text
        else:
            return response_csrf.json()["url"], response_csrf.json()["uuid"], "SUCCESS"
    except Exception as e:
        current_app.logger.error(str(e))
        return None, "Exception occurred while creation DNS profile for NSXT-T Cloud "


def associate_ipam_nsxtCloud(ip, csrf2, aviVersion, nsxtCloud_uuid, ipamUrl, dnsUrl):
    try:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0],
        }
        payload = {}

        url = "https://" + ip + "/api/cloud/" + nsxtCloud_uuid
        cloud_details_response = requests.request("GET", url, headers=headers, data=payload, verify=False)
        if cloud_details_response.status_code != 200:
            return None, "Failed to fetch IPAM details for NSXT Cloud"

        # append ipam details to response
        ipam_details = {"ipam_provider_ref": ipamUrl, "dns_provider_ref": dnsUrl}
        json_response = cloud_details_response.json()
        json_response.update(ipam_details)
        json_object = json.dumps(json_response, indent=4)

        response = requests.request("PUT", url, headers=headers, data=json_object, verify=False)
        if response.status_code != 200:
            return None, response.text

        return "SUCCESS", "IPAM/DNS association with NSXT Cloud completed"
    except Exception as e:
        current_app.logger.error(str(e))
        return None, "Exception occurred during association of DNS and IPAM profile with NSX-T Cloud"


def config_orchestrated(
    env, vcenter_ip, vcenter_username, password, data_center, data_store, cluster_name, avi_version, license_type
):
    try:
        isCreated1 = create_folder(
            vcenter_ip,
            vcenter_username,
            password,
            data_center,
            ResourcePoolAndFolderName.Template_Automation_Folder.replace("vmc", "vsphere"),
        )
        if isCreated1 is not None:
            current_app.logger.info(
                "Created  folder " + ResourcePoolAndFolderName.Template_Automation_Folder.replace("vmc", "vsphere")
            )

    except Exception as e:
        current_app.logger.error("Failed to create folder " + str(e))
        d = {"responseType": "ERROR", "msg": "Failed to create folder " + str(e), "STATUS_CODE": 500}
        return jsonify(d), 500
    avi_fqdn = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController01Fqdn"]
    if isAviHaEnabled(env):
        ip = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviClusterIp"]
    else:
        ip = avi_fqdn
    if ip is None:
        current_app.logger.error("Failed to get IP of AVI controller")
        d = {"responseType": "ERROR", "msg": "Failed to get IP of AVI controller", "STATUS_CODE": 500}
        return jsonify(d), 500
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {"responseType": "ERROR", "msg": "Wrong env provided " + env[0], "STATUS_CODE": 500}
        return jsonify(d), 500
    env = env[0]
    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        current_app.logger.error("Failed to get csrf from new password")
        d = {"responseType": "ERROR", "msg": "Failed to get csrf from new password", "STATUS_CODE": 500}
        return jsonify(d), 500
    default = waitForCloudPlacementReady(ip, csrf2, "Default-Cloud", avi_version)
    if default[0] is None:
        current_app.logger.error("Failed to get default cloud status")
        d = {"responseType": "ERROR", "msg": "Failed to get default cloud status", "STATUS_CODE": 500}
        return jsonify(d), 500
    aviVersion = get_avi_version(env)
    get_cloud = getCloudStatus(ip, csrf2, aviVersion, Cloud.CLOUD_NAME.replace("vmc", "vsphere"))
    if get_cloud[0] is None:
        current_app.logger.error("Failed to get cloud status " + str(get_cloud[1]))
        d = {"responseType": "ERROR", "msg": "Failed to get cloud status " + str(get_cloud[1]), "STATUS_CODE": 500}
        return jsonify(d), 500

    isGen = False
    if get_cloud[0] == "NOT_FOUND":
        isGen = True
        for i in tqdm(range(60), desc="Waiting…", ascii=False, ncols=75):
            time.sleep(1)
        current_app.logger.info("Creating New cloud " + Cloud.CLOUD_NAME.replace("vmc", "vsphere"))
        cloud = createNewCloud_Arch(ip, csrf2, aviVersion)
        if cloud[0] is None:
            current_app.logger.error("Failed to create cloud " + str(cloud[1]))
            d = {"responseType": "ERROR", "msg": "Failed to create cloud " + str(cloud[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
        cloud_url = cloud[0]
    else:
        cloud_url = get_cloud[0]

    get_se_cloud = getSECloudStatus(ip, csrf2, aviVersion, Cloud.SE_GROUP_NAME.replace("vmc", "vsphere"))
    if get_se_cloud[0] is None:
        current_app.logger.error("Failed to get service engine cloud status " + str(get_se_cloud[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get service engine cloud status " + str(get_se_cloud[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500

    isGen = False
    if get_se_cloud[0] == "NOT_FOUND":
        isGen = True
        current_app.logger.info("Creating New se cloud " + Cloud.SE_GROUP_NAME.replace("vmc", "vsphere"))
        cloud_se = createSECloud_Arch(
            ip,
            csrf2,
            cloud_url,
            Cloud.SE_GROUP_NAME.replace("vmc", "vsphere"),
            aviVersion,
            "Mgmt",
            license_type=license_type,
        )
        if cloud_se[0] is None:
            current_app.logger.error("Failed to create service engine cloud " + str(cloud_se[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create service engine cloud " + str(cloud_se[1]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        se_cloud_url = cloud_se[0]
    else:
        se_cloud_url = get_se_cloud[0]

    data_network = request.get_json(force=True)["tkgMgmtDataNetwork"]["tkgMgmtDataNetworkName"]
    get_wip = getVipNetwork(ip, csrf2, data_network, aviVersion)
    if get_wip[0] is None:
        current_app.logger.error("Failed to get service engine VIP network " + str(get_wip[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get service engine VIP network " + str(get_wip[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500

    isGen = False
    if get_wip[0] == "NOT_FOUND":
        isGen = True
        current_app.logger.info("Creating New VIP network " + data_network)
        vip_net = createVipNetwork(ip, csrf2, cloud_url, data_network, Type.MANAGEMENT, aviVersion)
        if vip_net[0] is None:
            current_app.logger.error("Failed to create VIP network " + str(vip_net[1]))
            d = {"responseType": "ERROR", "msg": "Failed to create VIP network " + str(vip_net[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
        wip_url = vip_net[0]
        wip_cluster_url = ""
        current_app.logger.info("Created New VIP network " + data_network)
    else:
        wip_url = get_wip[0]
        wip_cluster_url = ""

    if Tkg_version.TKG_VERSION == "2.1":
        cluster_vip = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"][
            "tkgClusterVipNetworkName"
        ]
        get__cluster_wip = getVipNetwork(ip, csrf2, cluster_vip, aviVersion)
        if get__cluster_wip[0] is None:
            current_app.logger.error("Failed to get cluster VIP network " + str(get__cluster_wip[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get cluster VIP network " + str(get__cluster_wip[1]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        isGen = False
        if get__cluster_wip[0] == "NOT_FOUND":
            isGen = True
            current_app.logger.info("Creating New cluster VIP network " + cluster_vip)
            vip_net = createClusterVipNetwork(ip, csrf2, cloud_url, cluster_vip, aviVersion)
            if vip_net[0] is None:
                current_app.logger.error("Failed to create cluster VIP network " + str(vip_net[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create cluster VIP network " + str(vip_net[1]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            wip_cluster_url = vip_net[0]
            current_app.logger.info("Created New cluster VIP network " + cluster_vip)
        else:
            wip_cluster_url = get__cluster_wip[0]
    startIp = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"]["tkgClusterVipIpStartRange"]
    endIp = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"]["tkgClusterVipIpEndRange"]
    prefixIpNetmask = seperateNetmaskAndIp(
        request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"]["tkgClusterVipNetworkGatewayCidr"]
    )
    getVIPNetworkDetails = getNetworkDetailsVip(
        ip, csrf2, wip_cluster_url, startIp, endIp, prefixIpNetmask[0], prefixIpNetmask[1], aviVersion, env
    )

    if getVIPNetworkDetails[0] is None:
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get VIP network details " + str(getVIPNetworkDetails[2]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    ip_pre = getVIPNetworkDetails[2]["subnet_ip"] + "/" + str(getVIPNetworkDetails[2]["subnet_mask"])
    current_app.logger.info(ip_pre)
    with open("vip_ip.txt", "w") as e:
        e.write(ip_pre)
    get_ipam = getIpam(ip, csrf2, Cloud.IPAM_NAME.replace("vmc", "vsphere"), aviVersion)
    if get_ipam[0] is None:
        current_app.logger.error("Failed to get service engine Ipam " + str(get_ipam[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get service engine Ipam " + str(get_ipam[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500

    isGen = False
    if get_ipam[0] == "NOT_FOUND":
        isGen = True
        current_app.logger.info("Creating IPam " + Cloud.SE_GROUP_NAME.replace("vmc", "vsphere"))
        ipam = createIpam_Arch(
            ip, csrf2, wip_url, wip_cluster_url, Cloud.IPAM_NAME.replace("vmc", "vsphere"), aviVersion
        )
        if ipam[0] is None:
            current_app.logger.error("Failed to create Ipam " + str(ipam[1]))
            d = {"responseType": "ERROR", "msg": "Failed to create  ipam " + str(ipam[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
        ipam_url = ipam[0]
    else:
        ipam_url = get_ipam[0]

    new_cloud_status = getDetailsOfNewCloud_Arch(ip, csrf2, cloud_url, ipam_url, se_cloud_url, aviVersion)
    if new_cloud_status[0] is None:
        current_app.logger.error("Failed to get new cloud details" + str(new_cloud_status[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get new cloud details " + str(new_cloud_status[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    update = updateNewCloudSeGroup(ip, csrf2, cloud_url, aviVersion)
    if update[0] is None:
        current_app.logger.error("Failed to update cloud " + str(update[1]))
        d = {"responseType": "ERROR", "msg": "Failed to update cloud " + str(update[1]), "STATUS_CODE": 500}
        return jsonify(d), 500
    se_ova = generateSeOva(ip, csrf2, aviVersion, Cloud.CLOUD_NAME.replace("vmc", "vsphere"))
    if se_ova[0] is None:
        current_app.logger.error("Failed to generate service engine ova " + str(se_ova[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to generate service engine ova " + str(se_ova[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    vm_state = checkVmPresent(vcenter_ip, vcenter_username, password, ip)
    if vm_state is None:
        current_app.logger.error("AVI controller not found ")
        d = {"responseType": "ERROR", "msg": "AVI controller not found ", "STATUS_CODE": 500}
        return jsonify(d), 500
    avi_uuid = vm_state.config.uuid
    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        current_app.logger.error("Failed to get csrf from new password")
        d = {"responseType": "ERROR", "msg": "Failed to get csrf from new password", "STATUS_CODE": 500}
        return jsonify(d), 500
    se_download_ova = downloadSeOva(ip, csrf2, avi_uuid, aviVersion, Cloud.CLOUD_NAME.replace("vmc", "vsphere"))
    if se_download_ova[0] is None:
        current_app.logger.error("Failed to download service engine ova " + str(se_download_ova[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to download service engine ova " + str(se_download_ova[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    current_app.logger.info("Getting token")
    token = generateToken(ip, csrf2, aviVersion, Cloud.CLOUD_NAME.replace("vmc", "vsphere"))
    if token[0] is None:
        current_app.logger.error("Failed to get token " + str(token[1]))
        d = {"responseType": "ERROR", "msg": "Failed to  token " + str(token[1]), "STATUS_CODE": 500}
        return jsonify(d), 500
    current_app.logger.info("Get cluster uuid")
    uuid = getClusterUUid(ip, csrf2, aviVersion)
    if uuid[0] is None:
        current_app.logger.error("Failed to get cluster uuid " + str(uuid[1]))
        d = {"responseType": "ERROR", "msg": "Failed to get cluster uuid " + str(uuid[1]), "STATUS_CODE": 500}
        return jsonify(d), 500

    clo = Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE
    get_se_cloud_workload = getSECloudStatus(ip, csrf2, aviVersion, clo)
    if get_se_cloud_workload[0] is None:
        current_app.logger.error("Failed to get service engine cloud status " + str(get_se_cloud_workload[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get se cloud status " + str(get_se_cloud_workload[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500

    isGen = False
    if get_se_cloud_workload[0] == "NOT_FOUND":
        isGen = True
        current_app.logger.info("Creating New service engine cloud " + clo)
        cloud_se_workload = createSECloud_Arch(
            ip, csrf2, cloud_url, clo, aviVersion, "Workload", license_type=license_type
        )
        if cloud_se_workload[0] is None:
            current_app.logger.error("Failed to create service engine cloud " + str(cloud_se_workload[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create service engine cloud " + str(cloud_se_workload[1]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        se_cloud_url_workload = cloud_se_workload[0]
    else:
        se_cloud_url_workload = get_se_cloud_workload[0]
    current_app.logger.info(f"SE workload cloud url {se_cloud_url_workload}")
    replaceNetworkValues(ip, token[0], uuid[0], "./vsphere/managementConfig/importSeOva-vc.json")
    vm_state = checkVmPresent(
        vcenter_ip,
        vcenter_username,
        password,
        ControllerLocation.SE_OVA_TEMPLATE_NAME.replace("vmc", "vsphere") + "_" + avi_uuid,
    )
    if vm_state is None:
        try:
            destroy_vm(
                getSi(vcenter_ip, vcenter_username, password),
                ResourcePoolAndFolderName.Template_Automation_Folder,
                data_center,
                ControllerLocation.SE_OVA_TEMPLATE_NAME.replace("vmc", "vsphere"),
            )
        except Exception as e:
            current_app.logger.info(e)
            pass
    if vm_state is None:
        current_app.logger.info("Pushing ova and marking it as template..")
        push = pushSeOvaToVcenter(
            vcenter_ip, vcenter_username, password, data_center, data_store, cluster_name, avi_uuid
        )
        if push[0] is None:
            current_app.logger.error("Failed to push service engine ova to vcenter " + str(push[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to push service engine ova to vcenter " + str(push[1]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
    else:
        current_app.logger.info("Service engine ova is already pushed to the vcenter")
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
        "./vsphere/managementConfig/se.json",
        "detailsOfServiceEngine1.json",
        "detailsOfServiceEngine2.json",
        ControllerLocation.CONTROLLER_SE_NAME.replace("vmc", "vsphere"),
        ControllerLocation.CONTROLLER_SE_NAME2.replace("vmc", "vsphere"),
        1,
        Type.MANAGEMENT,
        0,
        aviVersion,
    )
    if dep[1] != 200:
        current_app.logger.error("Controller deployment failed" + str(dep[0]))
        d = {"responseType": "ERROR", "msg": "Controller deployment failed " + str(dep[0]), "STATUS_CODE": 500}
        return jsonify(d), 500
    current_app.logger.debug(f"Gen {isGen}")
    current_app.logger.info("Configured management cluster successfully")
    d = {"responseType": "SUCCESS", "msg": "Configured management cluster successfully", "STATUS_CODE": 200}
    return jsonify(d), 200


def controllerDeployment(
    ip,
    csrf2,
    data_center,
    data_store,
    cluster_name,
    vcenter_ip,
    vcenter_username,
    password,
    se_cloud_url,
    seJson,
    detailsJson1,
    detailsJson2,
    controllerName1,
    controllerName2,
    seCount,
    type,
    name,
    aviVersion,
):
    isDeployed = False
    env = envCheck()
    env = env[0]
    current_app.logger.info("Checking controller 1")
    vm_state_se = checkVmPresent(vcenter_ip, vcenter_username, password, controllerName1)
    if vm_state_se is None:
        current_app.logger.info("Getting token")
        token = generateToken(ip, csrf2, aviVersion, Cloud.CLOUD_NAME.replace("vmc", "vsphere"))
        if token[0] is None:
            current_app.logger.error("Failed to get token " + str(token[1]))
            d = {"responseType": "ERROR", "msg": "Failed to  token " + str(token[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
        current_app.logger.info("Get cluster uuid")
        uuid = getClusterUUid(ip, csrf2, aviVersion)
        if uuid[0] is None:
            current_app.logger.error("Failed to get cluster uuid " + str(uuid[1]))
            d = {"responseType": "ERROR", "msg": "Failed to get cluster uuid " + str(uuid[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
        if type == Type.WORKLOAD:
            replaceNetworkValuesWorkload(ip, token[0], uuid[0], seJson)
        else:
            replaceNetworkValues(ip, token[0], uuid[0], seJson)
        deploy_se = deploySeEngines(
            vcenter_ip,
            vcenter_username,
            password,
            ip,
            token[0],
            uuid[0],
            data_center,
            data_store,
            cluster_name,
            seJson,
            controllerName1,
            type,
        )
        if deploy_se[0] != "SUCCESS":
            current_app.logger.error("Failed to deploy service engine ova to vcenter " + str(deploy_se[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to deploy service engine ova to vcenter " + str(deploy_se[0]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        isDeployed = True
    count = 0
    found = False
    seIp1 = None
    while count < 120:
        try:
            current_app.logger.info("Waited " + str(10 * count) + "s to get controller 1 ip, retrying")
            seIp1 = checkforIpAddress(getSi(vcenter_ip, vcenter_username, password), controllerName1)
            if seIp1 is not None:
                found = True
                break
        except Exception:
            pass
        time.sleep(10)
        count = count + 1

    if not found:
        current_app.logger.error("Controller 1 is not up failed to get ip ")
        d = {"responseType": "ERROR", "msg": "Controller 1 is not up ", "STATUS_CODE": 500}
        return jsonify(d), 500
    current_app.logger.info("Checking controller 2")
    vm_state_se2 = checkVmPresent(vcenter_ip, vcenter_username, password, controllerName2)
    if vm_state_se2 is None:
        current_app.logger.info("Getting token")
        token = generateToken(ip, csrf2, aviVersion, Cloud.CLOUD_NAME.replace("vmc", "vsphere"))
        if token[0] is None:
            current_app.logger.error("Failed to get token " + str(token[0]))
            d = {"responseType": "ERROR", "msg": "Failed to  token " + str(token[0]), "STATUS_CODE": 500}
            return jsonify(d), 500
        current_app.logger.info("Get cluster uuid")
        uuid = getClusterUUid(ip, csrf2, aviVersion)
        if uuid[0] is None:
            current_app.logger.error("Failed to get cluster uuid " + str(uuid[0]))
            d = {"responseType": "ERROR", "msg": "Failed to get cluster uuid " + str(uuid[0]), "STATUS_CODE": 500}
            return jsonify(d), 500
        replaceNetworkValues(ip, token[0], uuid[0], seJson)
        deploy_se2 = deploySeEngines(
            vcenter_ip,
            vcenter_username,
            password,
            ip,
            token[0],
            uuid[0],
            data_center,
            data_store,
            cluster_name,
            seJson,
            controllerName2,
            type,
        )
        if deploy_se2[0] != "SUCCESS":
            current_app.logger.error("Failed to deploy 2nd service engine ova to vcenter " + str(deploy_se2[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to deploy 2nd service engine ova to vcenter " + str(deploy_se2[0]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        isDeployed = True
    count2 = 0
    found2 = False
    seIp2 = None
    while count2 < 120:
        try:
            current_app.logger.info("Waited " + str(10 * count2) + "s to get controller 2 ip, retrying")
            seIp2 = checkforIpAddress(getSi(vcenter_ip, vcenter_username, password), controllerName2)
            if seIp2 is not None:
                found2 = True
                break
        except Exception:
            pass
        time.sleep(10)
        count2 = count2 + 1

    if not found2:
        current_app.logger.error("Controller 2 is not up, failed to get ip ")
        d = {"responseType": "ERROR", "msg": "Controller 2 is not up ", "STATUS_CODE": 500}
        return jsonify(d), 500
    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        current_app.logger.error("Failed to get csrf from new set password")
        d = {"responseType": "ERROR", "msg": "Failed to get csrf from new set password", "STATUS_CODE": 500}
        return jsonify(d), 500
    urlFromServiceEngine1 = listAllServiceEngine(
        ip, csrf2, seCount, seIp1, controllerName1, vcenter_ip, vcenter_username, password, aviVersion
    )
    if urlFromServiceEngine1[0] is None:
        current_app.logger.error("Failed to get service engine details" + str(urlFromServiceEngine1[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get service engine details " + str(urlFromServiceEngine1[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    urlFromServiceEngine2 = listAllServiceEngine(
        ip, csrf2, seCount, seIp2, controllerName2, vcenter_ip, vcenter_username, password, aviVersion
    )
    if urlFromServiceEngine2[0] is None:
        current_app.logger.error("Failed to get service engine details" + str(urlFromServiceEngine2[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get service engine details " + str(urlFromServiceEngine2[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    details1 = getDetailsOfServiceEngine(ip, csrf2, urlFromServiceEngine1[0], detailsJson1, aviVersion)
    if details1[0] is None:
        current_app.logger.error("Failed to get details of engine 1" + str(details1[1]))
        d = {"responseType": "ERROR", "msg": "Failed to get details of engine 1" + str(details1[1]), "STATUS_CODE": 500}
        return jsonify(d), 500
    details2 = getDetailsOfServiceEngine(ip, csrf2, urlFromServiceEngine2[0], detailsJson2, aviVersion)
    if details2[0] is None:
        current_app.logger.error("Failed to get details of engine 2 " + str(details2[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get details of engine 2 " + str(details2[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500

    se_engines = changeSeGroupAndSetInterfaces(
        ip,
        csrf2,
        urlFromServiceEngine1[0],
        se_cloud_url,
        detailsJson1,
        vcenter_ip,
        vcenter_username,
        password,
        controllerName1,
        type,
        name,
        aviVersion,
    )
    if se_engines[0] is None:
        current_app.logger.error("Failed to change set interfaces engine 1" + str(se_engines[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to  change set interfaces engine 1" + str(se_engines[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    se_engines2 = changeSeGroupAndSetInterfaces(
        ip,
        csrf2,
        urlFromServiceEngine2[0],
        se_cloud_url,
        detailsJson2,
        vcenter_ip,
        vcenter_username,
        password,
        controllerName2,
        type,
        name,
        aviVersion,
    )
    if se_engines2[0] is None:
        current_app.logger.error("Failed to change set interfaces engine 2" + str(se_engines2[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to change set interfaces engine2 " + str(se_engines2[1]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    listOfServiceEngine = [urlFromServiceEngine1[0], urlFromServiceEngine2[0]]
    for i in listOfServiceEngine:
        current_app.logger.info("Getting status of service engine " + i)
        s = getConnectedStatus(ip, csrf2, i, aviVersion)
        if s[0] is None or s[0] == "FAILED":
            current_app.logger.error("Failed to get connected status of engine " + str(s[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get connected status of engine " + str(s[1]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        current_app.logger.info("Service engine " + i + " is connected")
    try:
        checkforIpAddress(getSi(vcenter_ip, vcenter_username, password), controllerName1)
        checkforIpAddress(getSi(vcenter_ip, vcenter_username, password), controllerName2)
    except Exception as e:
        current_app.logger.error(e)
        d = {"responseType": "ERROR", "msg": e, "STATUS_CODE": 500}
        return jsonify(d), 500
    with open("./newCloudInfo.json", "r") as file2:
        new_cloud_json = json.load(file2)
    uuid = None
    try:
        uuid = new_cloud_json["uuid"]
    except Exception:
        for re in new_cloud_json["results"]:
            if re["name"] == Cloud.CLOUD_NAME.replace("vmc", "vsphere"):
                uuid = re["uuid"]
    if uuid is None:
        return None, "NOT_FOUND"
    if type == Type.WORKLOAD:
        ipNetMask = seperateNetmaskAndIp(
            request.get_json(force=True)["tkgWorkloadDataNetwork"]["tkgWorkloadDataNetworkGatewayCidr"]
        )
    else:
        ipNetMask = seperateNetmaskAndIp(
            request.get_json(force=True)["tkgMgmtDataNetwork"]["tkgMgmtDataNetworkGatewayCidr"]
        )
        ipNetMask_ = seperateNetmaskAndIp(
            request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"]["tkgClusterVipNetworkGatewayCidr"]
        )
        vrf = getVrfAndNextRoutId(ip, csrf2, uuid, VrfType.GLOBAL, ipNetMask_[0], aviVersion)
        if vrf[0] is None or vrf[1] == "NOT_FOUND":
            current_app.logger.error("Vrf not found " + str(vrf[1]))
            d = {"responseType": "ERROR", "msg": "Vrf not found " + str(vrf[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
        if vrf[1] != "Already_Configured":
            current_app.logger.info("Routing is not configured , configuring.")
            ad = addStaticRoute(ip, csrf2, vrf[0], ipNetMask_[0], vrf[1], aviVersion)
            if ad[0] is None:
                current_app.logger.error("Failed to add static route " + str(ad[1]))
                d = {"responseType": "ERROR", "msg": "Vrf not found " + str(ad[1]), "STATUS_CODE": 500}
                return jsonify(d), 500
            current_app.logger.info("Routing is configured.")
    vrf = getVrfAndNextRoutId(ip, csrf2, uuid, VrfType.GLOBAL, ipNetMask[0], aviVersion)
    if vrf[0] is None or vrf[1] == "NOT_FOUND":
        current_app.logger.error("Vrf not found " + str(vrf[1]))
        d = {"responseType": "ERROR", "msg": "Vrf not found " + str(vrf[1]), "STATUS_CODE": 500}
        return jsonify(d), 500
    if vrf[1] != "Already_Configured":
        current_app.logger.info("Routing is not configured , configuring.")
        ad = addStaticRoute(ip, csrf2, vrf[0], ipNetMask[0], vrf[1], aviVersion)
        if ad[0] is None:
            current_app.logger.error("Failed to add static route " + str(ad[1]))
            d = {"responseType": "ERROR", "msg": "Vrf not found " + str(ad[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
        current_app.logger.info("Routing is configured.")
    current_app.logger.debug(f"is deployed. {isDeployed}")
    d = {"responseType": "SUCCESS", "msg": "Deployment Successful", "STATUS_CODE": 200}
    return jsonify(d), 200


def pushSeOvaToVcenter(vcenter_ip, vcenter_username, password, data_center, data_store, cluster_name, avi_uuid):
    os.putenv("GOVC_URL", "https://" + vcenter_ip + "/sdk")
    os.putenv("GOVC_USERNAME", vcenter_username)
    os.putenv("GOVC_PASSWORD", password)
    os.putenv("GOVC_INSECURE", "true")
    parent_resourcepool = current_app.config["RESOURCE_POOL"]
    if parent_resourcepool is not None:
        rp_pool = (
            data_center
            + "/host/"
            + cluster_name
            + "/Resources/"
            + parent_resourcepool
            + "/"
            + ResourcePoolAndFolderName.AVI_RP.replace("vmc", "vsphere")
        )
    else:
        rp_pool = (
            data_center
            + "/host/"
            + cluster_name
            + "/Resources/"
            + ResourcePoolAndFolderName.AVI_RP.replace("vmc", "vsphere")
        )
    replaceValueSysConfig(
        "./vsphere/managementConfig/importSeOva-vc.json",
        "Name",
        "name",
        ControllerLocation.SE_OVA_TEMPLATE_NAME.replace("vmc", "vsphere") + "_" + avi_uuid,
    )
    ova_deploy_command = [
        "govc",
        "import.ova",
        "-options",
        "./vsphere/managementConfig/importSeOva-vc.json",
        "-dc=" + data_center,
        "-ds=" + data_store,
        "-folder=" + ResourcePoolAndFolderName.Template_Automation_Folder.replace("vmc", "vsphere"),
        "-pool=/" + rp_pool,
        current_app.config["se_ova_path"],
    ]
    try:
        runProcess(ova_deploy_command)
    except Exception as e:
        return None, str(e)
    return "SUCCESS", 200


def replaceNetworkValues(ip, aviAuthToken, clusterUUid, file_name):
    tkg_management = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtNetworkName"]
    avi_management = request.get_json(force=True)["tkgComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkName"]
    avi_data_pg = request.get_json(force=True)["tkgMgmtDataNetwork"]["tkgMgmtDataNetworkName"]
    tkg_cluster_vip_name = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"][
        "tkgClusterVipNetworkName"
    ]
    property_mapping = {"AVICNTRL": ip, "AVICNTRL_AUTHTOKEN": aviAuthToken, "AVICNTRL_CLUSTERUUID": clusterUUid}
    for key, value in property_mapping.items():
        replaceSe(file_name, "PropertyMapping", key, "Key", "Value", value)
    if Tkg_version.TKG_VERSION == "2.1":
        dictionary_network = {
            "Management": avi_management,
            "Data Network 1": avi_data_pg,
            "Data Network 2": tkg_management,
            "Data Network 3": tkg_management,
            "Data Network 4": tkg_cluster_vip_name,
            "Data Network 5": tkg_management,
            "Data Network 6": tkg_management,
            "Data Network 7": tkg_management,
            "Data Network 8": tkg_management,
            "Data Network 9": tkg_management,
        }
    else:
        dictionary_network = {
            "Management": "",
            "Data Network 1": "",
            "Data Network 2": tkg_management,
            "Data Network 3": "",
            "Data Network 4": "",
            "Data Network 5": "",
            "Data Network 6": "",
            "Data Network 7": "",
            "Data Network 8": "",
            "Data Network 9": "",
        }
    for key, value in dictionary_network.items():
        replaceSe(file_name, "NetworkMapping", key, "Name", "Network", value)


def createSECloud_Arch(ip, csrf2, newCloudUrl, seGroupName, aviVersion, se_name_prefix, license_type="enterprise"):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    json_object = getNewBody(newCloudUrl, seGroupName, se_name_prefix, license_type=license_type)
    url = "https://" + ip + "/api/serviceenginegroup"
    response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        return response_csrf.json()["url"], "SUCCESS"


def getNewBody(newCloudUrl, seGroupName, se_name_prefix, license_type):
    enterprise_body = {
        "ha_mode": "HA_MODE_SHARED_PAIR",
        "hm_on_standby": True,
        "dedicated_dispatcher_core": False,
        "disable_gro": True,
        "self_se_election": True,
        "objsync_config": {"objsync_cpu_limit": 30, "objsync_reconcile_interval": 10, "objsync_hub_elect_interval": 60},
        "app_cache_percent": 10,
        "license_tier": "ENTERPRISE",
    }
    essentials_body = {
        "ha_mode": "HA_MODE_LEGACY_ACTIVE_STANDBY",
        "hm_on_standby": False,
        "self_se_election": False,
        "app_cache_percent": 0,
        "license_tier": "ESSENTIALS",
    }
    body = {
        "max_vs_per_se": 10,
        "min_scaleout_per_vs": 2,
        "max_scaleout_per_vs": 4,
        "max_se": 10,
        "vcpus_per_se": 1,
        "memory_per_se": 2048,
        "disk_per_se": 15,
        "max_cpu_usage": 80,
        "min_cpu_usage": 30,
        "se_deprovision_delay": 120,
        "auto_rebalance": False,
        "se_name_prefix": se_name_prefix,
        "vs_host_redundancy": True,
        "vcenter_folder": "AviSeFolder",
        "vcenter_datastores_include": False,
        "vcenter_datastore_mode": "VCENTER_DATASTORE_ANY",
        "cpu_reserve": False,
        "mem_reserve": True,
        "algo": "PLACEMENT_ALGO_PACKED",
        "buffer_se": 0,
        "active_standby": False,
        "placement_mode": "PLACEMENT_MODE_AUTO",
        "se_dos_profile": {"thresh_period": 5},
        "auto_rebalance_interval": 300,
        "aggressive_failure_detection": False,
        "realtime_se_metrics": {"enabled": False, "duration": 30},
        "vs_scaleout_timeout": 600,
        "vs_scalein_timeout": 30,
        "connection_memory_percentage": 50,
        "extra_config_multiplier": 0,
        "vs_scalein_timeout_for_upgrade": 30,
        "log_disksz": 10000,
        "os_reserved_memory": 0,
        "per_app": False,
        "distribute_load_active_standby": False,
        "auto_redistribute_active_standby_load": False,
        "cpu_socket_affinity": False,
        "num_flow_cores_sum_changes_to_ignore": 8,
        "least_load_core_selection": True,
        "extra_shared_config_memory": 0,
        "se_tunnel_mode": 0,
        "se_vs_hb_max_vs_in_pkt": 256,
        "se_vs_hb_max_pkts_in_batch": 64,
        "se_thread_multiplier": 1,
        "async_ssl": False,
        "async_ssl_threads": 1,
        "se_udp_encap_ipc": 0,
        "se_tunnel_udp_port": 1550,
        "archive_shm_limit": 8,
        "significant_log_throttle": 100,
        "udf_log_throttle": 100,
        "non_significant_log_throttle": 100,
        "ingress_access_mgmt": "SG_INGRESS_ACCESS_ALL",
        "ingress_access_data": "SG_INGRESS_ACCESS_ALL",
        "se_sb_dedicated_core": False,
        "se_probe_port": 7,
        "se_sb_threads": 1,
        "ignore_rtt_threshold": 5000,
        "waf_mempool": True,
        "waf_mempool_size": 64,
        "host_gateway_monitor": False,
        "vss_placement": {"num_subcores": 4, "core_nonaffinity": 2},
        "flow_table_new_syn_max_entries": 0,
        "disable_csum_offloads": False,
        "disable_tso": False,
        "enable_hsm_priming": False,
        "distribute_queues": False,
        "vss_placement_enabled": False,
        "enable_multi_lb": False,
        "n_log_streaming_threads": 1,
        "free_list_size": 1024,
        "max_rules_per_lb": 150,
        "max_public_ips_per_lb": 30,
        "minimum_connection_memory": 20,
        "shm_minimum_config_memory": 4,
        "heap_minimum_config_memory": 8,
        "disable_se_memory_check": False,
        "memory_for_config_update": 15,
        "num_dispatcher_cores": 0,
        "ssl_preprocess_sni_hostname": True,
        "se_dpdk_pmd": 0,
        "se_use_dpdk": 0,
        "min_se": 1,
        "se_pcap_reinit_frequency": 0,
        "se_pcap_reinit_threshold": 0,
        "disable_avi_securitygroups": False,
        "se_flow_probe_retries": 2,
        "vs_switchover_timeout": 300,
        "config_debugs_on_all_cores": False,
        "vs_se_scaleout_ready_timeout": 60,
        "vs_se_scaleout_additional_wait_time": 0,
        "se_dp_hm_drops": 0,
        "disable_flow_probes": False,
        "dp_aggressive_hb_frequency": 100,
        "dp_aggressive_hb_timeout_count": 10,
        "bgp_state_update_interval": 60,
        "max_memory_per_mempool": 64,
        "app_learning_memory_percent": 0,
        "datascript_timeout": 1000000,
        "se_pcap_lookahead": False,
        "enable_gratarp_permanent": False,
        "gratarp_permanent_periodicity": 10,
        "reboot_on_panic": True,
        "se_flow_probe_retry_timer": 40,
        "se_lro": True,
        "se_tx_batch_size": 64,
        "se_pcap_pkt_sz": 69632,
        "se_pcap_pkt_count": 0,
        "distribute_vnics": False,
        "se_dp_vnic_queue_stall_event_sleep": 0,
        "se_dp_vnic_queue_stall_timeout": 10000,
        "se_dp_vnic_queue_stall_threshold": 2000,
        "se_dp_vnic_restart_on_queue_stall_count": 3,
        "se_dp_vnic_stall_se_restart_window": 3600,
        "se_pcap_qdisc_bypass": True,
        "se_rum_sampling_nav_percent": 1,
        "se_rum_sampling_res_percent": 100,
        "se_rum_sampling_nav_interval": 1,
        "se_rum_sampling_res_interval": 2,
        "se_kni_burst_factor": 0,
        "max_queues_per_vnic": 1,
        "se_rl_prop": {"msf_num_stages": 1, "msf_stage_size": 16384},
        "app_cache_threshold": 5,
        "core_shm_app_learning": False,
        "core_shm_app_cache": False,
        "pcap_tx_mode": "PCAP_TX_AUTO",
        "se_dp_max_hb_version": 2,
        "resync_time_interval": 65536,
        "use_hyperthreaded_cores": True,
        "se_hyperthreaded_mode": "SE_CPU_HT_AUTO",
        "compress_ip_rules_for_each_ns_subnet": True,
        "se_vnic_tx_sw_queue_size": 256,
        "se_vnic_tx_sw_queue_flush_frequency": 0,
        "transient_shared_memory_max": 30,
        "log_malloc_failure": True,
        "se_delayed_flow_delete": True,
        "se_txq_threshold": 2048,
        "se_mp_ring_retry_count": 500,
        "dp_hb_frequency": 100,
        "dp_hb_timeout_count": 10,
        "pcap_tx_ring_rd_balancing_factor": 10,
        "use_objsync": True,
        "se_ip_encap_ipc": 0,
        "se_l3_encap_ipc": 0,
        "handle_per_pkt_attack": True,
        "per_vs_admission_control": False,
        "objsync_port": 9001,
        "se_dp_isolation": False,
        "se_dp_isolation_num_non_dp_cpus": 0,
        "cloud_ref": newCloudUrl,
        "vcenter_datastores": [],
        "service_ip_subnets": [],
        "auto_rebalance_criteria": [],
        "auto_rebalance_capacity_per_se": [],
        "license_type": "LIC_CORES",
        "se_bandwidth_type": "SE_BANDWIDTH_UNLIMITED",
        "name": seGroupName,
    }
    body_update = essentials_body if license_type == "essentials" else enterprise_body
    body.update(body_update)
    return json.dumps(body, indent=4)


def createVipNetwork(ip, csrf2, newCloudUrl, name, type, aviVersion):
    if type == Type.WORKLOAD:
        ipNetMask = seperateNetmaskAndIp(
            request.get_json(force=True)["tkgWorkloadDataNetwork"]["tkgWorkloadDataNetworkGatewayCidr"]
        )
        start_ip = request.get_json(force=True)["tkgWorkloadDataNetwork"]["tkgWorkloadAviServiceIpStartRange"]
        end_ip = request.get_json(force=True)["tkgWorkloadDataNetwork"]["tkgWorkloadAviServiceIpEndRange"]
    else:
        ipNetMask = seperateNetmaskAndIp(
            request.get_json(force=True)["tkgMgmtDataNetwork"]["tkgMgmtDataNetworkGatewayCidr"]
        )
        start_ip = request.get_json(force=True)["tkgMgmtDataNetwork"]["tkgMgmtAviServiceIpStartRange"]
        end_ip = request.get_json(force=True)["tkgMgmtDataNetwork"]["tkgMgmtAviServiceIpEndRange"]
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    body = {
        "name": name,
        "vcenter_dvs": True,
        "dhcp_enabled": False,
        "exclude_discovered_subnets": False,
        "synced_from_se": False,
        "ip6_autocfg_enabled": False,
        "cloud_ref": newCloudUrl,
        "configured_subnets": [
            {
                "prefix": {"ip_addr": {"addr": ipNetMask[0], "type": "V4"}, "mask": ipNetMask[1]},
                "static_ip_ranges": [
                    {
                        "range": {"begin": {"addr": start_ip, "type": "V4"}, "end": {"addr": end_ip, "type": "V4"}},
                        "type": "STATIC_IPS_FOR_VIP_AND_SE",
                    }
                ],
            }
        ],
    }
    json_object = json.dumps(body, indent=4)
    url = "https://" + ip + "/api/network"
    response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        return response_csrf.json()["url"], "SUCCESS"


def createClusterVipNetwork(ip, csrf2, newCloudUrl, name, aviVersion):
    ipNetMask = seperateNetmaskAndIp(
        request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"]["tkgClusterVipNetworkGatewayCidr"]
    )
    start_ip = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"]["tkgClusterVipIpStartRange"]
    end_ip = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"]["tkgClusterVipIpEndRange"]
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    body = {
        "name": name,
        "vcenter_dvs": True,
        "dhcp_enabled": False,
        "exclude_discovered_subnets": False,
        "synced_from_se": False,
        "ip6_autocfg_enabled": False,
        "cloud_ref": newCloudUrl,
        "configured_subnets": [
            {
                "prefix": {"ip_addr": {"addr": ipNetMask[0], "type": "V4"}, "mask": ipNetMask[1]},
                "static_ip_ranges": [
                    {
                        "range": {"begin": {"addr": start_ip, "type": "V4"}, "end": {"addr": end_ip, "type": "V4"}},
                        "type": "STATIC_IPS_FOR_VIP_AND_SE",
                    }
                ],
            }
        ],
    }
    json_object = json.dumps(body, indent=4)
    url = "https://" + ip + "/api/network"
    response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        return response_csrf.json()["url"], "SUCCESS"


def createIpam_Arch(ip, csrf2, vipNetworkUrl, clusterVip, name, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    if Tkg_version.TKG_VERSION == "1.3":
        body = {
            "name": name,
            "internal_profile": {"ttl": 30, "usable_networks": [{"nw_ref": vipNetworkUrl}]},
            "allocate_ip_in_vrf": False,
            "type": "IPAMDNS_TYPE_INTERNAL",
            "gcp_profile": {"match_se_group_subnet": False, "use_gcp_network": False},
            "azure_profile": {"use_enhanced_ha": False, "use_standard_alb": False},
        }
    elif Tkg_version.TKG_VERSION == "2.1":
        body = {
            "name": name,
            "internal_profile": {"ttl": 30, "usable_networks": [{"nw_ref": vipNetworkUrl}, {"nw_ref": clusterVip}]},
            "allocate_ip_in_vrf": False,
            "type": "IPAMDNS_TYPE_INTERNAL",
            "gcp_profile": {"match_se_group_subnet": False, "use_gcp_network": False},
            "azure_profile": {"use_enhanced_ha": False, "use_standard_alb": False},
        }
    json_object = json.dumps(body, indent=4)
    url = "https://" + ip + "/api/ipamdnsproviderprofile"
    response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        return response_csrf.json()["url"], "SUCCESS"


def getDetailsOfNewCloud_Arch(ip, csrf2, newCloudUrl, newIpamUrl, seGroupUrl, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    payload = {}
    url = newCloudUrl
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        json_object = json.dumps(response_csrf.json(), indent=4)
        os.system("rm -rf detailsOfNewCloud.json")
        with open("./detailsOfNewCloud.json", "w") as outfile:
            outfile.write(json_object)
        replaceValueSysConfig("detailsOfNewCloud.json", "ipam_provider_ref", "name", newIpamUrl)
        replaceValueSysConfig("detailsOfNewCloud.json", "se_group_template_ref", "name", seGroupUrl)
        return response_csrf.json(), "SUCCESS"


def replaceNetworkValuesWorkload(ip, aviAuthToken, clusterUUid, file_name):
    tkg_management = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtNetworkName"]
    avi_management = request.get_json(force=True)["tkgComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkName"]
    avi_data_pg = request.get_json(force=True)["tkgMgmtDataNetwork"]["tkgMgmtDataNetworkName"]
    tkg_cluster_vip_name = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"][
        "tkgClusterVipNetworkName"
    ]
    workload_vip = request.get_json(force=True)["tkgWorkloadDataNetwork"]["tkgWorkloadDataNetworkName"]
    property_mapping = {"AVICNTRL": ip, "AVICNTRL_AUTHTOKEN": aviAuthToken, "AVICNTRL_CLUSTERUUID": clusterUUid}
    for key, value in property_mapping.items():
        replaceSe(file_name, "PropertyMapping", key, "Key", "Value", value)
    dictionary_network = {
        "Management": avi_management,
        "Data Network 1": avi_data_pg,
        "Data Network 2": tkg_management,
        "Data Network 3": tkg_management,
        "Data Network 4": tkg_cluster_vip_name,
        "Data Network 5": workload_vip,
        "Data Network 6": tkg_management,
        "Data Network 7": tkg_management,
        "Data Network 8": tkg_management,
        "Data Network 9": tkg_management,
    }
    for key, value in dictionary_network.items():
        replaceSe(file_name, "NetworkMapping", key, "Name", "Network", value)


def deploySeEngines(
    vcenter_ip,
    vcenter_username,
    password,
    ip,
    aviAuthToken,
    clusterUUid,
    data_center,
    data_store,
    cluster_name,
    file_name,
    engine_name,
    type,
):
    os.putenv("GOVC_URL", "https://" + vcenter_ip + "/sdk")
    os.putenv("GOVC_USERNAME", vcenter_username)
    os.putenv("GOVC_PASSWORD", password)
    os.putenv("GOVC_INSECURE", "true")
    replaceValueSysConfig(file_name, "Name", "name", engine_name)
    if type == Type.WORKLOAD:
        replaceNetworkValuesWorkload(ip, aviAuthToken, clusterUUid, file_name)
    else:
        replaceNetworkValues(ip, aviAuthToken, clusterUUid, file_name)
    parent_resourcepool = current_app.config["RESOURCE_POOL"]
    if parent_resourcepool is not None:
        rp_pool = (
            data_center
            + "/host/"
            + cluster_name
            + "/Resources/"
            + parent_resourcepool
            + "/"
            + ResourcePoolAndFolderName.AVI_RP.replace("vmc", "vsphere")
        )
    else:
        rp_pool = (
            data_center
            + "/host/"
            + cluster_name
            + "/Resources/"
            + ResourcePoolAndFolderName.AVI_RP.replace("vmc", "vsphere")
        )
    ova_deploy_command = [
        "govc",
        "import.ova",
        "-options",
        file_name,
        "-dc=" + data_center,
        "-ds=" + data_store,
        "-folder=" + ResourcePoolAndFolderName.AVI_Components_FOLDER.replace("vmc", "vsphere"),
        "-pool=/" + rp_pool,
        current_app.config["se_ova_path"],
    ]
    if type == Type.WORKLOAD:
        network_connect = ["govc", "device.connect", "-vm", engine_name, "ethernet-0", "ethernet-1", "ethernet-5"]
        network_disconnect = [
            "govc",
            "device.disconnect",
            "-vm",
            engine_name,
            "ethernet-2",
            "ethernet-3",
            "ethernet-4",
            "ethernet-6",
            "ethernet-7",
            "ethernet-8",
            "ethernet-9",
        ]

    else:
        if Tkg_version.TKG_VERSION == "2.1":
            network_connect = [
                "govc",
                "device.connect",
                "-vm",
                engine_name,
                "ethernet-0",
                "ethernet-1",
                "ethernet-2",
                "ethernet-4",
            ]
            network_disconnect = [
                "govc",
                "device.disconnect",
                "-vm",
                engine_name,
                "ethernet-5",
                "ethernet-3",
                "ethernet-6",
                "ethernet-7",
                "ethernet-8",
                "ethernet-9",
            ]
        else:
            network_connect = [
                "govc",
                "device.connect",
                "-vm",
                engine_name,
                "ethernet-0",
                "ethernet-1",
                "ethernet-2",
                "ethernet-3",
            ]
            network_disconnect = [
                "govc",
                "device.disconnect",
                "-vm",
                engine_name,
                "ethernet-4",
                "ethernet-5",
                "ethernet-6",
                "ethernet-7",
                "ethernet-8",
                "ethernet-9",
            ]
    change_VM_config = ["govc", "vm.change", "-vm=" + engine_name, "-c=2", "-m=4096"]
    power_on = ["govc", "vm.power", "-on=true", engine_name]
    try:
        current_app.logger.info("Deploying se engine " + engine_name)
        runShellCommandWithPolling(ova_deploy_command)
        time.sleep(10)
        runShellCommandWithPolling(network_connect)
        runShellCommandWithPolling(network_disconnect)
        runShellCommandWithPolling(change_VM_config)
        runShellCommandWithPolling(power_on)
    except Exception as e:
        return str(e), 500

    return "SUCCESS", 200


def listAllServiceEngine(ip, csrf2, countSe, name, controllerName, vcenter_ip, vcenter_username, password, aviVersion):
    with open("./newCloudInfo.json", "r") as file2:
        new_cloud_json = json.load(file2)
    uuid = None
    try:
        uuid = new_cloud_json["uuid"]
    except Exception:
        for re in new_cloud_json["results"]:
            if re["name"] == Cloud.CLOUD_NAME.replace("vmc", "vsphere"):
                uuid = re["uuid"]
    if uuid is None:
        return None, "Failed", "ERROR"
    url = "https://" + ip + "/api/serviceengine-inventory/?cloud_ref.uuid=" + str(uuid)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    payload = {}
    count = 0
    response_csrf = None
    while count < 60:
        try:
            isThere = False
            try:
                name = checkforIpAddress(getSi(vcenter_ip, vcenter_username, password), controllerName)
            except Exception:
                pass
            current_app.logger.info("Waited for " + str(count * 10) + "s retrying")
            response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
            if response_csrf.status_code == 200:
                if response_csrf.json()["count"] > countSe:
                    for se in response_csrf.json()["results"]:
                        if str(se["config"]["name"]).strip() == str(name).strip():
                            isThere = True
                            break
                if isThere:
                    break
            count = count + 1
            time.sleep(10)
        except Exception:
            pass
    if response_csrf is None:
        current_app.logger.info("Waited for " + str(count * 10) + "s but service engine is not up")
        return None, "Failed", "ERROR"
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    elif count >= 59:
        return None, "NOT_FOUND", "TIME_OUT"
    else:
        current_app.logger.info("Successfully deployed se engine")
        for se in response_csrf.json()["results"]:
            if str(se["config"]["name"]).strip() == str(name).strip():
                return se["config"]["url"], "FOUND", "SUCCESS"
        return None, "NOT_FOUND", "Failed"


def createNewCloud_Arch(ip, csrf2, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    body = {
        "name": Cloud.CLOUD_NAME.replace("vmc", "vsphere"),
        "vtype": "CLOUD_NONE",
        "dhcp_enabled": False,
        "mtu": 1500,
        "prefer_static_routes": False,
        "enable_vip_static_routes": False,
        "state_based_dns_registration": True,
        "ip6_autocfg_enabled": False,
        "dns_resolution_on_se": False,
        "enable_vip_on_all_interfaces": False,
        "autoscale_polling_interval": 60,
        "vmc_deployment": False,
        "license_type": "LIC_CORES",
    }
    json_object = json.dumps(body, indent=4)
    url = "https://" + ip + "/api/cloud"
    response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        os.system("rm -rf newCloudInfo.json")
        with open("./newCloudInfo.json", "w") as outfile:
            json.dump(response_csrf.json(), outfile)
        return response_csrf.json()["url"], "SUCCESS"


def changeSeGroupAndSetInterfaces(
    ip,
    csrf2,
    urlFromServiceEngine,
    se_cloud_url,
    file_name,
    vcenter_ip,
    vcenter_username,
    password,
    vm_name,
    type,
    name,
    aviVersion,
):
    if type == Type.WORKLOAD:
        changeMacAddressAndSeGroupInFileWorkload(
            vcenter_ip, vcenter_username, password, vm_name, se_cloud_url, file_name, name
        )
    else:
        changeMacAddressAndSeGroupInFile(vcenter_ip, vcenter_username, password, vm_name, se_cloud_url, file_name)
    url = urlFromServiceEngine
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    with open(file_name, "r") as openfile:
        json_object = json.load(openfile)
    json_object_m = json.dumps(json_object, indent=4)
    response_csrf = requests.request("PUT", url, headers=headers, data=json_object_m, verify=False, timeout=600)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        return response_csrf.json(), 200


def changeMacAddressAndSeGroupInFile(vcenter_ip, vcenter_username, password, vm_name, segroupUrl, file_name):
    d = getMacAddresses(getSi(vcenter_ip, vcenter_username, password), vm_name)
    mac1 = d[1]
    mac2 = d[2]
    # mac3 = d[3]
    replaceSeGroup(file_name, "se_group_ref", "false", segroupUrl)
    replaceMac(file_name, mac1)
    replaceMac(file_name, mac2)
    # replaceMac(file_name, mac3)
    if Tkg_version.TKG_VERSION == "2.1":
        mac4 = d[4]
        replaceMac(file_name, mac4)


def changeMacAddressAndSeGroupInFileWorkload(
    vcenter_ip, vcenter_username, password, vm_name, segroupUrl, file_name, number
):
    try:
        d = getMacAddresses(getSi(vcenter_ip, vcenter_username, password), vm_name)
    except Exception:
        for i in tqdm(range(120), desc="Waiting for getting ip …", ascii=False, ncols=75):
            time.sleep(1)
        d = getMacAddresses(getSi(vcenter_ip, vcenter_username, password), vm_name)
    if number == 1:
        mac2 = d[1]
        replaceMac(file_name, mac2)
    else:
        mac3 = d[2]
        mac5 = d[5]
        replaceMac(file_name, mac3)
        replaceMac(file_name, mac5)
    replaceSeGroup(file_name, "se_group_ref", "false", segroupUrl)
