from flask import Blueprint
import logging
from flask import jsonify, request
from flask import current_app
import sys
import time
import requests
import base64
import json
from tqdm import tqdm
from ruamel import yaml
from common.util.file_helper import FileHelper
from common.operation.constants import Paths
from common.model.vsphereSpec import VsphereMasterSpec
from common.util.ssl_helper import get_base64_cert
from jinja2 import Template

logger = logging.getLogger(__name__)
vsphere_management_config = Blueprint("vsphere_management_config", __name__, static_folder="managementConfig")

sys.path.append(".../")
from common.operation.vcenter_operations import createResourcePool, create_folder, checkforIpAddress, getSi, \
    getMacAddresses
from common.operation.constants import ResourcePoolAndFolderName, Cloud, AkoType, CIDR, TmcUser, Type, Avi_Version, \
    RegexPattern, Env, KubernetesOva
import os
from common.common_utilities import isAviHaEnabled, create_virtual_service, checkAndWaitForAllTheServiceEngineIsUp, \
    createSubscribedLibrary, \
    preChecks, registerWithTmc, get_avi_version, runSsh, \
    getCloudStatus, \
    getSECloudStatus, envCheck, getClusterStatusOnTanzu, getVipNetworkIpNetMask, getVrfAndNextRoutId, addStaticRoute, \
    VrfType, checkMgmtProxyEnabled, enableProxy, disable_proxy, checkAirGappedIsEnabled, loadBomFile, grabPortFromUrl, \
    grabHostFromUrl, checkTmcEnabled, registerTMCTKGs, downloadAndPushKubernetesOvaMarketPlace, \
    VrfType, checkMgmtProxyEnabled, enableProxy, checkAirGappedIsEnabled, loadBomFile, grabPortFromUrl, \
    grabHostFromUrl, checkTmcEnabled, registerTMCTKGs, obtain_second_csrf, isEnvTkgs_ns, isEnvTkgs_wcp, \
    obtain_avi_version, \
    configureKubectl, getClusterID, checkEnableIdentityManagement, switchToManagementContext, checkPinnipedInstalled, \
    checkPinnipedServiceStatus, checkPinnipedDexServiceStatus, createRbacUsers, createClusterFolder
from common.certificate_base64 import getBase64CertWriteToFile
from common.replace_value import generateVsphereConfiguredSubnets, generateVsphereConfiguredSubnetsForSe, \
    replaceValueSysConfig, replaceSeGroup, replaceMac
from common.operation.ShellHelper import runShellCommandAndReturnOutput, runShellCommandWithPolling, grabKubectlCommand, \
    runShellCommandAndReturnOutputAsList, runProcess, verifyPodsAreRunning
from common.operation.constants import ControllerLocation, Tkg_version
from vsphere.managementConfig.vsphere_tkgs_management_config import configTkgsCloud, enableWCP, \
    configureTkgConfiguration
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


@vsphere_management_config.route("/api/tanzu/vsphere/tkgmgmt", methods=['POST'])
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


