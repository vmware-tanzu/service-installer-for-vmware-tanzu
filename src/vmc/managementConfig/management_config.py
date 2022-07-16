import base64
import json
import logging
import pathlib
import sys
import time
from pathlib import Path

import requests
from common.model.vmcSpec import VmcMasterSpec
from common.operation.constants import Paths
from common.util.file_helper import FileHelper
from flask import Blueprint, current_app, jsonify, request
from jinja2 import Template
from ruamel import yaml
from tqdm import tqdm

logger = logging.getLogger(__name__)
management_config = Blueprint("management_config", __name__, static_folder="managementConfig")

sys.path.append(".../")
from common.operation.vcenter_operations import create_folder, checkforIpAddress, getSi, \
    getMacAddresses, \
    checkVmPresent, destroy_vm
from common.operation.constants import ResourcePoolAndFolderName, Cloud, AkoType, CIDR, TmcUser, Vcenter, Type, \
    KubernetesOva
from common.operation.constants import ResourcePoolAndFolderName, Cloud, AkoType, CIDR, Type
import os
from common.common_utilities import isAviHaEnabled, preChecks, createResourceFolderAndWait, registerWithTmc, \
    getCloudStatus, envCheck, getSECloudStatus, runSsh, getClusterStatusOnTanzu, getVipNetworkIpNetMask, \
    getVrfAndNextRoutId, addStaticRoute, checkTmcEnabled, downloadAndPushKubernetesOvaMarketPlace
from common.common_utilities import preChecks, createResourceFolderAndWait, registerWithTmc, obtain_second_csrf, \
    getCloudStatus, envCheck, get_avi_version, getSECloudStatus, runSsh, getClusterStatusOnTanzu, \
    getVipNetworkIpNetMask, checkEnableIdentityManagement, switchToManagementContext, checkPinnipedInstalled, \
    getVrfAndNextRoutId, addStaticRoute, checkTmcEnabled, checkPinnipedServiceStatus, checkPinnipedDexServiceStatus, \
    createRbacUsers
from common.certificate_base64 import getBase64CertWriteToFile
from common.replace_value import replaceValueSysConfig, replaceSe, replaceSeGroup, replaceMac
from common.operation.ShellHelper import runShellCommandWithPolling, grabKubectlCommand, \
    runShellCommandAndReturnOutputAsList, runProcess, verifyPodsAreRunning
from common.operation.constants import SegmentsName, RegexPattern, Tkg_version, VrfType
from common.operation.constants import ControllerLocation
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


@management_config.route("/api/tanzu/vmc/tkgmgmt", methods=['POST'])
def configManagementCluster():
    config_cloud = configCloud()
    if config_cloud[1] != 200:
        current_app.logger.error(str(config_cloud[0].json['msg']))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to Config management cluster " + str(config_cloud[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    config_mgmt = configTkgMgmt()
    if config_mgmt[1] != 200:
        current_app.logger.error(str(config_mgmt[0].json['msg']))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to Config management cluster " + str(config_mgmt[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    d = {
        "responseType": "SUCCESS",
        "msg": "Management cluster configured Successfully",
        "ERROR_CODE": 200
    }
    current_app.logger.info("Management cluster configured Successfully")
    return jsonify(d), 200