@vsphere_management_config.route("/api/tanzu/vsphere/tkgmgmt/alb/config", methods=['POST'])
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
    # aviVersion = get_avi_version(env)
    password = current_app.config['VC_PASSWORD']
    vcenter_username = current_app.config['VC_USER']
    vcenter_ip = current_app.config['VC_IP']
    cluster_name = current_app.config['VC_CLUSTER']
    data_center = current_app.config['VC_DATACENTER']
    data_store = current_app.config['VC_DATASTORE']
    req = True
    refToken = request.get_json(force=True)['envSpec']['marketplaceSpec']['refreshToken']
    if refToken and (env == Env.VSPHERE or env == Env.VCF):
        if not (isEnvTkgs_wcp(env) or isEnvTkgs_ns(env)):
            kubernetes_ova_os = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtBaseOs"]
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
        current_app.logger.info("MarketPlace refresh token is not provided, skipping the download of kubernetes ova")
    if isEnvTkgs_wcp(env):
        avi_fqdn = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController01Fqdn']
        ip_ = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviClusterIp']
        if isAviHaEnabled(env):
            aviClusterFqdn = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviClusterFqdn']

    else:
        avi_fqdn = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController01Fqdn']
        aviClusterFqdn = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviClusterFqdn']
    if not avi_fqdn:
        controller_name = ControllerLocation.CONTROLLER_NAME_VSPHERE
    else:
        controller_name = avi_fqdn
    if isAviHaEnabled(env):
        ip = aviClusterFqdn
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
    deployed_avi_version = obtain_avi_version(ip, env)
    if deployed_avi_version[0] is None:
        current_app.logger.error("Failed to login and obtain avi version" + str(deployed_avi_version[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to login and obtain avi version " + deployed_avi_version[1],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    aviVersion = deployed_avi_version[0]
    default = waitForCloudPlacementReady(ip, csrf2, "Default-Cloud", aviVersion)
    if default[0] is None:
        current_app.logger.error("Failed to get default cloud status")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get default cloud status",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if isEnvTkgs_wcp(env):
        configTkgs = configTkgsCloud(ip, csrf2, aviVersion)
        if configTkgs[0] is None:
            current_app.logger.error("Failed to config tkgs " + str(configTkgs[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to config tkgs " + str(configTkgs[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    else:
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
            if req:
                for i in tqdm(range(60), desc="Waiting…", ascii=False, ncols=75):
                    time.sleep(1)
            isGen = True
            current_app.logger.info("Creating New cloud " + Cloud.CLOUD_NAME_VSPHERE)
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
        if isGen:
            for i in tqdm(range(60), desc="Waiting…", ascii=False, ncols=75):
                time.sleep(1)
        mgmt_pg = request.get_json(force=True)['tkgComponentSpec']['aviMgmtNetwork']['aviMgmtNetworkName']
        get_management = getNetworkUrl(ip, csrf2, mgmt_pg, aviVersion)
        if get_management[0] is None:
            current_app.logger.error("Failed to get management network " + str(get_management[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get management network " + str(get_management[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        startIp = request.get_json(force=True)["tkgComponentSpec"]["aviMgmtNetwork"][
            "aviMgmtServiceIpStartRange"]
        endIp = request.get_json(force=True)["tkgComponentSpec"]["aviMgmtNetwork"]["aviMgmtServiceIpEndRange"]
        prefixIpNetmask = seperateNetmaskAndIp(
            request.get_json(force=True)["tkgComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkGatewayCidr"])
        getManagementDetails = getNetworkDetails(ip, csrf2, get_management[0], startIp, endIp, prefixIpNetmask[0],
                                                 prefixIpNetmask[1], aviVersion)
        if getManagementDetails[0] is None:
            current_app.logger.error("Failed to get management network details " + str(getManagementDetails[2]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get management network details " + str(getManagementDetails[2]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        if getManagementDetails[0] == "AlreadyConfigured":
            current_app.logger.info("Ip pools are already configured.")
            vim_ref = getManagementDetails[2]["vim_ref"]
            ip_pre = getManagementDetails[2]["subnet_ip"]
            mask = getManagementDetails[2]["subnet_mask"]
        else:
            update_resp = updateNetworkWithIpPools(ip, csrf2, get_management[0], "managementNetworkDetails.json",
                                                   aviVersion)
            if update_resp[0] != 200:
                current_app.logger.error("Failed to update management network ip pools " + str(update_resp[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to update management network ip pools " + str(update_resp[1]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            vim_ref = update_resp[2]["vimref"]
            mask = update_resp[2]["subnet_mask"]
            ip_pre = update_resp[2]["subnet_ip"]
        new_cloud_status = getDetailsOfNewCloud(ip, csrf2, cloud_url, vim_ref, ip_pre, mask, aviVersion)
        if new_cloud_status[0] is None:
            current_app.logger.error("Failed to get new cloud details" + str(new_cloud_status[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get new cloud details " + str(new_cloud_status[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        updateNewCloudStatus = updateNewCloud(ip, csrf2, cloud_url, aviVersion)
        if updateNewCloudStatus[0] is None:
            current_app.logger.error("Failed to update cloud " + str(updateNewCloudStatus[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to update cloud " + str(updateNewCloudStatus[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        mgmt_data_pg = request.get_json(force=True)['tkgMgmtDataNetwork']['tkgMgmtDataNetworkName']
        get_management_data_pg = getNetworkUrl(ip, csrf2, mgmt_data_pg, aviVersion)
        if get_management_data_pg[0] is None:
            current_app.logger.error("Failed to get management data network details " + str(get_management_data_pg[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get management data network details " + str(get_management_data_pg[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        startIp = request.get_json(force=True)["tkgMgmtDataNetwork"]["tkgMgmtAviServiceIpStartRange"]
        endIp = request.get_json(force=True)["tkgMgmtDataNetwork"]["tkgMgmtAviServiceIpEndRange"]
        prefixIpNetmask = seperateNetmaskAndIp(
            request.get_json(force=True)["tkgMgmtDataNetwork"]["tkgMgmtDataNetworkGatewayCidr"])
        getManagementDetails_data_pg = getNetworkDetails(ip, csrf2, get_management_data_pg[0], startIp, endIp,
                                                         prefixIpNetmask[0], prefixIpNetmask[1], aviVersion)
        if getManagementDetails_data_pg[0] is None:
            current_app.logger.error(
                "Failed to get management data network details " + str(getManagementDetails_data_pg[2]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get management data network details " + str(getManagementDetails_data_pg[2]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        if getManagementDetails_data_pg[0] == "AlreadyConfigured":
            current_app.logger.info("Ip pools are already configured.")
        else:
            update_resp = updateNetworkWithIpPools(ip, csrf2, get_management_data_pg[0],
                                                   "managementNetworkDetails.json",
                                                   aviVersion)
            if update_resp[0] != 200:
                current_app.logger.error("Failed to update management network details " + str(update_resp[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to update management network details " + str(update_resp[1]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
        mgmt_pg = request.get_json(force=True)['tkgComponentSpec']['tkgClusterVipNetwork'][
            'tkgClusterVipNetworkName']
        get_vip = getNetworkUrl(ip, csrf2, mgmt_pg, aviVersion)
        if get_vip[0] is None:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get vip network " + str(get_vip[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        vip_pool = updateVipNetworkIpPools(ip, csrf2, get_vip, aviVersion)
        if vip_pool[1] != 200:
            current_app.logger.error(str(vip_pool[0].json['msg']))
            d = {
                "responseType": "ERROR",
                "msg": str(vip_pool[0].json['msg']),
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

        isGen = False
        if get_ipam[0] == "NOT_FOUND":
            isGen = True
            current_app.logger.info("Creating IPam " + Cloud.IPAM_NAME_VSPHERE)
            ipam = createIpam(ip, csrf2, get_management[0], get_management_data_pg[0], get_vip[0],
                              Cloud.IPAM_NAME_VSPHERE,
                              aviVersion)
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

        new_cloud_status = getDetailsOfNewCloudAddIpam(ip, csrf2, cloud_url, ipam_url, aviVersion)
        if new_cloud_status[0] is None:
            current_app.logger.error("Failed to get new cloud details" + str(new_cloud_status[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get new cloud details " + str(new_cloud_status[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        updateIpam_re = updateIpam(ip, csrf2, cloud_url, aviVersion)
        if updateIpam_re[0] is None:
            current_app.logger.error("Failed to update ipam to cloud " + str(updateIpam_re[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to update ipam to cloud " + str(updateIpam_re[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
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
        get_se_cloud = getSECloudStatus(ip, csrf2, aviVersion, Cloud.SE_GROUP_NAME_VSPHERE)
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
            current_app.logger.info("Creating New se cloud " + Cloud.SE_GROUP_NAME_VSPHERE)
            cloud_se = createSECloud(ip, csrf2, cloud_url, Cloud.SE_GROUP_NAME_VSPHERE, cluster_status[0], data_store,
                                     aviVersion)
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
        mgmt_name = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtNetworkName"]
        dhcp = enableDhcpForManagementNetwork(ip, csrf2, mgmt_name, aviVersion)
        if dhcp[0] is None:
            current_app.logger.error("Failed to enable dhcp " + str(dhcp[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to enable dhcp " + str(dhcp[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        if env == Env.VCF:
            shared_service_name = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                'tkgSharedserviceNetworkName']
            dhcp = enableDhcpForSharedNetwork(ip, csrf2, shared_service_name, aviVersion)
            if dhcp[0] is None:
                current_app.logger.error("Failed to enable dhcp " + str(dhcp[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to enable dhcp " + str(dhcp[1]),
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
            return None, "NOT_FOUND"
        ipNetMask = seperateNetmaskAndIp(
            request.get_json(force=True)["tkgComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkGatewayCidr"])
        vrf = getVrfAndNextRoutId(ip, csrf2, uuid, VrfType.MANAGEMENT, ipNetMask[0], aviVersion)
        if vrf[0] is None or vrf[1] == "NOT_FOUND":
            current_app.logger.error("Vrf not found " + str(vrf[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Vrf not found " + str(vrf[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        if vrf[1] != "Already_Configured":
            ad = addStaticRoute(ip, csrf2, vrf[0], ipNetMask[0], vrf[1], aviVersion)
            if ad[0] is None:
                current_app.logger.error("Failed to add static route " + str(ad[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Vrf not found " + str(ad[1]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
        prefixIpNetmask_vip = seperateNetmaskAndIp(
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
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            if vrf[1] != "Already_Configured":
                ad = addStaticRoute(ip, csrf2, vrf[0], l, vrf[1], aviVersion)
                if ad[0] is None:
                    current_app.logger.error("Failed to add static route " + str(ad[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Vrf not found " + str(ad[1]),
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
        virtual_service, error = create_virtual_service(ip, csrf2, uuid, Cloud.SE_GROUP_NAME_VSPHERE, get_vip[0], 2,
                                                        aviVersion)
        if virtual_service is None:
            current_app.logger.error("Failed to create virtual service " + str(error))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create virtual service " + str(error),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    current_app.logger.info("Configured management cluster cloud successfully")
    d = {
        "responseType": "SUCCESS",
        "msg": "Configured management cluster cloud successfully",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


@vsphere_management_config.route("/api/tanzu/vsphere/enablewcp", methods=['POST'])
def enable_wcp():
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
    if not isEnvTkgs_wcp(env):
        current_app.logger.error("Wrong env provided wcp can  only be  enabled on TKGS")
        d = {
            "responseType": "ERROR",
            "msg": "Wrong env provided wcp can  only be  enabled on TKGS",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    # aviVersion = get_avi_version(env)
    password = current_app.config['VC_PASSWORD']
    vcenter_username = current_app.config['VC_USER']
    vcenter_ip = current_app.config['VC_IP']
    cLib = createSubscribedLibrary(vcenter_ip, vcenter_username, password, env)
    if cLib[0] is None:
        current_app.logger.error("Failed to create content library " + str(cLib[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create content library " + str(cLib[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    avi_fqdn = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController01Fqdn']
    if not avi_fqdn:
        controller_name = ControllerLocation.CONTROLLER_NAME_VSPHERE
    else:
        controller_name = avi_fqdn
    if isAviHaEnabled(env):
        ip = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviClusterFqdn']
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

    avi_ip = checkforIpAddress(getSi(vcenter_ip, vcenter_username, password), avi_fqdn)
    if avi_ip is None:
        current_app.logger.error("Failed to get ip of avi controller")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get ip of avi controller",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    deployed_avi_version = obtain_avi_version(avi_ip, env)
    if deployed_avi_version[0] is None:
        current_app.logger.error("Failed to login and obtain avi version" + str(deployed_avi_version[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to login and obtain avi version " + deployed_avi_version[1],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    aviVersion = deployed_avi_version[0]

    enable = enableWCP(ip, csrf2, aviVersion)
    if enable[0] is None:
        current_app.logger.error("Failed to enable wcp " + str(enable[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to configure wcp " + str(enable[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    isUp = checkAndWaitForAllTheServiceEngineIsUp(ip, Cloud.DEFAULT_CLOUD_NAME_VSPHERE, env, aviVersion)
    if isUp[0] is None:
        current_app.logger.error("All service engines are not up, check your network configuration " + str(isUp[1]))
        d = {
            "responseType": "ERROR",
            "msg": "All service engines are not up, check your network configuration " + str(isUp[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    current_app.logger.info("Setting up kubectl vsphere plugin...")
    url_ = "https://" + vcenter_ip + "/"
    sess = requests.post(url_ + "rest/com/vmware/cis/session", auth=(vcenter_username, password), verify=False)
    if sess.status_code != 200:
        d = {
            "responseType": "ERROR",
            "msg": "Failed to fetch session ID for vCenter - " + vcenter_ip,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    else:
        session_id = sess.json()['value']

    header = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "vmware-api-session-id": session_id
    }
    cluster_name = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterCluster"]
    id = getClusterID(vcenter_ip, vcenter_username, password, cluster_name)
    if id[1] != 200:
        return None, id[0]
    clusterip_resp = requests.get(url_ + "api/vcenter/namespace-management/clusters/" + str(id[0]), verify=False,
                                  headers=header)
    if clusterip_resp.status_code != 200:
        d = {
            "responseType": "ERROR",
            "msg": "Failed to fetch API server cluster endpoint - " + vcenter_ip,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    cluster_endpoint = clusterip_resp.json()["api_server_cluster_endpoint"]
    current_app.logger.info("Waiting for 2 min status == ready")
    time.sleep(120)
    configure_kubectl = configureKubectl(cluster_endpoint)
    if configure_kubectl[1] != 200:
        current_app.logger.error(configure_kubectl[0])
        d = {
            "responseType": "ERROR",
            "msg": configure_kubectl[0],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    current_app.logger.info("Configured Wcp successfully")
    configTkgs, message = configureTkgConfiguration(vcenter_username, password, cluster_endpoint)
    if configTkgs is None:
        d = {
            "responseType": "ERROR",
            "msg": "Failed to configure tkgs service configuration " + str(message),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    if checkTmcEnabled(env):
        tmc_register_response = registerTMCTKGs(vcenter_ip, vcenter_username, password)
        if tmc_register_response[1] != 200:
            current_app.logger.error("Supervisor cluster TMC registration failed " + str(tmc_register_response[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Supervisor cluster TMC registration failed " + str(tmc_register_response[0]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        else:
            current_app.logger.info("TMC registration successful")
    else:
        current_app.logger.info("Skipping TMC registration, as tmcAvailability is set to False")
    d = {
        "responseType": "SUCCESS",
        "msg": "Configured Wcp successfully",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def updateIpam(ip, csrf2, newCloudUrl, aviVersion):
    with open("./detailsOfNewCloudIpam.json", 'r') as file2:
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


def enableDhcpForManagementNetwork(ip, csrf2, name, aviVersion):
    getNetwork = getNetworkUrl(ip, csrf2, name, aviVersion)
    if getNetwork[0] is None:
        current_app.logger.error("Failed to network url " + name)
        d = {
            "responseType": "ERROR",
            "msg": "Failed to network url " + name,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    details = getNetworkDetailsDhcp(ip, csrf2, getNetwork[0], aviVersion)
    if details[0] is None:
        current_app.logger.error("Failed to network details " + details[1])
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get network details " + details[1],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    with open('./managementNetworkDetailsDhcp.json', 'r') as openfile:
        json_object = json.load(openfile)
    json_object_m = json.dumps(json_object, indent=4)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    response_csrf = requests.request("PUT", getNetwork[0], headers=headers, data=json_object_m, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    return "SUCCESS", 200


def enableDhcpForSharedNetwork(ip, csrf2, name, aviVersion):
    getNetwork = getNetworkUrl(ip, csrf2, name, aviVersion)
    if getNetwork[0] is None:
        current_app.logger.error("Failed to network url " + name)
        d = {
            "responseType": "ERROR",
            "msg": "Failed to network url " + name,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    details = getNetworkDetailsSharedDhcp(ip, csrf2, getNetwork[0], aviVersion)
    if details[0] is None:
        current_app.logger.error("Failed to network details " + details[1])
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get network details " + details[1],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    with open('./sharedNetworkDetailsDhcp.json', 'r') as openfile:
        json_object = json.load(openfile)
    json_object_m = json.dumps(json_object, indent=4)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
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
        "x-csrftoken": csrf2[0]
    }
    url = "https://" + ip + "/api/vimgrclusterruntime"
    payload = {}
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        if str(cluster_name).__contains__("/"):
            cluster_name = cluster_name[cluster_name.rindex("/")+1:]
        for cluster in response_csrf.json()["results"]:
            if cluster["name"] == cluster_name:
                return cluster["url"], "SUCCESS"

        return "NOT_FOUND", "FAILED"


@vsphere_management_config.route("/api/tanzu/vsphere/tkgmgmt/config", methods=['POST'])
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
    vsSpec = VsphereMasterSpec.parse_obj(json_dict)
    env = env[0]
    aviVersion = get_avi_version(env)
    password = current_app.config['VC_PASSWORD']
    vcenter_username = current_app.config['VC_USER']
    vcenter_ip = current_app.config['VC_IP']
    cluster_name = current_app.config['VC_CLUSTER']
    data_center = current_app.config['VC_DATACENTER']
    data_store = current_app.config['VC_DATASTORE']
    parent_resourcepool = current_app.config['RESOURCE_POOL']
    try:
        isCreated5 = createResourcePool(vcenter_ip, vcenter_username, password,
                                        cluster_name,
                                        ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE, parent_resourcepool, data_center)
        if isCreated5 is not None:
            current_app.logger.info("Created resource pool " + ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE)
    except Exception as e:
        current_app.logger.error("Failed to create resource pool " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create resource pool " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    try:
        isCreated3 = create_folder(vcenter_ip, vcenter_username, password,
                                   data_center,
                                   ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder_VSPHERE)
        if isCreated3 is not None:
            current_app.logger.info("Created folder " + ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder_VSPHERE)

    except Exception as e:
        current_app.logger.error("Failed to create folder " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create folder " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
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
    data_network = request.get_json(force=True)["tkgMgmtDataNetwork"]["tkgMgmtDataNetworkName"]
    get_wip = getVipNetworkIpNetMask(ip, csrf2, data_network, aviVersion)
    if get_wip[0] is None or get_wip[0] == "NOT_FOUND":
        current_app.logger.error("Failed to get se vip network ip and netmask " + str(get_wip[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get vip network " + str(get_wip[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    management_cluster = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
        'tkgMgmtClusterName']
    avi_ip = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController01Ip']
    avi_fqdn = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController01Fqdn']
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
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    current_app.logger.info(
        "The config files for management cluster will be located at: " + Paths.CLUSTER_PATH + management_cluster)
    current_app.logger.info("Deploying Management Cluster " + management_cluster)
    deploy_status = deployManagementCluster(management_cluster, controller_fqdn, data_center, data_store, cluster_name,
                                            data_network,
                                            get_wip[0],
                                            vcenter_ip, vcenter_username, aviVersion, password, env, vsSpec)
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
                request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["identityManagementType"])
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
                request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec'][
                    'clusterAdminUsers']
            admin_users = \
                request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec'][
                    'adminUsers']
            edit_users = \
                request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec'][
                    'editUsers']
            view_users = \
                request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec'][
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

    tmc_required = str(request.get_json(force=True)['envSpec']["saasEndpoints"]['tmcDetails']['tmcAvailability'])
    if tmc_required.lower() == "true":
        current_app.logger.info("TMC registration is enabled")
    elif tmc_required.lower() == "false":
        current_app.logger.info("Tmc registration is disabled")
    else:
        current_app.logger.error("Wrong tmc selection attribute provided " + tmc_required)
        d = {
            "responseType": "ERROR",
            "msg": "Wrong tmc selection attribute provided " + tmc_required,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if not checkAirGappedIsEnabled(env):
        if checkTmcEnabled(env):
            if Tkg_version.TKG_VERSION == "1.5":
                current_app.logger.info("TMC registration on management cluster is supported on tanzu 1.5")
                clusterGroup = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                    'tkgMgmtClusterGroupName']
                if not clusterGroup:
                    clusterGroup = "default"
                if checkMgmtProxyEnabled(env):
                    state = registerWithTmc(management_cluster, env, "true", "management", clusterGroup)
                else:
                    state = registerWithTmc(management_cluster, env, "false", "management", clusterGroup)
                if state[0] is None:
                    current_app.logger.error("Failed to register on tmc " + state[1])
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to register on tmc " + state[1],
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
    if checkAirGappedIsEnabled(env):
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
            current_app.logger.error("Failed to switch to management cluster context " + str(status[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to switch to management cluster context " + str(status[0]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        air_gapped_repo = str(
            request.get_json(force=True)['envSpec']['customRepositorySpec']['tkgCustomImageRepository'])
        air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
        bom = loadBomFile()
        if bom is None:
            current_app.logger.error("Failed to load bom")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to load bom",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        try:
            tag = bom['components']['kube_rbac_proxy'][0]['images']['kubeRbacProxyControllerImage']['tag']
        except Exception as e:
            current_app.logger.error("Failed to load bom key " + str(e))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to load bom key " + str(e),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        kube = air_gapped_repo + "/kube-rbac-proxy:" + tag
        spec = "{\"spec\": {\"template\": {\"spec\": {\"containers\": [{\"name\": \"kube-rbac-proxy\",\"image\": \"" + kube + "\"}]}}}}"
        command = ["kubectl", "patch", "deployment", "ako-operator-controller-manager", "-n", "tkg-system-networking",
                   "--patch", spec]
        status = runShellCommandAndReturnOutputAsList(command)
        if status[1] != 0:
            current_app.logger.error("Failed to patch ako operator " + str(status[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to patch ako operator " + str(status[0]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    d = {
        "responseType": "SUCCESS",
        "msg": "Successfully configured management cluster ",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def referenceTkgMNetwork(ip, csrf2, url, aviVersion):
    reference_TKG_Mgmt_Network_ipNetmask = seperateNetmaskAndIp(
        request.get_json(force=True)['tkgComponentSpec']['aviMgmtNetwork'][
            'aviMgmtNetworkGatewayCidr'])
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
                            "addr": reference_TKG_Mgmt_Network_ipNetmask[0], "type": "V4"},
                        "mask": reference_TKG_Mgmt_Network_ipNetmask[1]
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


def waitForCloudPlacementReady(ip, csrf2, name, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
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
        except:
            pass
        count = count + 1
        time.sleep(10)
        current_app.logger.info("Waited for " + str(count * 10) + "s retrying")
    if response_csrf is None:
        current_app.logger.info("Waited for " + str(count * 10) + "s default cloud status")
        return None, "Failed", "ERROR"

    return "SUCCESS", "READY", response_csrf.json()["state"]


def createNewCloud(ip, csrf2, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    datacenter = current_app.config['VC_DATACENTER']
    if str(datacenter).__contains__("/"):
        dc = datacenter[datacenter.rindex("/")+1:]
    else:
        dc = datacenter
    body = {
        "name": Cloud.CLOUD_NAME_VSPHERE,
        "vtype": "CLOUD_VCENTER",
        "vcenter_configuration": {
            "privilege": "WRITE_ACCESS",
            "deactivate_vm_discovery": False,
            "vcenter_url": current_app.config['VC_IP'],
            "username": current_app.config['VC_USER'],
            "password": current_app.config['VC_PASSWORD'],
            "datacenter": dc
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


def getNetworkUrl(ip, csrf2, name, aviVersion):
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
        return None, "Failed", "ERROR"
    url = "https://" + ip + "/api/network-inventory/?cloud_ref.uuid=" + uuid
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
        "x-csrftoken": csrf2[0]
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
        "x-csrftoken": csrf2[0]
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


def getNetworkDetails(ip, csrf2, managementNetworkUrl, startIp, endIp, prefixIp, netmask, aviVersion):
    url = managementNetworkUrl
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
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
    except Exception as e:
        current_app.logger.info("Ip pools are not configured configuring it")

    os.system("rm -rf managementNetworkDetails.json")
    with open("./managementNetworkDetails.json", "w") as outfile:
        json.dump(response_csrf.json(), outfile)

    generateVsphereConfiguredSubnets("managementNetworkDetails.json", startIp, endIp, prefixIp,
                                     int(netmask))
    return "SUCCESS", 200, details


def getNetworkDetailsVip(ip, csrf2, vipNetworkUrl, startIp, endIp, prefixIp, netmask, aviVersion):
    url = vipNetworkUrl
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
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
    except Exception as e:
        current_app.logger.info("Ip pools are not configured configuring it")

    os.system("rm -rf vipNetworkDetails.json")
    with open("./vipNetworkDetails.json", "w") as outfile:
        json.dump(response_csrf.json(), outfile)
    generateVsphereConfiguredSubnets("vipNetworkDetails.json", startIp, endIp, prefixIp,
                                     int(netmask))
    return "SUCCESS", 200, details


def updateNetworkWithIpPools(ip, csrf2, managementNetworkUrl, fileName, aviVersion):
    with open(fileName, 'r') as openfile:
        json_object = json.load(openfile)
    json_object_m = json.dumps(json_object, indent=4)
    url = managementNetworkUrl
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    details = {}
    response_csrf = requests.request("PUT", url, headers=headers, data=json_object_m, verify=False)
    if response_csrf.status_code != 200:
        count = 0
        if response_csrf.text.__contains__(
                "Cannot edit network properties till network sync from Service Engines is complete"):
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
    details["vimref"] = response_csrf.json()["vimgrnw_ref"]
    return 200, "SUCCESS", details


def getSeNewBody(newCloudUrl, seGroupName, clusterUrl, dataStore):
    if str(dataStore).__contains__("/"):
        dataStore = dataStore[dataStore.rindex("/")+1:]

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
        "se_name_prefix": "Avi",
        "vs_host_redundancy": True,
        "vcenter_folder": "AviSeFolder",
        "vcenter_datastores_include": True,
        "vcenter_datastore_mode": "VCENTER_DATASTORE_SHARED",
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
        "vcenter_datastores": [{
            "datastore_name": dataStore
        }],
        "service_ip_subnets": [],
        "auto_rebalance_criteria": [],
        "auto_rebalance_capacity_per_se": [],
        "vcenter_clusters": {
            "include": True,
            "cluster_refs": [
                clusterUrl
            ]
        },
        "license_tier": "ENTERPRISE",
        "license_type": "LIC_CORES",
        "se_bandwidth_type": "SE_BANDWIDTH_UNLIMITED",
        "name": seGroupName
    }
    return json.dumps(body, indent=4)


def createSECloud(ip, csrf2, newCloudUrl, seGroupName, clusterUrl, dataStore, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    body = {
        "max_vs_per_se": 10,
        "min_scaleout_per_vs": 1,
        "max_scaleout_per_vs": 4,
        "max_se": 2,
        "vcpus_per_se": 2,
        "memory_per_se": 4096,
        "disk_per_se": 15,
        "max_cpu_usage": 80,
        "min_cpu_usage": 30,
        "se_deprovision_delay": 120,
        "auto_rebalance": False,
        "se_name_prefix": "Avi",
        "vs_host_redundancy": True,
        "vcenter_folder": "AviSeFolder",
        "vcenter_datastores_include": True,
        "vcenter_datastore_mode": "VCENTER_DATASTORE_SHARED",
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
        "se_dp_isolation": False,
        "se_dp_isolation_num_non_dp_cpus": 0,
        "cloud_ref": newCloudUrl,
        "vcenter_datastores": [{
            "datastore_name": dataStore
        }],
        "service_ip_subnets": [],
        "auto_rebalance_criteria": [],
        "auto_rebalance_capacity_per_se": [],
        "vcenter_clusters": {
            "include": True,
            "cluster_refs": [
                clusterUrl
            ]
        },
        "license_tier": "ESSENTIALS",
        "license_type": "LIC_CORES",
        "se_bandwidth_type": "SE_BANDWIDTH_UNLIMITED",
        "name": seGroupName
    }
    json_object = getSeNewBody(newCloudUrl, seGroupName, clusterUrl, dataStore)
    url = "https://" + ip + "/api/serviceenginegroup"
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
        json_object = json.dumps(response_csrf.json(), indent=4)
        with open("./ipam_details.json", "w") as outfile:
            outfile.write(json_object)
        for re in response_csrf.json()["results"]:
            if re['name'] == name:
                return re["url"], "SUCCESS"
    return "NOT_FOUND", "SUCCESS"


def createIpam(ip, csrf2, managementNetworkUrl, managementDataNetwork, vip_network, name, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    body = {
        "name": name,
        "internal_profile": {
            "ttl": 30,
            "usable_networks": [
                {
                    "nw_ref": managementNetworkUrl
                },
                {
                    "nw_ref": managementDataNetwork
                },
                {
                    "nw_ref": vip_network
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


def updateIpam_profile(ip, csrf2, network_name, aviVersion):
    with open("./ipam_details.json", 'r') as file2:
        ipam_json = json.load(file2)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
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
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    for usable in update["internal_profile"]["usable_networks"]:
        if usable["nw_ref"] == str(get_network_pg[0]):
            return "Already configured", "SUCCESS"
        networks.append(usable)
    network_url = get_network_pg[0]
    networks.append({"nw_ref": network_url})
    update["internal_profile"]["usable_networks"] = networks
    with open("./ipam_details_get.json", 'w') as file2:
        json.dump(update, file2)
    with open("./ipam_details_get.json", 'r') as file2:
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
        "x-csrftoken": csrf2[0]
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
        with open("detailsOfNewCloudIpam.json", 'w') as f:
            json.dump(data, f)
        return response_csrf.json(), "SUCCESS"


def updateNewCloud(ip, csrf2, newCloudUrl, aviVersion):
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


def generateConfigYaml(ip, datacenter, datastoreName, cluster_name, wpName, wipIpNetmask, _vcenter_ip,
                       _vcenter_username,
                       _password, env):
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
    str_enc_avi = str(request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviPasswordBase64'])
    base64_bytes = str_enc_avi.encode('ascii')
    enc_bytes = base64.b64decode(base64_bytes)
    password_avi = enc_bytes.decode('ascii').rstrip("\n")
    _base64_bytes = password_avi.encode('ascii')
    _enc_bytes = base64.b64encode(_base64_bytes)
    str_enc_avi = _enc_bytes.decode('ascii')
    management_cluster = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
        'tkgMgmtClusterName']
    datastore_path = "/" + datacenter + "/datastore/" + datastoreName
    vsphere_folder_path = "/" + datacenter + "/vm/" + ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder_VSPHERE
    mgmt_network = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtNetworkName']
    parent_resourcePool = request.get_json(force=True)['envSpec']['vcenterDetails']["resourcePoolName"]
    if parent_resourcePool:
        vsphere_rp = "/" + datacenter + "/host/" + cluster_name + "/Resources/" + parent_resourcePool + "/" + ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE
    else:
        vsphere_rp = "/" + datacenter + "/host/" + cluster_name + "/Resources/" + ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE
    str_enc = str(_password)
    _base64_bytes = str_enc.encode('ascii')
    _enc_bytes = base64.b64encode(_base64_bytes)
    vc_p = _enc_bytes.decode('ascii')
    vcenter_passwd = vc_p
    vcenter_ip = _vcenter_ip
    vcenter_username = _vcenter_username
    avi_cluster_vip_name = str(
        request.get_json(force=True)['tkgComponentSpec']['tkgClusterVipNetwork']['tkgClusterVipNetworkName'])
    with open("vip_ip.txt", "r") as e:
        vip_ip = e.read()
    avi_cluster_vip_network_gateway_cidr = vip_ip
    control_plan = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
        'tkgMgmtDeploymentType']
    size = str(request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtSize'])
    clustercidr = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtClusterCidr']
    servicecidr = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtServiceCidr']
    try:
        osName = str(request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtBaseOs'])
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
            "Provided cluster size: " + size + "is not supported, please provide one of: medium/large/extra-large")
        d = {
            "responseType": "ERROR",
            "msg": "Provided cluster size: " + size + "is not supported, please provide one of: medium/large/extra-large/custom",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    ssh_key = runSsh(vcenter_username)
    file_name = "management_cluster_vsphere.yaml"
    with open(file_name, 'w') as outfile:
        if checkMgmtProxyEnabled(env):
            yaml_str_proxy = """
    TKG_HTTP_PROXY: %s
    TKG_HTTPS_PROXY: %s
    TKG_NO_PROXY: %s
            """
            proxy_str = yaml_str + yaml_str_proxy
            httpProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgMgmt']['httpProxy'])
            httpsProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgMgmt']['httpsProxy'])
            noProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgMgmt']['noProxy'])
            formatted = proxy_str % (
                cert, Cloud.CLOUD_NAME_VSPHERE, ip, wpName, wipIpNetmask, AkoType.KEY, AkoType.VALUE,
                str_enc_avi,
                Cloud.SE_GROUP_NAME_VSPHERE, clustercidr,
                management_cluster, control_plan,
                servicecidr, "true", datacenter, datastore_path, vsphere_folder_path,
                mgmt_network,
                vcenter_passwd, vsphere_rp, vcenter_ip, ssh_key, vcenter_username, size.lower(), size.lower(), osName,
                osVersion,
                avi_cluster_vip_name, avi_cluster_vip_network_gateway_cidr, httpProxy, httpsProxy, noProxy)
        elif checkAirGappedIsEnabled(env):
            yaml_str_airgapped = """
    TKG_CUSTOM_IMAGE_REPOSITORY: %s
            """
            airgapped_str = yaml_str + yaml_str_airgapped
            air_gapped_repo = str(
                request.get_json(force=True)['envSpec']['customRepositorySpec']['tkgCustomImageRepository'])
            air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
            os.putenv("TKG_BOM_IMAGE_TAG", Tkg_version.TAG)
            os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY", air_gapped_repo)
            isSelfsinged = str(request.get_json(force=True)['envSpec']['customRepositorySpec'][
                                   'tkgCustomImageRepositoryPublicCaCert'])
            if isSelfsinged.lower() == "false":
                s = """
    TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY: "False"
    TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE: %s
                """
                os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False")
                airgapped_str = airgapped_str + s
                url = air_gapped_repo[:air_gapped_repo.find("/")]
                getBase64CertWriteToFile(grabHostFromUrl(air_gapped_repo), grabPortFromUrl(air_gapped_repo))
                with open('cert.txt', 'r') as file2:
                    repo_cert = file2.readline()
                repo_certificate = repo_cert
                os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE", repo_certificate)
                formatted = airgapped_str % (
                    cert, Cloud.CLOUD_NAME_VSPHERE, ip, wpName, wipIpNetmask, AkoType.KEY, AkoType.VALUE,
                    str_enc_avi,
                    Cloud.SE_GROUP_NAME_VSPHERE, clustercidr,
                    management_cluster, control_plan,
                    servicecidr, "false", datacenter, datastore_path,
                    vsphere_folder_path,
                    mgmt_network,
                    vcenter_passwd, vsphere_rp, vcenter_ip, ssh_key, vcenter_username, size.lower(), size.lower(),
                    osName, osVersion,
                    avi_cluster_vip_name, avi_cluster_vip_network_gateway_cidr, air_gapped_repo, repo_certificate)
            else:
                s = """
    TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY: "False"
                """
                os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False")
                airgapped_str = airgapped_str + s
                formatted = airgapped_str % (
                    cert, Cloud.CLOUD_NAME_VSPHERE, ip, wpName, wipIpNetmask, AkoType.KEY, AkoType.VALUE,
                    str_enc_avi,
                    Cloud.SE_GROUP_NAME_VSPHERE, clustercidr,
                    management_cluster, control_plan,
                    servicecidr, "false", datacenter, datastore_path,
                    vsphere_folder_path,
                    mgmt_network,
                    vcenter_passwd, vsphere_rp, vcenter_ip, ssh_key, vcenter_username, size.lower(), size.lower(),
                    osName, osVersion,
                    avi_cluster_vip_name, avi_cluster_vip_network_gateway_cidr, air_gapped_repo)
        else:
            disable_proxy()
            formatted = yaml_str % (
                cert, Cloud.CLOUD_NAME_VSPHERE, ip, wpName, wipIpNetmask, AkoType.KEY, AkoType.VALUE,
                str_enc_avi,
                Cloud.SE_GROUP_NAME_VSPHERE, clustercidr,
                management_cluster, control_plan,
                servicecidr, "false", datacenter, datastore_path, vsphere_folder_path,
                mgmt_network,
                vcenter_passwd, vsphere_rp, vcenter_ip, ssh_key, vcenter_username, size.lower(), size.lower(), osName,
                osVersion,
                avi_cluster_vip_name, avi_cluster_vip_network_gateway_cidr)
        data1 = yaml.load(formatted, Loader=yaml.RoundTripLoader)
        yaml.dump(data1, outfile, Dumper=yaml.RoundTripDumper, indent=2)


def templateMgmtDeployYaml(ip, datacenter, avi_version, data_store, cluster_name, wpName, wipIpNetmask, vcenter_ip,
                           vcenter_username,
                           password, env, vsSpec):
    deploy_yaml = FileHelper.read_resource(Paths.TKG_MGMT_SPEC_J2)
    t = Template(deploy_yaml)
    datastore_path = "/" + datacenter + "/datastore/" + data_store
    vsphere_folder_path = "/" + datacenter + "/vm/" + ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder_VSPHERE
    str_enc = str(password)
    _base64_bytes = str_enc.encode('ascii')
    _enc_bytes = base64.b64encode(_base64_bytes)
    vcenter_passwd = _enc_bytes.decode('ascii')
    management_cluster = vsSpec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtClusterName
    parent_resourcePool = vsSpec.envSpec.vcenterDetails.resourcePoolName
    if parent_resourcePool:
        vsphere_rp = "/" + datacenter + "/host/" + cluster_name + "/Resources/" + parent_resourcePool + "/" + ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE
    else:
        vsphere_rp = "/" + datacenter + "/host/" + cluster_name + "/Resources/" + ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE
    datacenter = "/" + datacenter
    ssh_key = runSsh(vcenter_username)
    size = vsSpec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtSize
    control_plane_vcpu = ""
    control_plane_disk_gb = ""
    control_plane_mem_mb = ""
    proxyCert = ""
    try:
        proxyCert_raw = request.get_json(force=True)['envSpec']['proxySpec']['tkgMgmt']['proxyCert']
        base64_bytes = base64.b64encode(proxyCert_raw.encode("utf-8"))
        proxyCert = str(base64_bytes, "utf-8")
        isProxy = "true"
    except:
        isProxy = "false"
        current_app.logger.info("Proxy certificate for  Management is not provided")
    ciep = str(request.get_json(force=True)['envSpec']["ceipParticipation"])
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
        control_plane_vcpu = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
            'tkgMgmtCpuSize']
        control_plane_disk_gb = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
            'tkgMgmtStorageSize']
        control_plane_mem_gb = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
            'tkgMgmtMemorySize']
        control_plane_mem_mb = str(int(control_plane_mem_gb) * 1024)
    else:
        current_app.logger.error(
            "Provided cluster size: " + size + "is not supported, please provide one of: medium/large/extra-large/custom")
        d = {
            "responseType": "ERROR",
            "msg": "Provided cluster size: " + size + "is not supported, please provide one of: medium/large/extra-large/custom",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    try:
        osName = str(request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtBaseOs'])
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
    avi_cluster_vip_network_gateway_cidr = vip_ip
    air_gapped_repo = ""
    repo_certificate = ""
    if checkAirGappedIsEnabled(env):
        air_gapped_repo = vsSpec.envSpec.customRepositorySpec.tkgCustomImageRepository
        air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
        os.putenv("TKG_BOM_IMAGE_TAG", Tkg_version.TAG)
        os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY", air_gapped_repo)
        os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False")
        getBase64CertWriteToFile(grabHostFromUrl(air_gapped_repo), grabPortFromUrl(air_gapped_repo))
        with open('cert.txt', 'r') as file2:
            repo_cert = file2.readline()
        repo_certificate = repo_cert
        os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE", repo_certificate)
    if checkEnableIdentityManagement(env):
        try:
            identity_mgmt_type = str(
                request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["identityManagementType"])
            if identity_mgmt_type.lower() == "oidc":
                oidc_provider_client_id = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["oidcSpec"][
                        "oidcClientId"])
                oidc_provider_client_secret = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["oidcSpec"][
                        "oidcClientSecret"])
                oidc_provider_groups_claim = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["oidcSpec"][
                        "oidcGroupsClaim"])
                oidc_provider_issuer_url = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["oidcSpec"][
                        "oidcIssuerUrl"])
                ## TODO: check if provider name is required -- NOT REQUIRED
                # oidc_provider_name = str(request.get_json(force=True))
                oidc_provider_scopes = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["oidcSpec"][
                        "oidcScopes"])
                oidc_provider_username_claim = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["oidcSpec"][
                        "oidcUsernameClaim"])
                FileHelper.write_to_file(
                    t.render(config=vsSpec, avi_cert=get_base64_cert(ip), ip=ip, wpName=wpName,
                             wipIpNetmask=wipIpNetmask, ceip=ciep, isProxyCert=isProxy,proxyCert=proxyCert,
                             avi_label_key=AkoType.KEY, avi_label_value=AkoType.VALUE, cluster_name=management_cluster,
                             data_center=datacenter, datastore_path=datastore_path,
                             vsphere_folder_path=vsphere_folder_path, vcenter_passwd=vcenter_passwd,
                             vsphere_rp=vsphere_rp,
                             vcenter_ip=vcenter_ip, ssh_key=ssh_key, vcenter_username=vcenter_username,
                             size_controlplane=size.lower(), size_worker=size.lower(),
                             avi_cluster_vip_network_gateway_cidr=avi_cluster_vip_network_gateway_cidr,
                             air_gapped_repo=air_gapped_repo, repo_certificate=repo_certificate, osName=osName,
                             osVersion=osVersion,
                             avi_version=avi_version,
                             size=size, control_plane_vcpu=control_plane_vcpu,
                             control_plane_disk_gb=control_plane_disk_gb,
                             control_plane_mem_mb=control_plane_mem_mb, identity_mgmt_type=identity_mgmt_type,
                             oidc_provider_client_id=oidc_provider_client_id,
                             oidc_provider_client_secret=oidc_provider_client_secret,
                             oidc_provider_groups_claim=oidc_provider_groups_claim,
                             oidc_provider_issuer_url=oidc_provider_issuer_url,
                             oidc_provider_scopes=oidc_provider_scopes,
                             oidc_provider_username_claim=oidc_provider_username_claim),
                    Paths.CLUSTER_PATH + management_cluster + "/management_cluster_vsphere.yaml")
            ## TODO: add ldap code here
            elif identity_mgmt_type.lower() == "ldap":
                ldap_endpoint_ip = str(request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]
                                       ["ldapSpec"]["ldapEndpointIp"])
                ldap_endpoint_port = str(request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]
                                         ["ldapSpec"]["ldapEndpointPort"])
                str_enc = str(request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["ldapSpec"][
                                  "ldapBindPWBase64"])
                base64_bytes = str_enc.encode('ascii')
                enc_bytes = base64.b64decode(base64_bytes)
                ldap_endpoint_bind_pw = enc_bytes.decode('ascii').rstrip("\n")
                ldap_bind_dn = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]["ldapSpec"][
                        "ldapBindDN"])
                ldap_user_search_base_dn = str(
                    request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"]
                    ["ldapSpec"]["ldapUserSearchBaseDN"])
                ldap_user_search_filter = str(request.get_json(force=True)["tkgComponentSpec"]
                                              ["identityManagementSpec"]["ldapSpec"]["ldapUserSearchFilter"])
                ldap_user_search_uname = str(request.get_json(force=True)["tkgComponentSpec"]
                                             ["identityManagementSpec"]["ldapSpec"]["ldapUserSearchUsername"])
                ldap_grp_search_base_dn = str(request.get_json(force=True)["tkgComponentSpec"]
                                              ["identityManagementSpec"]["ldapSpec"]["ldapGroupSearchBaseDN"])
                ldap_grp_search_filter = str(request.get_json(force=True)["tkgComponentSpec"]
                                             ["identityManagementSpec"]["ldapSpec"]["ldapGroupSearchFilter"])
                ldap_grp_search_user_attr = str(request.get_json(force=True)["tkgComponentSpec"]
                                                ["identityManagementSpec"]["ldapSpec"]["ldapGroupSearchUserAttr"])
                ldap_grp_search_grp_attr = str(request.get_json(force=True)["tkgComponentSpec"]
                                               ["identityManagementSpec"]["ldapSpec"]["ldapGroupSearchGroupAttr"])
                ldap_grp_search_name_attr = str(request.get_json(force=True)["tkgComponentSpec"]
                                                ["identityManagementSpec"]["ldapSpec"]["ldapGroupSearchNameAttr"])
                ldap_root_ca_data = str(request.get_json(force=True)["tkgComponentSpec"]
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
                    t.render(config=vsSpec, avi_cert=get_base64_cert(ip), ip=ip, wpName=wpName,
                             wipIpNetmask=wipIpNetmask, ceip=ciep,isProxyCert=isProxy, proxyCert=proxyCert,
                             avi_label_key=AkoType.KEY, avi_label_value=AkoType.VALUE, cluster_name=management_cluster,
                             data_center=datacenter, datastore_path=datastore_path,
                             vsphere_folder_path=vsphere_folder_path, vcenter_passwd=vcenter_passwd,
                             vsphere_rp=vsphere_rp,
                             vcenter_ip=vcenter_ip, ssh_key=ssh_key, vcenter_username=vcenter_username,
                             size_controlplane=size.lower(), size_worker=size.lower(),
                             avi_cluster_vip_network_gateway_cidr=avi_cluster_vip_network_gateway_cidr,
                             air_gapped_repo=air_gapped_repo, repo_certificate=repo_certificate, osName=osName,
                             osVersion=osVersion,
                             avi_version=avi_version,
                             size=size, control_plane_vcpu=control_plane_vcpu,
                             control_plane_disk_gb=control_plane_disk_gb,
                             control_plane_mem_mb=control_plane_mem_mb, identity_mgmt_type=identity_mgmt_type,
                             ldap_endpoint_ip=ldap_endpoint_ip, ldap_endpoint_port=ldap_endpoint_port,
                             ldap_endpoint_bind_pw=ldap_endpoint_bind_pw,
                             ldap_bind_dn=ldap_bind_dn, ldap_user_search_base_dn=ldap_user_search_base_dn,
                             ldap_user_search_filter=ldap_user_search_filter,
                             ldap_user_search_uname=ldap_user_search_uname,
                             ldap_grp_search_base_dn=ldap_grp_search_base_dn,
                             ldap_grp_search_filter=ldap_grp_search_filter,
                             ldap_grp_search_user_attr=ldap_grp_search_user_attr,
                             ldap_grp_search_grp_attr=ldap_grp_search_grp_attr,
                             ldap_grp_search_name_attr=ldap_grp_search_name_attr,
                             ldap_root_ca_data_base64=ldap_root_ca_data_base64),
                    Paths.CLUSTER_PATH + management_cluster + "/management_cluster_vsphere.yaml")
            #     TODO: Read param
            else:
                raise Exception("Wrong Identity Management type provided, accepted values are: oidc or ldap")
        except Exception as e:
            raise Exception("Keyword " + str(e) + "  not found in input file")
    else:
        FileHelper.write_to_file(
            t.render(config=vsSpec, avi_cert=get_base64_cert(ip), ip=ip, wpName=wpName, wipIpNetmask=wipIpNetmask,
                     avi_label_key=AkoType.KEY, avi_label_value=AkoType.VALUE, cluster_name=management_cluster,
                     data_center=datacenter, datastore_path=datastore_path, ceip=ciep,isProxyCert=isProxy, proxyCert=proxyCert,
                     vsphere_folder_path=vsphere_folder_path, vcenter_passwd=vcenter_passwd, vsphere_rp=vsphere_rp,
                     vcenter_ip=vcenter_ip, ssh_key=ssh_key, vcenter_username=vcenter_username,
                     size_controlplane=size.lower(), size_worker=size.lower(),
                     avi_version=avi_version,
                     avi_cluster_vip_network_gateway_cidr=avi_cluster_vip_network_gateway_cidr,
                     air_gapped_repo=air_gapped_repo, repo_certificate=repo_certificate, osName=osName,
                     osVersion=osVersion,
                     size=size, control_plane_vcpu=control_plane_vcpu, control_plane_disk_gb=control_plane_disk_gb,
                     control_plane_mem_mb=control_plane_mem_mb),
            Paths.CLUSTER_PATH + management_cluster + "/management_cluster_vsphere.yaml")


def deployManagementCluster(management_cluster, ip, data_center, data_store, cluster_name, wpName, wipIpNetmask,
                            vcenter_ip,
                            vcenter_username, avi_version, password, env, vsSpec):
    try:
        if not getClusterStatusOnTanzu(management_cluster, "management"):
            os.system("rm -rf kubeconfig.yaml")
            templateMgmtDeployYaml(ip, data_center, avi_version, data_store, cluster_name, wpName, wipIpNetmask,
                                   vcenter_ip,
                                   vcenter_username,
                                   password, env, vsSpec)
            # generateConfigYaml(ip, data_center, data_store, cluster_name, wpName, wipIpNetmask, vcenter_ip,
            #                    vcenter_username,
            #                    password, env)
            current_app.logger.info("Deploying management cluster")
            os.putenv("DEPLOY_TKG_ON_VSPHERE7", "true")
            listOfCmd = ["tanzu", "management-cluster", "create", "-y", "--file",
                         Paths.CLUSTER_PATH + management_cluster + "/management_cluster_vsphere.yaml",
                         "-v",
                         "6"]
            runProcess(listOfCmd)
            listOfCmdKube = ["tanzu", "management-cluster", "kubeconfig", "get", management_cluster, "--admin",
                             "--export-file",
                             "kubeconfig.yaml"]
            runProcess(listOfCmdKube)
            current_app.logger.info("Waiting  for 1 min for status==ready")
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
        startIp = request.get_json(force=True)["tkgComponentSpec"]['tkgClusterVipNetwork'][
            "tkgClusterVipIpStartRange"]
        endIp = request.get_json(force=True)["tkgComponentSpec"]['tkgClusterVipNetwork'][
            "tkgClusterVipIpEndRange"]
        prefixIpNetmask = seperateNetmaskAndIp(
            request.get_json(force=True)["tkgComponentSpec"]['tkgClusterVipNetwork'][
                "tkgClusterVipNetworkGatewayCidr"])
        getVIPNetworkDetails = getNetworkDetailsVip(ip, csrf2, get_vip[0], startIp, endIp, prefixIpNetmask[0],
                                                    prefixIpNetmask[1], aviVersion)
        if getVIPNetworkDetails[0] is None:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get vip network details " + str(getVIPNetworkDetails[2]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        if getVIPNetworkDetails[0] == "AlreadyConfigured":
            current_app.logger.info("Vip Ip pools are already configured.")
            ip_pre = getVIPNetworkDetails[2]["subnet_ip"] + "/" + str(getVIPNetworkDetails[2]["subnet_mask"])
        else:
            update_resp = updateNetworkWithIpPools(ip, csrf2, get_vip[0], "vipNetworkDetails.json",
                                                   aviVersion)
            if update_resp[0] != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to update vip network ip pools " + str(update_resp[1]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            ip_pre = update_resp[2]["subnet_ip"] + "/" + str(update_resp[2]["subnet_mask"])
        with open("vip_ip.txt", "w") as e:
            e.write(ip_pre)
        d = {
            "responseType": "SUCCESS",
            "msg": "Updated ip vip pools successfully",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200
    except Exception as e:
        d = {
            "responseType": "ERROR",
            "msg": "Failed to update vip ip pools " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