@management_config.route("/api/tanzu/vmc/tkgmgmt/alb/config", methods=['POST'])
def configCloud():
    pre = preChecks()
    if pre[1] != 200:
        current_app.logger.error(pre[0].json['msg'])
        d = {
            "responseType": "ERROR",
            "msg": pre[0].json['msg'],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    password = current_app.config['VC_PASSWORD']
    vcenter_username = current_app.config['VC_USER']
    vcenter_ip = current_app.config['VC_IP']
    cluster_name = current_app.config['VC_CLUSTER']
    data_center = current_app.config['VC_DATACENTER']
    data_store = current_app.config['VC_DATASTORE']
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
    refreshToken = request.get_json(force=True)['marketplaceSpec']['refreshToken']
    if refreshToken:
        kubernetes_ova_os = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtBaseOs']
        kubernetes_ova_version = KubernetesOva.KUBERNETES_OVA_LATEST_VERSION
        current_app.logger.info("Kubernetes OVA configs for management cluster")
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
        current_app.logger.info("MarketPlace refresh token is not provided, skipping the download of kubernetes OVA")
    try:
        isCreated1 = create_folder(vcenter_ip, vcenter_username, password,
                                   data_center,
                                   ResourcePoolAndFolderName.Template_Automation_Folder)
        if isCreated1 is not None:
            current_app.logger.info("Created  folder " + ResourcePoolAndFolderName.Template_Automation_Folder)

    except Exception as e:
        current_app.logger.error("Failed to create folder " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create folder " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if isAviHaEnabled(env):
        ip = request.get_json(force=True)['componentSpec']['aviComponentSpec']['aviClusterIp']
    else:
        ip = checkforIpAddress(getSi(vcenter_ip, vcenter_username, password), ControllerLocation.CONTROLLER_NAME)
    if ip is None:
        current_app.logger.error("Failed to get ip of avi controller")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get ip of avi controller",
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
    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        current_app.logger.error("Failed to get csrf from new set password")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get csrf from new set password",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    aviVersion = get_avi_version(env)
    get_cloud = getCloudStatus(ip, csrf2, aviVersion, Cloud.CLOUD_NAME)
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
        isGen = True
        current_app.logger.info("Creating New cloud " + Cloud.CLOUD_NAME)
        cloud = createNewCloud(ip, csrf2, aviVersion)
        if cloud[0] is None:
            current_app.logger.error("Failed to create cloud " + str(cloud[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create cloud " + str(cloud[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        cloud_url = cloud[0]
    else:
        cloud_url = get_cloud[0]

    get_se_cloud = getSECloudStatus(ip, csrf2, aviVersion, Cloud.SE_GROUP_NAME)
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
        current_app.logger.info("Creating New se cloud " + Cloud.SE_GROUP_NAME)
        cloud_se = createSECloud(ip, csrf2, cloud_url, Cloud.SE_GROUP_NAME, aviVersion)
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

    get_wip = getVipNetwork(ip, csrf2, Cloud.WIP_NETWORK_NAME, aviVersion)
    if get_wip[0] is None:
        current_app.logger.error("Failed to get se vip network " + str(get_wip[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get vip network " + str(get_wip[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    isGen = False
    if get_wip[0] == "NOT_FOUND":
        isGen = True
        current_app.logger.info("Creating New VIP network " + Cloud.WIP_NETWORK_NAME)
        vip_net = createVipNetwork(ip, csrf2, cloud_url, Cloud.WIP_NETWORK_NAME, Type.MANAGEMENT, aviVersion)
        if vip_net[0] is None:
            current_app.logger.error("Failed to create vip network " + str(vip_net[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create  vip network " + str(vip_net[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        wip_url = vip_net[0]
        wip_cluster_url = ""
        current_app.logger.info("Created New VIP network " + Cloud.WIP_NETWORK_NAME)
    else:
        wip_url = get_wip[0]
        wip_cluster_url = ""
    if Tkg_version.TKG_VERSION == "1.5":
        get__cluster_wip = getVipNetwork(ip, csrf2, Cloud.WIP_CLUSTER_NETWORK_NAME, aviVersion)
        if get_wip[0] is None:
            current_app.logger.error("Failed to get cluster vip network " + str(get_wip[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get cluster vip network " + str(get_wip[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        isGen = False
        if get__cluster_wip[0] == "NOT_FOUND":
            isGen = True
            current_app.logger.info("Creating New cluster VIP network " + Cloud.WIP_CLUSTER_NETWORK_NAME)
            vip_net = createClusterVipNetwork(ip, csrf2, cloud_url, Cloud.WIP_CLUSTER_NETWORK_NAME,
                                              aviVersion)
            if vip_net[0] is None:
                current_app.logger.error("Failed to create cluster vip network " + str(vip_net[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create cluster vip network " + str(vip_net[1]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            wip_cluster_url = vip_net[0]
            current_app.logger.info("Created New cluster VIP network " + Cloud.WIP_NETWORK_NAME)
        else:
            wip_cluster_url = get_wip[0]
    get_ipam = getIpam(ip, csrf2, Cloud.IPAM_NAME, aviVersion)
    if get_ipam[0] is None:
        current_app.logger.error("Failed to get se Ipam " + str(get_ipam[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get ipam " + str(get_ipam[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    isGen = False
    if get_ipam[0] == "NOT_FOUND":
        isGen = True
        current_app.logger.info("Creating IPam " + Cloud.SE_GROUP_NAME)
        ipam = createIpam(ip, csrf2, wip_url, wip_cluster_url, Cloud.IPAM_NAME, aviVersion)
        if ipam[0] is None:
            current_app.logger.error("Failed to create ipam " + str(ipam[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create  ipam " + str(ipam[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        ipam_url = ipam[0]
    else:
        ipam_url = get_ipam[0]

    new_cloud_status = getDetailsOfNewCloud(ip, csrf2, cloud_url, ipam_url, se_cloud_url, aviVersion)
    if new_cloud_status[0] is None:
        current_app.logger.error("Failed to get new cloud details" + str(new_cloud_status[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get new cloud details " + str(new_cloud_status[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    update = updateNewCloudSeGroup(ip, csrf2, cloud_url, aviVersion)
    if update[0] is None:
        current_app.logger.error("Failed to update cloud " + str(update[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to update cloud " + str(update[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    se_ova = generateSeOva(ip, csrf2, aviVersion)
    if se_ova[0] is None:
        current_app.logger.error("Failed to generate se ova " + str(se_ova[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to generate se ova " + str(se_ova[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    vm_state = checkVmPresent(vcenter_ip, vcenter_username, password,
                              ControllerLocation.CONTROLLER_NAME)
    if vm_state is None:
        current_app.logger.error("Avi controller not found ")
        d = {
            "responseType": "ERROR",
            "msg": "Avi controller not found ",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    avi_uuid = vm_state.config.uuid
    se_download_ova = downloadSeOva(ip, csrf2, avi_uuid, aviVersion)
    if se_download_ova[0] is None:
        current_app.logger.error("Failed to download se ova " + str(se_download_ova[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to download se ova " + str(se_download_ova[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    current_app.logger.info("Getting token")
    token = generateToken(ip, csrf2, aviVersion)
    if token[0] is None:
        current_app.logger.error("Failed to get token " + str(token[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to  token " + str(token[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    current_app.logger.info("Get cluster uuid")
    uuid = getClusterUUid(ip, csrf2, aviVersion)
    if uuid[0] is None:
        current_app.logger.error("Failed to get cluster uuid " + str(uuid[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get cluster uuid " + str(uuid[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    replaceNetworkValues(ip, token[0], uuid[0], "./vmc/managementConfig/importSeOva-vc.json")
    vm_state = checkVmPresent(vcenter_ip, vcenter_username, password,
                              ControllerLocation.SE_OVA_TEMPLATE_NAME + "_" + avi_uuid)
    if vm_state is None:
        try:
            destroy_vm(getSi(vcenter_ip, vcenter_username, password),
                       ResourcePoolAndFolderName.Template_Automation_Folder, data_center,
                       ControllerLocation.SE_OVA_TEMPLATE_NAME)
        except Exception as e:
            current_app.logger.info(e)
            pass
    if vm_state is None:
        current_app.logger.info("Pushing ova and marking it as template..")
        push = pushSeOvaToVcenter(vcenter_ip, vcenter_username, password, data_center, data_store, cluster_name,
                                  avi_uuid)
        if push[0] is None:
            current_app.logger.error("Failed to  push se ova to vcenter " + str(push[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to  push se ova to vcenter " + str(push[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    else:
        current_app.logger.info("Se ova is already pushed to the vcenter")
    dep = controllerDeployment(ip, csrf2, data_center, data_store, cluster_name, vcenter_ip, vcenter_username, password,
                               se_cloud_url, "./vmc/managementConfig/se.json", "detailsOfServiceEngine1.json",
                               "detailsOfServiceEngine2.json", ControllerLocation.CONTROLLER_SE_NAME,
                               ControllerLocation.CONTROLLER_SE_NAME2, 1, Type.MANAGEMENT, 0, aviVersion)
    if dep[1] != 200:
        current_app.logger.error("Controller deployment failed" + str(dep[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Controller deployment failed " + str(dep[0]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    current_app.logger.info("Configured management cluster successfully")
    d = {
        "responseType": "SUCCESS",
        "msg": "Configured management cluster successfully",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def controllerDeployment(ip, csrf2, data_center, data_store, cluster_name, vcenter_ip, vcenter_username, password,
                         se_cloud_url, seJson, detailsJson1, detailsJson2, controllerName1, controllerName2, seCount,
                         type, name, aviVersion):
    isDeployed = False
    current_app.logger.info("Checking controller 1")
    vm_state_se = checkVmPresent(vcenter_ip, vcenter_username, password, controllerName1)
    if vm_state_se is None:
        current_app.logger.info("Getting token")
        token = generateToken(ip, csrf2, aviVersion)
        if token[0] is None:
            current_app.logger.error("Failed to get token " + str(token[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to  token " + str(token[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Get cluster uuid")
        uuid = getClusterUUid(ip, csrf2, aviVersion)
        if uuid[0] is None:
            current_app.logger.error("Failed to get cluster uuid " + str(uuid[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get cluster uuid " + str(uuid[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        if type == Type.WORKLOAD:
            replaceNetworkValuesWorkload(ip, token[0], uuid[0], seJson)
        else:
            replaceNetworkValues(ip, token[0], uuid[0], seJson)
        deploy_se = deploySeEngines(vcenter_ip, vcenter_username, password, ip, token[0], uuid[0], data_center,
                                    data_store, cluster_name, seJson,
                                    controllerName1, type)
        if deploy_se[0] != "SUCCESS":
            current_app.logger.error("Failed to  deploy se ova to vcenter " + str(deploy_se[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to  deploy se ova to vcenter " + str(deploy_se[0]),
                "ERROR_CODE": 500
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
        except:
            pass
        time.sleep(10)
        count = count + 1

    if not found:
        current_app.logger.error("Controller 1 is not up failed to get ip ")
        d = {
            "responseType": "ERROR",
            "msg": "Controller 1 is not up ",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    current_app.logger.info("Checking controller 2")
    vm_state_se2 = checkVmPresent(vcenter_ip, vcenter_username, password, controllerName2)
    if vm_state_se2 is None:
        current_app.logger.info("Getting token")
        token = generateToken(ip, csrf2, aviVersion)
        if token[0] is None:
            current_app.logger.error("Failed to get token " + str(token[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to  token " + str(token[0]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Get cluster uuid")
        uuid = getClusterUUid(ip, csrf2, aviVersion)
        if uuid[0] is None:
            current_app.logger.error("Failed to get cluster uuid " + str(uuid[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get cluster uuid " + str(uuid[0]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        replaceNetworkValues(ip, token[0], uuid[0], seJson)
        deploy_se2 = deploySeEngines(vcenter_ip, vcenter_username, password, ip, token[0], uuid[0], data_center,
                                     data_store, cluster_name, seJson,
                                     controllerName2, type)
        if deploy_se2[0] != "SUCCESS":
            current_app.logger.error("Failed to  deploy 2nd se ova to vcenter " + str(deploy_se2[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to  deploy 2nd se ova to vcenter " + str(deploy_se2[0]),
                "ERROR_CODE": 500
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
        except:
            pass
        time.sleep(10)
        count2 = count2 + 1

    if not found2:
        current_app.logger.error("Controller 2 is not up failed to get ip ")
        d = {
            "responseType": "ERROR",
            "msg": "Controller 2 is not up ",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    urlFromServiceEngine1 = listAllServiceEngine(ip, csrf2, seCount, seIp1, aviVersion)
    if urlFromServiceEngine1[0] is None:
        current_app.logger.error("Failed to  get service engine details" + str(urlFromServiceEngine1[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to  get service engine details " + str(urlFromServiceEngine1[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    urlFromServiceEngine2 = listAllServiceEngine(ip, csrf2, seCount, seIp2, aviVersion)
    if urlFromServiceEngine2[0] is None:
        current_app.logger.error("Failed to  get service engine details" + str(urlFromServiceEngine2[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to  get service engine details " + str(urlFromServiceEngine2[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    details1 = getDetailsOfServiceEngine(ip, csrf2, urlFromServiceEngine1[0], detailsJson1, aviVersion)
    if details1[0] is None:
        current_app.logger.error("Failed to  get details of engine 1" + str(details1[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to  get details of engine 1" + str(details1[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    details2 = getDetailsOfServiceEngine(ip, csrf2, urlFromServiceEngine2[0], detailsJson2, aviVersion)
    if details2[0] is None:
        current_app.logger.error("Failed to  get details of engine 2 " + str(details2[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to  get details of engine 2 " + str(details2[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    se_engines = changeSeGroupAndSetInterfaces(ip, csrf2, urlFromServiceEngine1[0], se_cloud_url,
                                               detailsJson1,
                                               vcenter_ip, vcenter_username,
                                               password, controllerName1,
                                               type, name, aviVersion)
    if se_engines[0] is None:
        current_app.logger.error("Failed to  change set interfaces engine 1" + str(se_engines[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to  change set interfaces engine 1" + str(se_engines[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    se_engines2 = changeSeGroupAndSetInterfaces(ip, csrf2, urlFromServiceEngine2[0], se_cloud_url,
                                                detailsJson2,
                                                vcenter_ip, vcenter_username,
                                                password, controllerName2,
                                                type, name, aviVersion)
    if se_engines2[0] is None:
        current_app.logger.error("Failed to  change set interfaces engine 2" + str(se_engines2[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to  change set interfaces engine2 " + str(se_engines2[1]),
            "ERROR_CODE": 500
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
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Service engine " + i + " is connected")
    try:
        checkforIpAddress(getSi(vcenter_ip, vcenter_username, password), controllerName1)
        checkforIpAddress(getSi(vcenter_ip, vcenter_username, password), controllerName2)
    except Exception as e:
        current_app.logger.error(e)
        d = {
            "responseType": "ERROR",
            "msg": e,
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
            if re["name"] == Cloud.CLOUD_NAME:
                uuid = re["uuid"]
    if uuid is None:
        return None, "NOT_FOUND"
    if type == Type.WORKLOAD:
        ipNetMask = seperateNetmaskAndIp(
            request.get_json(force=True)['componentSpec']['tkgWorkloadDataNetworkSpec'][
                'tkgWorkloadDataGatewayCidr'])
    else:
        ipNetMask = seperateNetmaskAndIp(
            request.get_json(force=True)['componentSpec']['tkgMgmtDataNetworkSpec']['tkgMgmtDataGatewayCidr'])
        ipNetMask_ = seperateNetmaskAndIp(
            request.get_json(force=True)['componentSpec']['tkgClusterVipNetwork'][
                'tkgClusterVipNetworkGatewayCidr'])
        vrf = getVrfAndNextRoutId(ip, csrf2, uuid, VrfType.GLOBAL, ipNetMask_[0], aviVersion)
        if vrf[0] is None or vrf[1] == "NOT_FOUND":
            current_app.logger.error("Vrf not found " + str(vrf[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Vrf not found " + str(vrf[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        if vrf[1] != "Already_Configured":
            current_app.logger.info("Routing is not configured , configuring.")
            ad = addStaticRoute(ip, csrf2, vrf[0], ipNetMask_[0], vrf[1], aviVersion)
            if ad[0] is None:
                current_app.logger.error("Failed to add static route " + str(ad[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Vrf not found " + str(ad[1]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            current_app.logger.info("Routing is configured.")
    vrf = getVrfAndNextRoutId(ip, csrf2, uuid, VrfType.GLOBAL, ipNetMask[0], aviVersion)
    if vrf[0] is None or vrf[1] == "NOT_FOUND":
        current_app.logger.error("Vrf not found " + str(vrf[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Vrf not found " + str(vrf[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if vrf[1] != "Already_Configured":
        current_app.logger.info("Routing is not configured , configuring.")
        ad = addStaticRoute(ip, csrf2, vrf[0], ipNetMask[0], vrf[1], aviVersion)
        if ad[0] is None:
            current_app.logger.error("Failed to add static route " + str(ad[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Vrf not found " + str(ad[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Routing is configured.")
    d = {
        "responseType": "SUCCESS",
        "msg": "Deployment Successful",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


@management_config.route("/api/tanzu/vmc/tkgmgmt/config", methods=['POST'])
def configTkgMgmt():
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
    vmcSpec = VmcMasterSpec.parse_obj(json_dict)
    env = env[0]
    aviVersion = get_avi_version(env)
    password = current_app.config['VC_PASSWORD']
    vcenter_username = current_app.config['VC_USER']
    vcenter_ip = current_app.config['VC_IP']
    cluster_name = current_app.config['VC_CLUSTER']
    data_center = current_app.config['VC_DATACENTER']
    data_store = current_app.config['VC_DATASTORE']
    parent_resourcepool = current_app.config['RESOURCE_POOL']
    create = createResourceFolderAndWait(vcenter_ip, vcenter_username, password,
                                         cluster_name, data_center, ResourcePoolAndFolderName.TKG_Mgmt_RP,
                                         ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder, parent_resourcepool)
    if create[1] != 200:
        current_app.logger.error("Failed to create resource pool and folder " + create[0].json['msg'])
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create resource pool " + str(create[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if isAviHaEnabled(env):
        ip = request.get_json(force=True)['componentSpec']['aviComponentSpec']['aviClusterIp']
    else:
        ip = checkforIpAddress(getSi(vcenter_ip, vcenter_username, password), ControllerLocation.CONTROLLER_NAME)
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
    get_wip = getVipNetworkIpNetMask(ip, csrf2, Cloud.WIP_NETWORK_NAME, aviVersion)
    if get_wip[0] is None or get_wip[0] == "NOT_FOUND":
        current_app.logger.error("Failed to get se vip network ip and netmask " + str(get_wip[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get vip network " + str(get_wip[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if Tkg_version.TKG_VERSION == "1.5":

        get_cluster_wip = getVipNetworkIpNetMask(ip, csrf2, Cloud.WIP_CLUSTER_NETWORK_NAME, aviVersion)
        if get_cluster_wip[0] is None or get_cluster_wip[0] == "NOT_FOUND":
            current_app.logger.error("Failed to get cluster vip network ip and netmask " + str(get_cluster_wip[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get cluster  vip network " + str(get_cluster_wip[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        clusterWip = get_cluster_wip[0]
    else:
        clusterWip = ""
    management_cluster = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtClusterName']
    current_app.logger.info("Deploying Management Cluster " + management_cluster)
    deploy_status = deployManagementCluster(management_cluster, aviVersion, ip, data_center, data_store, cluster_name,
                                            get_wip[0],
                                            clusterWip, vcenter_ip, vcenter_username, password, vmcSpec)
    if deploy_status[0] is None:
        current_app.logger.error("Failed to deploy management cluster " + deploy_status[1])
        d = {
            "responseType": "ERROR",
            "msg": "Failed to deploy management cluster " + deploy_status[1],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    command = ["tanzu", "plugin", "sync"]
    runShellCommandAndReturnOutputAsList(command)

    if checkEnableIdentityManagement(env):
        podRunninng = ["tanzu", "cluster", "list", "--include-management-cluster"]
        command_status = runShellCommandAndReturnOutputAsList(podRunninng)
        if not verifyPodsAreRunning(management_cluster, command_status[0], RegexPattern.running):
            current_app.logger.error(management_cluster + " is not deployed")
            d = {
                "responseType": "ERROR",
                "msg": management_cluster + " is not deployed",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        switch = switchToManagementContext(management_cluster)
        if switch[1] != 200:
            current_app.logger.info(switch[0].json['msg'])
            d = {
                "responseType": "ERROR",
                "msg": switch[0].json['msg'],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
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
            current_app.logger.info("Validating pinniped service status")
            check_pinniped_svc = checkPinnipedServiceStatus()
            if check_pinniped_svc[1] != 200:
                current_app.logger.error(check_pinniped_svc[0])
                d = {
                    "responseType": "ERROR",
                    "msg": check_pinniped_svc[0],
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            current_app.logger.info("Successfully validated Pinniped service status")
            identity_mgmt_type = str(
                request.get_json(force=True)["componentSpec"]["identityManagementSpec"]["identityManagementType"])
            if identity_mgmt_type.lower() == "ldap":
                check_pinniped_dexsvc = checkPinnipedDexServiceStatus()
                if check_pinniped_dexsvc[1] != 200:
                    current_app.logger.error(check_pinniped_dexsvc[0])
                    d = {
                        "responseType": "ERROR",
                        "msg": check_pinniped_dexsvc[0],
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
                current_app.logger.info("External IP for Pinniped is set as: " + check_pinniped_svc[0])

            cluster_admin_users = \
            request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtRbacUserRoleSpec']['clusterAdminUsers']
            admin_users = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtRbacUserRoleSpec'][
                'adminUsers']
            edit_users = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtRbacUserRoleSpec'][
                'editUsers']
            view_users = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtRbacUserRoleSpec'][
                'viewUsers']
            rbac_user_status = createRbacUsers(management_cluster, isMgmt=True, env=env, edit_users=edit_users,
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
    if Tkg_version.TKG_VERSION == "1.5":
        current_app.logger.info("TMC registration on management cluster is supported on tanzu 1.5.1")
        if checkTmcEnabled(env):
            clusterGroup = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtClusterGroupName']

            if not clusterGroup:
                clusterGroup = "default"

            state = registerWithTmc(management_cluster, env, "false", "management", clusterGroup)
            if state[0] is None:
                current_app.logger.error("Failed to register on tmc " + state[1])
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to register on tmc " + state[1],
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
        else:
            current_app.logger.info("TMC registration is disabled")
    current_app.logger.info("Deployed management cluster successfully")
    d = {
        "responseType": "SUCCESS",
        "msg": "Successfully configured management cluster ",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def getConnectedStatus(ip, csrf2, se_engine_url, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    url = se_engine_url
    payload = {}
    count = 0
    while count < 30:
        response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False, timeout=120)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        else:
            if bool(response_csrf.json()["se_connected"]):
                return "SUCCESS", "FOUND"
            time.sleep(10)
            count = count + 1
            current_app.logger.info("Waited " + str(count * 10) + ", retrying")
    return "FAILED", "NOT_FOUND"


def getDefaultCloudUrl(ip, csrf2, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    url = "https://" + ip + "/api/cloud/"
    payload = {}
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        return response_csrf.json()["results"][0]["url"], "SUCCESS"


def referenceTkgMNetwork(ip, csrf2, url, aviVersion):
    reference_TKG_Mgmt_Network_ip = request.get_json(force=True)['componentSpec']['tkgMgmtSpec'][
        'Reference_TKG_Mgmt_Network_IP']
    reference_TKG_Mgmt_Network_netmask = request.get_json(force=True)['componentSpec']['tkgMgmtSpec'][
        'Reference_TKG_Mgmt_Network_Netmask']
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    body = {"vcenter_dvs": True,
            "dhcp_enabled": False,
            "exclude_discovered_subnets": False,
            "synced_from_se": False,
            "ip6_autocfg_enabled": False,
            "cloud_ref": url,
            "configured_subnets": [
                {
                    "prefix": {
                        "ip_addr": {
                            "addr": reference_TKG_Mgmt_Network_ip, "type": "V4"},
                        "mask": reference_TKG_Mgmt_Network_netmask
                    }
                }
            ],
            "name": Cloud.mgmtVipNetwork
            }
    json_object = json.dumps(body, indent=4)
    url = "https://" + ip + "/api/network"
    response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        return 200, "SUCCESS"


def createNewCloud(ip, csrf2, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    body = {"name": Cloud.CLOUD_NAME,
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
            "license_type": "LIC_CORES"
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


def getNewBody(newCloudUrl, seGroupName):
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
        "se_name_prefix": "Avi",
        "vs_host_redundancy": True,
        "vcenter_folder": "AviSeFolder",
        "vcenter_datastores_include": False,
        "vcenter_datastore_mode": "VCENTER_DATASTORE_ANY",
        "cpu_reserve": False,
        "mem_reserve": True,
        "ha_mode": "HA_MODE_SHARED_PAIR",
        "algo": "PLACEMENT_ALGO_PACKED",
        "buffer_se": 0,
        "active_standby": False,
        "placement_mode": "PLACEMENT_MODE_AUTO",
        "se_dos_profile": {
            "thresh_period": 5
        },
        "auto_rebalance_interval": 300,
        "aggressive_failure_detection": False,
        "realtime_se_metrics": {
            "enabled": False,
            "duration": 30
        },
        "vs_scaleout_timeout": 600,
        "vs_scalein_timeout": 30,
        "connection_memory_percentage": 50,
        "extra_config_multiplier": 0,
        "vs_scalein_timeout_for_upgrade": 30,
        "log_disksz": 10000,
        "os_reserved_memory": 0,
        "hm_on_standby": True,
        "per_app": False,
        "distribute_load_active_standby": False,
        "auto_redistribute_active_standby_load": False,
        "dedicated_dispatcher_core": False,
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
        "vss_placement": {
            "num_subcores": 4,
            "core_nonaffinity": 2
        },
        "flow_table_new_syn_max_entries": 0,
        "disable_csum_offloads": False,
        "disable_gro": True,
        "disable_tso": False,
        "enable_hsm_priming": False,
        "distribute_queues": False,
        "vss_placement_enabled": False,
        "enable_multi_lb": False,
        "n_log_streaming_threads": 1,
        "free_list_size": 1024,
        "max_rules_per_lb": 150,
        "max_public_ips_per_lb": 30,
        "self_se_election": True,
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
        "app_cache_percent": 10,
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
        "se_rl_prop": {
            "msf_num_stages": 1,
            "msf_stage_size": 16384
        },
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
        "objsync_config": {
            "objsync_cpu_limit": 30,
            "objsync_reconcile_interval": 10,
            "objsync_hub_elect_interval": 60
        },
        "se_dp_isolation": False,
        "se_dp_isolation_num_non_dp_cpus": 0,
        "cloud_ref": newCloudUrl,
        "vcenter_datastores": [
        ],
        "service_ip_subnets": [
        ],
        "auto_rebalance_criteria": [
        ],
        "auto_rebalance_capacity_per_se": [
        ],
        "license_tier": "ENTERPRISE",
        "license_type": "LIC_CORES",
        "se_bandwidth_type": "SE_BANDWIDTH_UNLIMITED",
        "name": seGroupName
    }
    return json.dumps(body, indent=4)


def createSECloud(ip, csrf2, newCloudUrl, seGroupName, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    body = {
        "name": seGroupName,
        "se_dp_isolation": False,
        "se_dp_isolation_num_non_dp_cpus": 0,
        "cloud_ref": newCloudUrl,
        "max_vs_per_se": 10,
        "min_scaleout_per_vs": 1,
        "max_scaleout_per_vs": 4,
        "max_se": 10,
        "vcpus_per_se": 1,
        "memory_per_se": 2048,
        "disk_per_se": 15,
        "max_cpu_usage": 80,
        "min_cpu_usage": 30,
        "se_deprovision_delay": 120,
        "auto_rebalance": False,
        "se_name_prefix": "Avi",
        "vs_host_redundancy": True,
        "vcenter_folder": "AviSeFolder",
        "vcenter_datastores_include": False,
        "vcenter_datastore_mode": "VCENTER_DATASTORE_ANY",
        "cpu_reserve": False,
        "mem_reserve": True,
        "ha_mode": "HA_MODE_LEGACY_ACTIVE_STANDBY",
        "algo": "PLACEMENT_ALGO_PACKED",
        "buffer_se": 1,
        "active_standby": False,
        "placement_mode": "PLACEMENT_MODE_AUTO",
        "se_dos_profile": {
            "thresh_period": 5
        },
        "auto_rebalance_interval": 300,
        "aggressive_failure_detection": False,
        "realtime_se_metrics": {
            "enabled": False,
            "duration": 30
        },
        "vs_scaleout_timeout": 600,
        "vs_scalein_timeout": 30,
        "connection_memory_percentage": 50,
        "extra_config_multiplier": 0,
        "vs_scalein_timeout_for_upgrade": 30,
        "log_disksz": 10000,
        "os_reserved_memory": 0,
        "hm_on_standby": False,
        "per_app": False,
        "distribute_load_active_standby": False,
        "auto_redistribute_active_standby_load": False,
        "dedicated_dispatcher_core": False,
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
        "vss_placement": {
            "num_subcores": 4,
            "core_nonaffinity": 2
        },
        "flow_table_new_syn_max_entries": 0,
        "disable_csum_offloads": False,
        "disable_gro": True,
        "disable_tso": False,
        "enable_hsm_priming": False,
        "distribute_queues": False,
        "vss_placement_enabled": False,
        "enable_multi_lb": False,
        "n_log_streaming_threads": 1,
        "free_list_size": 1024,
        "max_rules_per_lb": 150,
        "max_public_ips_per_lb": 30,
        "self_se_election": True,
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
        "app_cache_percent": 0,
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
        "se_rl_prop": {
            "msf_num_stages": 1,
            "msf_stage_size": 16384
        },
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
        "vcenter_datastores": [],
        "service_ip_subnets": [],
        "auto_rebalance_criteria": [],
        "auto_rebalance_capacity_per_se": [],
        "license_tier": "ESSENTIALS",
        "license_type": "LIC_CORES",
        "se_bandwidth_type": "SE_BANDWIDTH_UNLIMITED"
    }
    json_object = getNewBody(newCloudUrl, seGroupName)
    url = "https://" + ip + "/api/serviceenginegroup"
    response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        return response_csrf.json()["url"], "SUCCESS"


def getVipNetwork(ip, csrf2, name, aviVersion):
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
                    return re["url"], "SUCCESS"
            else:
                next_url = None if not response_csrf.json()["next"] else response_csrf.json()["next"]
                while len(next_url) > 0:
                    response_csrf = requests.request("GET", next_url, headers=headers, data=body, verify=False)
                    for re in response_csrf.json()["results"]:
                        if re['name'] == name:
                            return re["url"], "SUCCESS"
                    next_url = None if not response_csrf.json()["next"] else response_csrf.json()["next"]
        return "NOT_FOUND", "SUCCESS"
    except KeyError:
        return "NOT_FOUND", "SUCCESS"


def createClusterVipNetwork(ip, csrf2, newCloudUrl, name, aviVersion):
    ipNetMask = seperateNetmaskAndIp(
        request.get_json(force=True)['componentSpec']['tkgClusterVipNetwork'][
            'tkgClusterVipNetworkGatewayCidr'])
    start_ip = request.get_json(force=True)['componentSpec']['tkgClusterVipNetwork'][
        'tkgClusterVipIpStartRange']
    end_ip = request.get_json(force=True)['componentSpec']['tkgClusterVipNetwork'][
        'tkgClusterVipIpEndRange']
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    body = {"name": name,
            "vcenter_dvs": True,
            "dhcp_enabled": False,
            "exclude_discovered_subnets": False,
            "synced_from_se": False,
            "ip6_autocfg_enabled": False,
            "cloud_ref": newCloudUrl,
            "configured_subnets": [
                {"prefix": {
                    "ip_addr": {
                        "addr": ipNetMask[0],
                        "type": "V4"
                    },
                    "mask": ipNetMask[1]
                },
                    "static_ip_ranges": [
                        {
                            "range": {
                                "begin": {
                                    "addr": start_ip,
                                    "type": "V4"
                                },
                                "end": {
                                    "addr": end_ip,
                                    "type": "V4"
                                }
                            },
                            "type": "STATIC_IPS_FOR_VIP_AND_SE"
                        }
                    ]
                }
            ]
            }
    json_object = json.dumps(body, indent=4)
    url = "https://" + ip + "/api/network"
    response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        return response_csrf.json()["url"], "SUCCESS"


def createVipNetwork(ip, csrf2, newCloudUrl, name, type, aviVersion):
    if type == Type.WORKLOAD:
        ipNetMask = seperateNetmaskAndIp(
            request.get_json(force=True)['componentSpec']['tkgWorkloadDataNetworkSpec'][
                'tkgWorkloadDataGatewayCidr'])
        start_ip = request.get_json(force=True)['componentSpec']['tkgWorkloadDataNetworkSpec'][
            "tkgWorkloadDataServiceStartRange"]
        end_ip = request.get_json(force=True)['componentSpec']['tkgWorkloadDataNetworkSpec'][
            "tkgWorkloadDataServiceEndRange"]
    else:
        ipNetMask = seperateNetmaskAndIp(
            request.get_json(force=True)['componentSpec']['tkgMgmtDataNetworkSpec']['tkgMgmtDataGatewayCidr'])
        start_ip = request.get_json(force=True)['componentSpec']['tkgMgmtDataNetworkSpec'][
            'tkgMgmtDataServiceStartRange']
        end_ip = request.get_json(force=True)['componentSpec']['tkgMgmtDataNetworkSpec'][
            'tkgMgmtDataServiceEndRange']
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    body = {"name": name,
            "vcenter_dvs": True,
            "dhcp_enabled": False,
            "exclude_discovered_subnets": False,
            "synced_from_se": False,
            "ip6_autocfg_enabled": False,
            "cloud_ref": newCloudUrl,
            "configured_subnets": [
                {"prefix": {
                    "ip_addr": {
                        "addr": ipNetMask[0],
                        "type": "V4"
                    },
                    "mask": ipNetMask[1]
                },
                    "static_ip_ranges": [
                        {
                            "range": {
                                "begin": {
                                    "addr": start_ip,
                                    "type": "V4"
                                },
                                "end": {
                                    "addr": end_ip,
                                    "type": "V4"
                                }
                            },
                            "type": "STATIC_IPS_FOR_VIP_AND_SE"
                        }
                    ]
                }
            ]
            }
    json_object = json.dumps(body, indent=4)
    url = "https://" + ip + "/api/network"
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
        "x-csrftoken": csrf2[0]
    }
    body = {}
    url = "https://" + ip + "/api/ipamdnsproviderprofile"
    response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        for re in response_csrf.json()["results"]:
            if re['name'] == name:
                return re["url"], "SUCCESS"
    return "NOT_FOUND", "SUCCESS"


def createIpam(ip, csrf2, vipNetworkUrl, clusterVip, name, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    if Tkg_version.TKG_VERSION == "1.3":
        body = {
            "name": name,
            "internal_profile": {
                "ttl": 30,
                "usable_networks": [
                    {
                        "nw_ref": vipNetworkUrl
                    }
                ]
            },
            "allocate_ip_in_vrf": False,
            "type": "IPAMDNS_TYPE_INTERNAL",
            "gcp_profile": {
                "match_se_group_subnet": False,
                "use_gcp_network": False
            },
            "azure_profile": {
                "use_enhanced_ha": False,
                "use_standard_alb": False
            }
        }
    elif Tkg_version.TKG_VERSION == "1.5":
        body = {
            "name": name,
            "internal_profile": {
                "ttl": 30,
                "usable_networks": [
                    {
                        "nw_ref": vipNetworkUrl
                    },
                    {
                        "nw_ref": clusterVip
                    }
                ]
            },
            "allocate_ip_in_vrf": False,
            "type": "IPAMDNS_TYPE_INTERNAL",
            "gcp_profile": {
                "match_se_group_subnet": False,
                "use_gcp_network": False
            },
            "azure_profile": {
                "use_enhanced_ha": False,
                "use_standard_alb": False
            }
        }
    json_object = json.dumps(body, indent=4)
    url = "https://" + ip + "/api/ipamdnsproviderprofile"
    response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        return response_csrf.json()["url"], "SUCCESS"


def getDetailsOfNewCloud(ip, csrf2, newCloudUrl, newIpamUrl, seGroupUrl, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
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
        replaceValueSysConfig("detailsOfNewCloud.json", "ipam_provider_ref", "name",
                              newIpamUrl)
        replaceValueSysConfig("detailsOfNewCloud.json", "se_group_template_ref", "name",
                              seGroupUrl)
        return response_csrf.json(), "SUCCESS"


def updateNewCloudSeGroup(ip, csrf2, newCloudUrl, aviVersion):
    with open("./detailsOfNewCloud.json", 'r') as file2:
        new_cloud_json = json.load(file2)
    json_object = json.dumps(new_cloud_json, indent=4)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    response_csrf = requests.request("PUT", newCloudUrl, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        return response_csrf.json(), "SUCCESS"


def generateSeOva(ip, csrf2, aviVersion):
    current_app.logger.info("Generating se ova")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "type": "ova",
        "x-csrftoken": csrf2[0]
    }
    with open("./newCloudInfo.json", 'r') as file2:
        new_cloud_json = json.load(file2)
    uuid = None
    try:
        uuid = new_cloud_json["uuid"]
    except:
        for re in new_cloud_json["results"]:
            if re["name"] == Cloud.CLOUD_NAME:
                uuid = re["uuid"]
    if uuid is None:
        return None, "NOT_FOUND"
    body = {
        "file_format": "ova",
        "cloud_uuid": uuid
    }
    modified = json.dumps(body, indent=4)
    url = "https://" + ip + "/api/fileservice/seova"
    start = time.time()
    response_csrf = requests.request("POST", url, headers=headers, data=modified, verify=False, timeout=600)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        end = time.time()
        difference = int(end - start)
        if difference < 5:
            current_app.logger.info("Se ova is already generated")
        return "SUCCESS", 200


def downloadSeOva(ip, csrf2, avi_uuid, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "type": "ova",
        "x-csrftoken": csrf2[0]
    }
    with open("./newCloudInfo.json", 'r') as file2:
        new_cloud_json = json.load(file2)
    uuid = None
    try:
        uuid = new_cloud_json["uuid"]
    except:
        for re in new_cloud_json["results"]:
            if re["name"] == Cloud.CLOUD_NAME:
                uuid = re["uuid"]
    if uuid is None:
        return None, "NOT_FOUND"
    my_file = Path("/tmp/" + avi_uuid + ".ova")
    current_app.config['se_ova_path'] = "/tmp/" + avi_uuid + ".ova"
    if my_file.exists():
        current_app.logger.info("Se ova is already downloaded")
        return "SUCCESS", 200
    url = "https://" + ip + "/api/fileservice/seova?file_format=ova&cloud_uuid=" + uuid
    payload = {}
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False, timeout=600)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        for txt_file in pathlib.Path('/tmp').glob('*.ova'):
            os.system("rm -rf " + str(txt_file.absolute()))
        with open(r'/tmp/' + avi_uuid + '.ova', 'wb') as f:
            f.write(response_csrf.content)
        current_app.logger.info("Se ova downloaded")
        return "SUCCESS", 200


def getClusterUUid(ip, csrf2, aviVersion):
    url = "https://" + ip + "/api/cluster"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    payload = {}
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False, timeout=600)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        return response_csrf.json()["uuid"], 200


def generateToken(ip, csrf2, aviVersion):
    with open("./newCloudInfo.json", 'r') as file2:
        new_cloud_json = json.load(file2)
    uuid = None
    try:
        uuid = new_cloud_json["uuid"]
    except:
        for re in new_cloud_json["results"]:
            if re["name"] == Cloud.CLOUD_NAME:
                uuid = re["uuid"]
    if uuid is None:
        return None, "NOT_FOUND"
    url = "https://" + ip + "/api/securetoken-generate?cloud_uuid=" + uuid
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    payload = {}
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False, timeout=600)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        return response_csrf.json()["auth_token"], 200


def replaceNetworkValues(ip, aviAuthToken, clusterUUid, file_name):
    tkg_management = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtNetworkName']
    property_mapping = {
        "AVICNTRL": ip,
        "AVICNTRL_AUTHTOKEN": aviAuthToken,
        "AVICNTRL_CLUSTERUUID": clusterUUid
    }
    for key, value in property_mapping.items():
        replaceSe(file_name, "PropertyMapping", key, "Key", "Value", value)
    if Tkg_version.TKG_VERSION == "1.5":
        dictionary_network = {
            "Management": SegmentsName.DISPLAY_NAME_AVI_MANAGEMENT,
            "Data Network 1": SegmentsName.DISPLAY_NAME_AVI_DATA_SEGMENT,
            "Data Network 2": tkg_management,
            "Data Network 3": SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment,
            "Data Network 4": SegmentsName.DISPLAY_NAME_CLUSTER_VIP,
            "Data Network 5": SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment,
            "Data Network 6": SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment,
            "Data Network 7": SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment,
            "Data Network 8": SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment,
            "Data Network 9": SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment

        }
    else:
        dictionary_network = {
            "Management": SegmentsName.DISPLAY_NAME_AVI_MANAGEMENT,
            "Data Network 1": SegmentsName.DISPLAY_NAME_AVI_DATA_SEGMENT,
            "Data Network 2": tkg_management,
            "Data Network 3": SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment,
            "Data Network 4": SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment,
            "Data Network 5": SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment,
            "Data Network 6": SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment,
            "Data Network 7": SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment,
            "Data Network 8": SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment,
            "Data Network 9": SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment

        }
    for key, value in dictionary_network.items():
        replaceSe(file_name, "NetworkMapping", key, "Name", "Network", value)


def replaceNetworkValuesWorkload(ip, aviAuthToken, clusterUUid, file_name):
    property_mapping = {
        "AVICNTRL": ip,
        "AVICNTRL_AUTHTOKEN": aviAuthToken,
        "AVICNTRL_CLUSTERUUID": clusterUUid
    }
    for key, value in property_mapping.items():
        replaceSe(file_name, "PropertyMapping", key, "Key", "Value", value)
    dictionary_network = {
        "Management": SegmentsName.DISPLAY_NAME_AVI_MANAGEMENT,
        "Data Network 1": SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT,
        "Data Network 2": SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT,
        "Data Network 3": SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT,
        "Data Network 4": SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT,
        "Data Network 5": SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT,
        "Data Network 6": SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT,
        "Data Network 7": SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT,
        "Data Network 8": SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT,
        "Data Network 9": SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT

    }
    for key, value in dictionary_network.items():
        replaceSe(file_name, "NetworkMapping", key, "Name", "Network", value)


def pushSeOvaToVcenter(vcenter_ip, vcenter_username, password, data_center, data_store,
                       cluster_name, avi_uuid):
    os.putenv("GOVC_URL", "https://" + vcenter_ip + "/sdk")
    os.putenv("GOVC_USERNAME", vcenter_username)
    os.putenv("GOVC_PASSWORD", password)
    os.putenv("GOVC_INSECURE", "true")
    parent_resourcepool = current_app.config['RESOURCE_POOL']
    if parent_resourcepool is not None:
        rp_pool = data_center + "/host/" + cluster_name + "/Resources/" + parent_resourcepool + "/" + ResourcePoolAndFolderName.AVI_RP
    else:
        rp_pool = data_center + "/host/" + cluster_name + "/Resources/" + ResourcePoolAndFolderName.AVI_RP
    replaceValueSysConfig("./vmc/managementConfig/importSeOva-vc.json", "Name", "name",
                          ControllerLocation.SE_OVA_TEMPLATE_NAME + "_" + avi_uuid)
    ova_deploy_command = [
        "govc", "import.ova", "-options", "./vmc/managementConfig/importSeOva-vc.json", "-dc=" + data_center,
                                                                                        "-ds=" + data_store,
                                                                                        "-folder=" + ResourcePoolAndFolderName.Template_Automation_Folder,
                                                                                        "-pool=/" + rp_pool,
        current_app.config['se_ova_path']]
    try:
        runProcess(ova_deploy_command)
    except Exception as e:
        return None, str(e)
    return "SUCCESS", 200


def deploySeEngines(vcenter_ip, vcenter_username, password, ip, aviAuthToken, clusterUUid, data_center, data_store,
                    cluster_name, file_name, engine_name, type):
    os.putenv("GOVC_URL", "https://" + vcenter_ip + "/sdk")
    os.putenv("GOVC_USERNAME", vcenter_username)
    os.putenv("GOVC_PASSWORD", password)
    os.putenv("GOVC_INSECURE", "true")
    replaceValueSysConfig(file_name, "Name", "name", engine_name)
    if type == Type.WORKLOAD:
        replaceNetworkValuesWorkload(ip, aviAuthToken, clusterUUid, file_name)
    else:
        replaceNetworkValues(ip, aviAuthToken, clusterUUid, file_name)
    parent_resourcepool = current_app.config['RESOURCE_POOL']
    if parent_resourcepool is not None:
        rp_pool = data_center + "/host/" + cluster_name + "/Resources/" + parent_resourcepool + "/" + ResourcePoolAndFolderName.AVI_RP
    else:
        rp_pool = data_center + "/host/" + cluster_name + "/Resources/" + ResourcePoolAndFolderName.AVI_RP
    ova_deploy_command = [
        "govc", "import.ova", "-options", file_name, "-dc=" + data_center,
                                                     "-ds=" + data_store,
                                                     "-folder=" + ResourcePoolAndFolderName.AVI_Components_FOLDER,
                                                     "-pool=/" + rp_pool,
        current_app.config['se_ova_path']]
    if type == Type.WORKLOAD:
        network_connect = ["govc", "device.connect", "-vm", engine_name, "ethernet-0",
                           "ethernet-1"]
        network_disconnect = ["govc", "device.disconnect", "-vm", engine_name, "ethernet-2",
                              "ethernet-3", "ethernet-4", "ethernet-5", "ethernet-6", "ethernet-7", "ethernet-8",
                              "ethernet-9"]

    else:
        if Tkg_version.TKG_VERSION == "1.5":
            network_connect = ["govc", "device.connect", "-vm", engine_name, "ethernet-0",
                               "ethernet-1", "ethernet-2", "ethernet-3", "ethernet-4"]
            network_disconnect = ["govc", "device.disconnect", "-vm", engine_name,
                                  "ethernet-5", "ethernet-6", "ethernet-7", "ethernet-8", "ethernet-9"]
        else:
            network_connect = ["govc", "device.connect", "-vm", engine_name, "ethernet-0",
                               "ethernet-1", "ethernet-2", "ethernet-3"]
            network_disconnect = ["govc", "device.disconnect", "-vm", engine_name, "ethernet-4",
                                  "ethernet-5", "ethernet-6", "ethernet-7", "ethernet-8", "ethernet-9"]
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


def listAllServiceEngine(ip, csrf2, countSe, name, aviVersion):
    with open("./newCloudInfo.json", 'r') as file2:
        new_cloud_json = json.load(file2)
    uuid = None
    try:
        uuid = new_cloud_json["uuid"]
    except:
        for re in new_cloud_json["results"]:
            if re["name"] == Cloud.CLOUD_NAME:
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
        "x-csrftoken": csrf2[0]
    }
    payload = {}
    count = 0
    response_csrf = None
    while count < 60:
        try:
            isThere = False
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
        except:
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


def getDetailsOfServiceEngine(ip, csrf2, urlFromServiceEngine, file_name, aviVersion):
    url = urlFromServiceEngine
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    payload = {}
    count = 0
    response_csrf = None
    while count < 30:
        response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False, timeout=600)
        if response_csrf.status_code == 200:
            try:
                if len(response_csrf.json()["data_vnics"]) > 1:
                    break
                count = count + 1
                time.sleep(10)
                current_app.logger.info("Waited to get all the nics " + str(count * 10) + "s")
            except:
                pass
    if response_csrf is None:
        return None, "Failed"
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        json_object = json.dumps(response_csrf.json(), indent=4)
        os.system("rm -rf " + file_name)
        with open(file_name, "w") as outfile:
            outfile.write(json_object)
        return response_csrf.json(), 200


def changeMacAddressAndSeGroupInFile(vcenter_ip, vcenter_username, password, vm_name, segroupUrl, file_name):
    d = getMacAddresses(getSi(vcenter_ip, vcenter_username, password), vm_name)
    mac1 = d[1]
    mac2 = d[2]
    mac3 = d[3]
    replaceSeGroup(file_name, "se_group_ref", "false", segroupUrl)
    replaceMac(file_name, mac1)
    replaceMac(file_name, mac2)
    replaceMac(file_name, mac3)
    if Tkg_version.TKG_VERSION == "1.5":
        mac4 = d[4]
        replaceMac(file_name, mac4)


def changeMacAddressAndSeGroupInFileWorkload(vcenter_ip, vcenter_username, password, vm_name, segroupUrl, file_name,
                                             number):
    try:
        d = getMacAddresses(getSi(vcenter_ip, vcenter_username, password), vm_name)
    except:

        for i in tqdm(range(120), desc="Waiting for getting ip …", ascii=False, ncols=75):
            time.sleep(1)
        d = getMacAddresses(getSi(vcenter_ip, vcenter_username, password), vm_name)
    if number == 1:
        mac2 = d[1]
        replaceMac(file_name, mac2)
    else:
        mac3 = d[2]
        replaceMac(file_name, mac3)
    replaceSeGroup(file_name, "se_group_ref", "false", segroupUrl)


def generateConfigYaml(ip, datacenter, avi_version, datastoreName, cluster_name, wipIpNetmask, clusterWip, _vcenter_ip,
                       _vcenter_username,
                       _password, vmcSpec):
    if Tkg_version.TKG_VERSION == "1.5":
        template14MgmtDeployYaml(ip, datacenter, avi_version, datastoreName, cluster_name, wipIpNetmask, clusterWip,
                                 _vcenter_ip,
                                 _vcenter_username,
                                 _password, vmcSpec)
        # managementClusterYaml14(ip, datacenter, datastoreName, cluster_name, wipIpNetmask, clusterWip, _vcenter_ip,
        #                         _vcenter_username,
        #                         _password)
    elif Tkg_version.TKG_VERSION == "1.3":
        template13MgmtDeployYaml(ip, datacenter, datastoreName, cluster_name, wipIpNetmask, _vcenter_ip,
                                 _vcenter_username,
                                 _password, vmcSpec)
        managementClusterYaml13(ip, datacenter, datastoreName, cluster_name, wipIpNetmask, _vcenter_ip,
                                _vcenter_username,
                                _password)


def managementClusterYaml14(ip, datacenter, datastoreName, cluster_name, wipIpNetmask, clusterWip, _vcenter_ip,
                            _vcenter_username,
                            _password):
    getBase64CertWriteToFile(ip, "443")
    with open('cert.txt', 'r') as file2:
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
    TKG_HTTP_PROXY_ENABLED: "false"
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
    try:
        osName = str(request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtBaseOs'])
        if osName == "photon":
            osVersion = "3"
        elif osName == "ubuntu":
            osVersion = "20.04"
        else:
            raise Exception("Wrong os name provided")
    except Exception as e:
        raise Exception("Keyword " + str(e) + "  not found in input file")
    str_enc_avi = str(request.get_json(force=True)['componentSpec']['aviComponentSpec']['aviPasswordBase64'])
    base64_bytes = str_enc_avi.encode('ascii')
    enc_bytes = base64.b64decode(base64_bytes)
    password_avi = enc_bytes.decode('ascii').rstrip("\n")
    _base64_bytes = password_avi.encode('ascii')
    _enc_bytes = base64.b64encode(_base64_bytes)
    str_enc_avi = _enc_bytes.decode('ascii')
    management_cluster = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtClusterName']
    datastore_path = "/" + datacenter + "/datastore/" + datastoreName
    vsphere_folder_path = "/" + datacenter + "/vm/" + ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder
    mgmt_network = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtNetworkName']
    parent_resourcePool = current_app.config['RESOURCE_POOL']
    if parent_resourcePool:
        vsphere_rp = "/" + datacenter + "/host/" + cluster_name + "/Resources/" + parent_resourcePool + "/" + ResourcePoolAndFolderName.TKG_Mgmt_RP
    else:
        vsphere_rp = "/" + datacenter + "/host/" + cluster_name + "/Resources/" + ResourcePoolAndFolderName.TKG_Mgmt_RP
    _base64_bytes = _password.encode('ascii')
    _enc_bytes = base64.b64encode(_base64_bytes)
    str_enc = _enc_bytes.decode('ascii')
    vcenter_passwd = str_enc
    vcenter_ip = _vcenter_ip
    vcenter_username = _vcenter_username
    control_plan = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtDeploymentType']
    ssh_key = runSsh(vcenter_username)
    size = str(request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtSize'])
    clustercidr = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtClusterCidr']
    servicecidr = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtServiceCidr']
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
        current_app.logger.error("Un supported cluster size please specify small/medium/large/extra-large/custom " + size)
        d = {
            "responseType": "ERROR",
            "msg": "Un supported cluster size please specify small/medium/large/extra-large/custom " + size,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    avi_cluster_vip_name = Cloud.WIP_CLUSTER_NETWORK_NAME
    avi_cluster_vip_network_gateway_cidr = clusterWip
    file_name = "management_cluster_vmc.yaml"
    with open(file_name, 'w') as outfile:
        formatted = yaml_str % (
            cert, Cloud.CLOUD_NAME, ip, Cloud.WIP_NETWORK_NAME, wipIpNetmask, AkoType.KEY, AkoType.VALUE, str_enc_avi,
            Cloud.SE_GROUP_NAME, clustercidr,
            management_cluster, control_plan,
            servicecidr, datacenter, datastore_path, vsphere_folder_path, mgmt_network,
            vcenter_passwd, vsphere_rp, vcenter_ip, ssh_key, vcenter_username, size.lower(), size.lower(), osName,
            osVersion,
            avi_cluster_vip_name, avi_cluster_vip_network_gateway_cidr)
        data1 = yaml.load(formatted, Loader=yaml.RoundTripLoader)
        yaml.dump(data1, outfile, Dumper=yaml.RoundTripDumper, indent=2)


def template14MgmtDeployYaml(ip, datacenter, avi_version, datastoreName, cluster_name, wipIpNetmask, clusterWip,
                             vcenter_ip,
                             vcenter_username,
                             _password, vmcSpec):
    deploy_yaml = FileHelper.read_resource(Paths.TKG_MGMT_VMC_14_SPEC_J2)
    t = Template(deploy_yaml)
    getBase64CertWriteToFile(ip, "443")
    with open('cert.txt', 'r') as file2:
        cert = file2.readline()
    str_enc_avi = str(request.get_json(force=True)['componentSpec']['aviComponentSpec']['aviPasswordBase64'])
    base64_bytes = str_enc_avi.encode('ascii')
    enc_bytes = base64.b64decode(base64_bytes)
    password_avi = enc_bytes.decode('ascii').rstrip("\n")
    _base64_bytes = password_avi.encode('ascii')
    _enc_bytes = base64.b64encode(_base64_bytes)
    str_enc_avi = _enc_bytes.decode('ascii')
    _base64_bytes = _password.encode('ascii')
    _enc_bytes = base64.b64encode(_base64_bytes)
    str_enc = _enc_bytes.decode('ascii')
    vcenter_passwd = str_enc
    datastore_path = "/" + datacenter + "/datastore/" + datastoreName
    vsphere_folder_path = "/" + datacenter + "/vm/" + ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder
    parent_resourcePool = current_app.config['RESOURCE_POOL']
    if parent_resourcePool:
        vsphere_rp = "/" + datacenter + "/host/" + cluster_name + "/Resources/" + parent_resourcePool + "/" + ResourcePoolAndFolderName.TKG_Mgmt_RP
    else:
        vsphere_rp = "/" + datacenter + "/host/" + cluster_name + "/Resources/" + ResourcePoolAndFolderName.TKG_Mgmt_RP
    ssh_key = runSsh(vcenter_username)
    datacenter = "/" + datacenter
    size = vmcSpec.componentSpec.tkgMgmtSpec.tkgMgmtSize
    control_plane_vcpu = ""
    control_plane_disk_gb = ""
    control_plane_mem_gb = ""
    control_plane_mem_mb = ""
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
        control_plane_vcpu = request.get_json(force=True)['componentSpec']['tkgMgmtSpec'][
            'tkgMgmtCpuSize']
        control_plane_disk_gb = request.get_json(force=True)['componentSpec']['tkgMgmtSpec'][
            'tkgMgmtStorageSize']
        control_plane_mem_gb = request.get_json(force=True)['componentSpec']['tkgMgmtSpec'][
            'tkgMgmtMemorySize']
        control_plane_mem_mb = str(int(control_plane_mem_gb) * 1024)
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
    try:
        osName = str(request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtBaseOs'])
        if osName == "photon":
            osVersion = "3"
        elif osName == "ubuntu":
            osVersion = "20.04"
        else:
            raise Exception("Wrong os name provided")
    except Exception as e:
        raise Exception("Keyword " + str(e) + "  not found in input file")
    env = envCheck()
    env = env[0]
    ciep = str(request.get_json(force=True)["ceipParticipation"])
    if checkEnableIdentityManagement(env):
        try:
            identity_mgmt_type = str(
                request.get_json(force=True)["componentSpec"]["identityManagementSpec"]["identityManagementType"])
            if identity_mgmt_type.lower() == "oidc":
                oidc_provider_client_id = str(
                    request.get_json(force=True)["componentSpec"]["identityManagementSpec"]["oidcSpec"]["oidcClientId"])
                oidc_provider_client_secret = str(
                    request.get_json(force=True)["componentSpec"]["identityManagementSpec"]["oidcSpec"][
                        "oidcClientSecret"])
                oidc_provider_groups_claim = str(
                    request.get_json(force=True)["componentSpec"]["identityManagementSpec"]["oidcSpec"][
                        "oidcGroupsClaim"])
                oidc_provider_issuer_url = str(
                    request.get_json(force=True)["componentSpec"]["identityManagementSpec"]["oidcSpec"][
                        "oidcIssuerUrl"])
                ## TODO: check if provider name is required -- NOT REQUIRED
                # oidc_provider_name = str(request.get_json(force=True))
                oidc_provider_scopes = str(
                    request.get_json(force=True)["componentSpec"]["identityManagementSpec"]["oidcSpec"]["oidcScopes"])
                oidc_provider_username_claim = str(
                    request.get_json(force=True)["componentSpec"]["identityManagementSpec"]["oidcSpec"][
                        "oidcUsernameClaim"])
                FileHelper.write_to_file(
                    t.render(config=vmcSpec, cert=cert, ip=ip, wipIpNetmask=wipIpNetmask, avi_label_key=AkoType.KEY,
                             avi_label_value=AkoType.VALUE,ceip=ciep,
                             str_enc_avi=str_enc_avi, datacenter=datacenter, datastore_path=datastore_path,
                             vsphere_folder_path=vsphere_folder_path,
                             vcenter_passwd=vcenter_passwd, vsphere_rp=vsphere_rp, vcenter_ip=vcenter_ip,
                             ssh_key=ssh_key,
                             vcenter_username=vcenter_username,
                             control_plane_size=size.lower(), worker_size=size.lower(),
                             avi_cluster_vip_network_gateway_cidr=clusterWip, os_name=osName, os_version=osVersion,
                             size=size, control_plane_vcpu=control_plane_vcpu,
                             avi_version=avi_version,
                             control_plane_disk_gb=control_plane_disk_gb, control_plane_mem_mb=control_plane_mem_mb,
                             identity_mgmt_type=identity_mgmt_type, oidc_provider_client_id=oidc_provider_client_id,
                             oidc_provider_client_secret=oidc_provider_client_secret,
                             oidc_provider_groups_claim=oidc_provider_groups_claim,
                             oidc_provider_issuer_url=oidc_provider_issuer_url,
                             oidc_provider_scopes=oidc_provider_scopes,
                             oidc_provider_username_claim=oidc_provider_username_claim),
                    "management_cluster_vmc.yaml")
            elif identity_mgmt_type.lower() == "ldap":
                ldap_endpoint_ip = str(request.get_json(force=True)["componentSpec"]["identityManagementSpec"]
                                       ["ldapSpec"]["ldapEndpointIp"])
                ldap_endpoint_port = str(request.get_json(force=True)["componentSpec"]["identityManagementSpec"]
                                         ["ldapSpec"]["ldapEndpointPort"])
                str_enc = str(request.get_json(force=True)["componentSpec"]["identityManagementSpec"]["ldapSpec"][
                                  "ldapBindPWBase64"])
                base64_bytes = str_enc.encode('ascii')
                enc_bytes = base64.b64decode(base64_bytes)
                ldap_endpoint_bind_pw = enc_bytes.decode('ascii').rstrip("\n")
                ldap_bind_dn = str(
                    request.get_json(force=True)["componentSpec"]["identityManagementSpec"]["ldapSpec"]["ldapBindDN"])
                ldap_user_search_base_dn = str(
                    request.get_json(force=True)["componentSpec"]["identityManagementSpec"]
                    ["ldapSpec"]["ldapUserSearchBaseDN"])
                ldap_user_search_filter = str(request.get_json(force=True)["componentSpec"]
                                              ["identityManagementSpec"]["ldapSpec"]["ldapUserSearchFilter"])
                ldap_user_search_uname = str(request.get_json(force=True)["componentSpec"]
                                             ["identityManagementSpec"]["ldapSpec"]["ldapUserSearchUsername"])
                ldap_grp_search_base_dn = str(request.get_json(force=True)["componentSpec"]
                                              ["identityManagementSpec"]["ldapSpec"]["ldapGroupSearchBaseDN"])
                ldap_grp_search_filter = str(request.get_json(force=True)["componentSpec"]
                                             ["identityManagementSpec"]["ldapSpec"]["ldapGroupSearchFilter"])
                ldap_grp_search_user_attr = str(request.get_json(force=True)["componentSpec"]
                                                ["identityManagementSpec"]["ldapSpec"]["ldapGroupSearchUserAttr"])
                ldap_grp_search_grp_attr = str(request.get_json(force=True)["componentSpec"]
                                               ["identityManagementSpec"]["ldapSpec"]["ldapGroupSearchGroupAttr"])
                ldap_grp_search_name_attr = str(request.get_json(force=True)["componentSpec"]
                                                ["identityManagementSpec"]["ldapSpec"]["ldapGroupSearchNameAttr"])
                ldap_root_ca_data = str(request.get_json(force=True)["componentSpec"]
                                        ["identityManagementSpec"]["ldapSpec"]["ldapRootCAData"])
                if not ldap_user_search_base_dn:
                    current_app.logger.error("Please provide ldapUserSearchBaseDN for installing pinniped")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Please provide ldapUserSearchBaseDN for installing pinniped",
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
                if not ldap_grp_search_base_dn:
                    current_app.logger.error("Please provide ldapGroupSearchBaseDN for installing pinniped")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Please provide ldapGroupSearchBaseDN for installing pinniped",
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
                base64_bytes = base64.b64encode(ldap_root_ca_data.encode("utf-8"))
                ldap_root_ca_data_base64 = str(base64_bytes, "utf-8")
                FileHelper.write_to_file(
                    t.render(config=vmcSpec, cert=cert, ip=ip, wipIpNetmask=wipIpNetmask, avi_label_key=AkoType.KEY,
                             avi_label_value=AkoType.VALUE,ceip=ciep,
                             str_enc_avi=str_enc_avi, datacenter=datacenter, datastore_path=datastore_path,
                             vsphere_folder_path=vsphere_folder_path,
                             vcenter_passwd=vcenter_passwd, vsphere_rp=vsphere_rp, vcenter_ip=vcenter_ip,
                             ssh_key=ssh_key,
                             vcenter_username=vcenter_username,
                             control_plane_size=size.lower(), worker_size=size.lower(),
                             avi_cluster_vip_network_gateway_cidr=clusterWip, os_name=osName, os_version=osVersion,
                             size=size, control_plane_vcpu=control_plane_vcpu,
                             control_plane_disk_gb=control_plane_disk_gb,
                             control_plane_mem_mb=control_plane_mem_mb, identity_mgmt_type=identity_mgmt_type,
                             ldap_endpoint_ip=ldap_endpoint_ip, ldap_endpoint_port=ldap_endpoint_port,
                             ldap_endpoint_bind_pw=ldap_endpoint_bind_pw, ldap_bind_dn=ldap_bind_dn,
                             ldap_user_search_base_dn=ldap_user_search_base_dn,
                             ldap_user_search_filter=ldap_user_search_filter,
                             ldap_user_search_uname=ldap_user_search_uname,
                             ldap_grp_search_base_dn=ldap_grp_search_base_dn,
                             ldap_grp_search_filter=ldap_grp_search_filter,
                             ldap_grp_search_user_attr=ldap_grp_search_user_attr,
                             ldap_grp_search_grp_attr=ldap_grp_search_grp_attr,
                             ldap_grp_search_name_attr=ldap_grp_search_name_attr,
                             ldap_root_ca_data_base64=ldap_root_ca_data_base64),
                    "management_cluster_vmc.yaml")
            else:
                raise Exception("Wrong Identity Management type provided, accepted values are: oidc or ldap")
        except Exception as e:
            raise Exception("Keyword " + str(e) + "  not found in input file")
    else:
        FileHelper.write_to_file(
            t.render(config=vmcSpec, cert=cert, ip=ip, wipIpNetmask=wipIpNetmask, avi_label_key=AkoType.KEY,
                     avi_label_value=AkoType.VALUE,ceip=ciep,
                     str_enc_avi=str_enc_avi, datacenter=datacenter, datastore_path=datastore_path,
                     vsphere_folder_path=vsphere_folder_path,
                     vcenter_passwd=vcenter_passwd, vsphere_rp=vsphere_rp, vcenter_ip=vcenter_ip, ssh_key=ssh_key,
                     vcenter_username=vcenter_username,
                     control_plane_size=size.lower(), worker_size=size.lower(),
                     avi_cluster_vip_network_gateway_cidr=clusterWip, os_name=osName, os_version=osVersion,
                     size=size, control_plane_vcpu=control_plane_vcpu, control_plane_disk_gb=control_plane_disk_gb,
                     control_plane_mem_mb=control_plane_mem_mb),
            "management_cluster_vmc.yaml")


def managementClusterYaml13(ip, datacenter, datastoreName, cluster_name, wipIpNetmask, _vcenter_ip, _vcenter_username,
                            _password):
    getBase64CertWriteToFile(ip, "443")
    with open('cert.txt', 'r') as file2:
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
    TKG_HTTP_PROXY_ENABLED: "false"
    VSPHERE_CONTROL_PLANE_DISK_GIB: "40"
    VSPHERE_CONTROL_PLANE_ENDPOINT: %s
    VSPHERE_CONTROL_PLANE_MEM_MIB: "16384"
    DEPLOY_TKG_ON_VSPHERE7: "true"
    VSPHERE_CONTROL_PLANE_NUM_CPUS: "4"
    VSPHERE_DATACENTER: /%s
    VSPHERE_DATASTORE: %s
    VSPHERE_FOLDER: %s
    VSPHERE_NETWORK: %s
    VSPHERE_PASSWORD: <encoded:%s>
    VSPHERE_RESOURCE_POOL: %s
    VSPHERE_SERVER: %s
    VSPHERE_SSH_AUTHORIZED_KEY: %s
    VSPHERE_USERNAME: %s
    VSPHERE_WORKER_DISK_GIB: "40"
    VSPHERE_WORKER_MEM_MIB: "16384"
    VSPHERE_WORKER_NUM_CPUS: "4"
    """
    str_enc_avi = str(request.get_json(force=True)['componentSpec']['aviComponentSpec']['aviPasswordBase64'])
    base64_bytes = str_enc_avi.encode('ascii')
    enc_bytes = base64.b64decode(base64_bytes)
    password_avi = enc_bytes.decode('ascii').rstrip("\n")
    _base64_bytes = password_avi.encode('ascii')
    _enc_bytes = base64.b64encode(_base64_bytes)
    str_enc_avi = _enc_bytes.decode('ascii')
    management_cluster = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtClusterName']
    vsphere_cntrol_plane_ip = request.get_json(force=True)['componentSpec']['tkgMgmtSpec'][
        'TKG_Mgmt_ControlPlane_IP']
    datastore_path = "/" + datacenter + "/datastore/" + datastoreName
    vsphere_folder_path = "/" + datacenter + "/vm/" + ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder
    mgmt_network = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtNetworkName']
    vsphere_rp = "/" + datacenter + "/host/" + cluster_name + "/Resources/" + ResourcePoolAndFolderName.TKG_Mgmt_RP
    _base64_bytes = _password.encode('ascii')
    _enc_bytes = base64.b64encode(_base64_bytes)
    str_enc = _enc_bytes.decode('ascii')
    vcenter_passwd = str_enc
    vcenter_ip = _vcenter_ip
    vcenter_username = _vcenter_username
    control_plan = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtDeploymentType']
    ssh_key = runSsh(vcenter_username)
    file_name = "management_cluster_vmc.yaml"
    with open(file_name, 'w') as outfile:
        formatted = yaml_str % (
            cert, Cloud.CLOUD_NAME, ip, Cloud.WIP_NETWORK_NAME, wipIpNetmask, AkoType.KEY, AkoType.VALUE, str_enc_avi,
            Cloud.SE_GROUP_NAME, CIDR.CLUSTER_CIDR,
            management_cluster, control_plan,
            CIDR.SERVICE_CIDR, vsphere_cntrol_plane_ip, datacenter, datastore_path, vsphere_folder_path, mgmt_network,
            vcenter_passwd, vsphere_rp, vcenter_ip, ssh_key, vcenter_username)
        data1 = yaml.load(formatted, Loader=yaml.RoundTripLoader)
        yaml.dump(data1, outfile, Dumper=yaml.RoundTripDumper, indent=2)


def template13MgmtDeployYaml(ip, datacenter, datastoreName, cluster_name, wipIpNetmask, vcenter_ip,
                             vcenter_username,
                             _password, vmcSpec):
    deploy_yaml = FileHelper.read_resource(Paths.TKG_MGMT_VMC_13_SPEC_J2)
    t = Template(deploy_yaml)
    getBase64CertWriteToFile(ip, "443")
    with open('cert.txt', 'r') as file2:
        cert = file2.readline()
    str_enc_avi = str(request.get_json(force=True)['componentSpec']['aviComponentSpec']['aviPasswordBase64'])
    base64_bytes = str_enc_avi.encode('ascii')
    enc_bytes = base64.b64decode(base64_bytes)
    password_avi = enc_bytes.decode('ascii').rstrip("\n")
    _base64_bytes = password_avi.encode('ascii')
    _enc_bytes = base64.b64encode(_base64_bytes)
    str_enc_avi = _enc_bytes.decode('ascii')
    _base64_bytes = _password.encode('ascii')
    _enc_bytes = base64.b64encode(_base64_bytes)
    str_enc = _enc_bytes.decode('ascii')
    vcenter_passwd = str_enc
    vsphere_cntrol_plane_ip = request.get_json(force=True)['componentSpec']['tkgMgmtSpec'][
        'TKG_Mgmt_ControlPlane_IP']
    datastore_path = "/" + datacenter + "/datastore/" + datastoreName
    vsphere_folder_path = "/" + datacenter + "/vm/" + ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder
    vsphere_rp = "/" + datacenter + "/host/" + cluster_name + "/Resources/" + ResourcePoolAndFolderName.TKG_Mgmt_RP
    ssh_key = runSsh(vcenter_username)
    datacenter = "/" + datacenter
    FileHelper.write_to_file(
        t.render(config=vmcSpec, cert=cert, ip=ip, wipIpNetmask=wipIpNetmask, avi_label_key=AkoType.KEY,
                 avi_label_value=AkoType.VALUE,
                 str_enc_avi=str_enc_avi, vsphere_cntrol_plane_ip=vsphere_cntrol_plane_ip, datacenter=datacenter,
                 datastore_path=datastore_path,
                 vsphere_folder_path=vsphere_folder_path, vcenter_passwd=vcenter_passwd, vsphere_rp=vsphere_rp,
                 vcenter_ip=vcenter_ip,
                 ssh_key=ssh_key, vcenter_username=vcenter_username),
        cluster_name + ".yaml")


def deployManagementCluster(management_cluster, avi_version, ip, data_center, data_store, cluster_name, wipIpNetmask,
                            clusterWip,
                            vcenter_ip,
                            vcenter_username, password, vmcSpec):
    try:
        if not getClusterStatusOnTanzu(management_cluster, "management"):
            os.system("rm -rf kubeconfig.yaml")
            generateConfigYaml(ip, data_center, avi_version, data_store, cluster_name, wipIpNetmask, clusterWip,
                               vcenter_ip,
                               vcenter_username,
                               password, vmcSpec)
            current_app.logger.info("Deploying management cluster on vmc")
            os.putenv("DEPLOY_TKG_ON_VSPHERE7", "true")
            listOfCmd = ["tanzu", "management-cluster", "create", "-y", "--file", "management_cluster_vmc.yaml", "-v",
                         "6"]
            runProcess(listOfCmd)
            listOfCmdKube = ["tanzu", "management-cluster", "kubeconfig", "get", management_cluster, "--admin",
                             "--export-file",
                             "kubeconfig.yaml"]
            runProcess(listOfCmdKube)
            return "SUCCESS", 200
        else:
            return "SUCCESS", 200
    except Exception as e:
        return None, str(e)


def switchContextAndApplyAko(management_cluster):
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
    applyAkoCmd = ["kubectl", "apply", "-f", "ako_workloadset1.yaml"]
    status = runShellCommandAndReturnOutputAsList(applyAkoCmd)
    if status[1] != 0:
        current_app.logger.error("Failed apply ako " + str(status[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed apply ako " + str(status[0]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def changeSeGroupAndSetInterfaces(ip, csrf2, urlFromServiceEngine, se_cloud_url, file_name, vcenter_ip,
                                  vcenter_username, password,
                                  vm_name, type, name, aviVersion):
    if type == Type.WORKLOAD:
        changeMacAddressAndSeGroupInFileWorkload(vcenter_ip, vcenter_username, password, vm_name, se_cloud_url,
                                                 file_name, name)
    else:
        changeMacAddressAndSeGroupInFile(vcenter_ip, vcenter_username, password, vm_name, se_cloud_url, file_name)
    url = urlFromServiceEngine
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    with open(file_name, 'r') as openfile:
        json_object = json.load(openfile)
    json_object_m = json.dumps(json_object, indent=4)
    response_csrf = requests.request("PUT", url, headers=headers, data=json_object_m, verify=False, timeout=600)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        return response_csrf.json(), 200


def seperateNetmaskAndIp(cidr):
    return str(cidr).split("/")
