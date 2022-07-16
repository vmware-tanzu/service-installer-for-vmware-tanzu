import logging

from common.lib.nsxt_client import NsxtClient
from common.model.vmcSpec import VmcMasterSpec
from flask import Blueprint

from src.common.lib.govc_client import GovcClient
from src.common.util.local_cmd_helper import LocalCmdHelper

logger = logging.getLogger(__name__)
from flask import jsonify, request
import requests
from tqdm import tqdm
import base64
import time
import json
import os

workload_config = Blueprint("workload_config", __name__, static_folder="workloadConfig")
from flask import current_app
import ruamel
import sys

sys.path.append(".../")
from common.operation.vcenter_operations import checkVmPresent
from common.operation.constants import ResourcePoolAndFolderName, GroupNameCgw, GroupNameMgw, FirewallRuleMgw, \
    ControllerLocation, Paths
from common.common_utilities import preChecks, envCheck, getClusterStatusOnTanzu, \
    getCloudStatus, getSECloudStatus, createResourceFolderAndWait, validateNetworkAvailable, checkTmcEnabled, \
    deployCluster, registerWithTmcOnSharedAndWorkload, registerTanzuObservability, registerTSM, \
    downloadAndPushKubernetesOvaMarketPlace, getKubeVersionFullName, getNetworkPathTMC, checkDataProtectionEnabled, \
    enable_data_protection, createClusterFolder
from common.operation.ShellHelper import runShellCommandAndReturnOutput, grabKubectlCommand, grabIpAddress, \
    verifyPodsAreRunning, grabPipeOutput, runShellCommandAndReturnOutputAsList, \
    runShellCommandAndReturnOutputAsListWithChangedDir, grabPipeOutputChagedDir, runShellCommandWithPolling
from common.common_utilities import convertStringToCommaSeperated, obtain_second_csrf, preChecks, get_avi_version, \
    envCheck, getCloudStatus, checkEnableIdentityManagement, checkPinnipedInstalled, createRbacUsers, \
    createResourceFolderAndWait, validateNetworkAvailable, checkTmcEnabled, \
    deployCluster, registerWithTmcOnSharedAndWorkload, registerTanzuObservability, registerTSM
from common.operation.ShellHelper import grabKubectlCommand, verifyPodsAreRunning, grabPipeOutput, \
    runShellCommandAndReturnOutputAsList, \
    grabPipeOutputChagedDir, runShellCommandWithPolling
from common.operation.constants import SegmentsName, RegexPattern, Versions, AkoType, AppName, FirewallRuleCgw, \
    ServiceName, PLAN, \
    Cloud, Type, Env, Sizing, Tkg_version
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from vmc.managementConfig.management_config import controllerDeployment, getSECloudStatus, createSECloud, \
    getVipNetwork, createVipNetwork, getIpam, changeSeGroupAndSetInterfaces, listAllServiceEngine, \
    getDetailsOfServiceEngine
from common.replace_value import replaceValueSysConfig
from common.session.session_acquire import login

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


@workload_config.route("/api/tanzu/vmc/workload/preconfig", methods=['POST'])
def workloadConfig():
    network_config = networkConfig()
    if network_config[1] != 200:
        current_app.logger.error(network_config[0].json['msg'])
        d = {
            "responseType": "ERROR",
            "msg": "Failed to Config shared cluster " + str(network_config[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    deploy_workload = deploy()
    if deploy_workload[1] != 200:
        current_app.logger.error(str(deploy_workload[0].json['msg']))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to deploy extension " + str(deploy_workload[0].json['msg']),
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


@workload_config.route("/api/tanzu/vmc/workload/network-config", methods=['POST'])
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
    vcenter_ip = current_app.config['VC_IP']
    vcenter_username = current_app.config['VC_USER']
    password = current_app.config['VC_PASSWORD']
    cluster_name = current_app.config['VC_CLUSTER']
    data_center = current_app.config['VC_DATACENTER']
    data_store = current_app.config['VC_DATASTORE']
    refreshToken = request.get_json(force=True)['marketplaceSpec']['refreshToken']
    kubernetes_ova_os = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadBaseOs']
    kubernetes_ova_version = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadKubeVersion']
    if refreshToken:
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
        current_app.logger.info("MarketPlace refresh token is not provided, skipping the download of kubernetes OVA")
    login()
    listOfSegment = NsxtClient(current_app.config).list_segments(gateway_id='cgw')
    if not NsxtClient.find_object(listOfSegment, SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT):
        try:
            NsxtClient(current_app.config).create_segment(gateway_id='cgw',
                                                          segment_id=SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT,
                                                          gateway_cidr=request.get_json(force=True)['componentSpec'][
                                                              'tkgWorkloadDataNetworkSpec'][
                                                              'tkgWorkloadDataGatewayCidr'],
                                                          dhcp_start=request.get_json(force=True)['componentSpec'][
                                                              'tkgWorkloadDataNetworkSpec'][
                                                              'tkgWorkloadDataDhcpStartRange'],
                                                          dhcp_end=request.get_json(force=True)['componentSpec'][
                                                              'tkgWorkloadDataNetworkSpec'][
                                                              'tkgWorkloadDataDhcpEndRange'],
                                                          dns_servers=
                                                          convertStringToCommaSeperated(
                                                              request.get_json(force=True)['envVariablesSpec'][
                                                                  'dnsServersIp']))
        except Exception as e:
            d = {
                "responseType": "ERROR",
                "msg": f"Failed to create segment: {SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT} {e}",
                "ERROR_CODE": 500
            }
            current_app.logger.error(
                f"Failed to create segment: {SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT} {e}")
            return jsonify(d), 500
        current_app.logger.info("Created segment " + SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT)
    else:
        current_app.logger.info("Segment " + SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT + " already created")
    ##########################################################
    govc_client = GovcClient(current_app.config, LocalCmdHelper())
    ip = govc_client.get_vm_ip(ControllerLocation.CONTROLLER_NAME, datacenter_name=data_center)
    if ip is None:
        current_app.logger.error("Failed to get ip of avi controller")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get ip of avi controller",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    ip = ip[0]
    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        current_app.logger.error("Failed to get csrf from new set password")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get csrf from new set password",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
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
        current_app.logger.error("Requested cloud is not created")
        d = {
            "responseType": "ERROR",
            "msg": "Requested cloud is not created",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    else:
        cloud_url = get_cloud[0]
    get_wip = getVipNetwork(ip, csrf2, Cloud.WIP_WORKLOAD_NETWORK_NAME, aviVersion)
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
        current_app.logger.info("Creating New VIP network " + Cloud.WIP_WORKLOAD_NETWORK_NAME)
        vip_net = createVipNetwork(ip, csrf2, cloud_url, Cloud.WIP_WORKLOAD_NETWORK_NAME, Type.WORKLOAD, aviVersion)
        if vip_net[0] is None:
            current_app.logger.error("Failed to create vip network " + str(vip_net[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create  vip network " + str(vip_net[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        wip_url = vip_net[0]
        current_app.logger.info("Created New VIP network " + Cloud.WIP_WORKLOAD_NETWORK_NAME)
    else:
        wip_url = get_wip[0]

    get_se_cloud = getSECloudStatus(ip, csrf2, aviVersion, Cloud.SE_WORKLOAD_GROUP_NAME)
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
        current_app.logger.info("Creating New se cloud " + Cloud.SE_WORKLOAD_GROUP_NAME)
        cloud_se = createSECloud(ip, csrf2, cloud_url, Cloud.SE_WORKLOAD_GROUP_NAME, aviVersion)
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
    get_ipam = getIpam(ip, csrf2, Cloud.IPAM_NAME, aviVersion)
    if get_ipam[0] is None or get_ipam[0] == "NOT_FOUND":
        current_app.logger.error("Failed to get se Ipam " + str(get_ipam[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get ipam " + str(get_ipam[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    else:
        ipam_url = get_ipam[0]
    ipam = getIPamDetails(ip, csrf2, ipam_url, wip_url, aviVersion)
    if ipam[0] is None:
        current_app.logger.error("Failed to get se Ipam Details " + str(ipam[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get se Ipam Details  " + str(ipam[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    vm_state = checkVmPresent(vcenter_ip, vcenter_username, password, ControllerLocation.CONTROLLER_NAME)
    if vm_state is None:
        current_app.logger.error("Avi controller not found ")
        d = {
            "responseType": "ERROR",
            "msg": "Avi controller not found ",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    avi_uuid = vm_state.config.uuid
    current_app.config['se_ova_path'] = "/tmp/" + avi_uuid + ".ova"
    new_cloud_status = updateIpamWithDataNetwork(ip, csrf2, ipam_url, aviVersion)
    if new_cloud_status[0] is None:
        current_app.logger.error("Failed update ipam " + str(new_cloud_status[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed update ipam" + str(new_cloud_status[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if not validateNetworkAvailable(SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT, vcenter_ip, vcenter_username,
                                    password):
        current_app.logger.error("Failed to find the network " + SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT)
        d = {
            "responseType": "ERROR",
            "msg": "Failed to find the network " + SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    dep = controllerDeployment(ip, csrf2, data_center, data_store, cluster_name, vcenter_ip, vcenter_username, password,
                               se_cloud_url, "./vmc/workloadConfig/se.json", "detailsOfServiceEngine3.json",
                               "detailsOfServiceEngine4.json", ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME,
                               ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME2, 3, Type.WORKLOAD, 1, aviVersion)
    if dep[1] != 200:
        current_app.logger.error("Controller deployment failed" + str(dep[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Controller deployment failed " + str(dep[0]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    d = {
        "responseType": "SUCCESS",
        "msg": "Successfully configured workload cluster",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def getIPamDetails(ip, csrf2, url_ipam, dataNetwork, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    body = {}
    url = url_ipam
    response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        json_object = json.dumps(response_csrf.json(), indent=4)
        os.system("rm -rf detailsOfIpam.json")
        with open("./detailsOfIpam.json", "w") as outfile:
            outfile.write(json_object)
        dicti = {"nw_ref": dataNetwork}
        liti = []
        with open("detailsOfIpam.json") as f:
            data = json.load(f)
        for a in data["internal_profile"]["usable_networks"]:
            liti.append(a)
        liti.append(dicti)
        replaceValueSysConfig("detailsOfIpam.json", "internal_profile", "usable_networks", liti)
        return response_csrf.json(), "SUCCESS"


def updateIpamWithDataNetwork(ip, csrf2, ipamUrl, aviVersion):
    with open("./detailsOfIpam.json", 'r') as file2:
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
    response_csrf = requests.request("PUT", ipamUrl, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        return response_csrf.json(), "SUCCESS"


@workload_config.route("/api/tanzu/vmc/workload/config", methods=['POST'])
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
    vmcSpec: VmcMasterSpec = VmcMasterSpec.parse_obj(json_dict)
    env = env[0]
    isTkg13 = False
    if Tkg_version.TKG_VERSION == "1.3":
        isTkg13 = True
    aviVersion = get_avi_version(env)
    vcenter_ip = current_app.config['VC_IP']
    vcenter_username = current_app.config['VC_USER']
    password = current_app.config['VC_PASSWORD']
    cluster_name = current_app.config['VC_CLUSTER']
    data_center = current_app.config['VC_DATACENTER']
    data_store = current_app.config['VC_DATASTORE']
    vsphere_password = password
    _base64_bytes = vsphere_password.encode('ascii')
    _enc_bytes = base64.b64encode(_base64_bytes)
    vsphere_password = _enc_bytes.decode('ascii')
    headers = {
        "Content-Type": "application/json",
        "csp-auth-token": current_app.config['access_token']
    }
    listOfSegment = NsxtClient(current_app.config).list_segments(gateway_id='cgw')
    if not NsxtClient.find_object(listOfSegment, SegmentsName.DISPLAY_NAME_TKG_WORKLOAD):
        try:
            NsxtClient(current_app.config).create_segment(gateway_id='cgw',
                                                          segment_id=SegmentsName.DISPLAY_NAME_TKG_WORKLOAD,
                                                          gateway_cidr=request.get_json(force=True)['componentSpec'][
                                                              'tkgWorkloadSpec'][
                                                              'tkgWorkloadGatewayCidr'],
                                                          dhcp_start=request.get_json(force=True)['componentSpec'][
                                                              'tkgWorkloadSpec'][
                                                              'tkgWorkloadDhcpStartRange'],
                                                          dhcp_end=request.get_json(force=True)['componentSpec'][
                                                              'tkgWorkloadSpec'][
                                                              'tkgWorkloadDhcpEndRange'],
                                                          dns_servers=
                                                          convertStringToCommaSeperated(
                                                              request.get_json(force=True)['envVariablesSpec'][
                                                                  'dnsServersIp']))
        except Exception as e:
            d = {
                "responseType": "ERROR",
                "msg": f"Failed to create segment: {SegmentsName.DISPLAY_NAME_TKG_WORKLOAD} {e}",
                "ERROR_CODE": 500
            }
            current_app.logger.error(f"Failed to create segment: {SegmentsName.DISPLAY_NAME_TKG_WORKLOAD} {e}")
            return jsonify(d), 500
        current_app.logger.info(f"Created segment {SegmentsName.DISPLAY_NAME_TKG_WORKLOAD}")
    else:
        current_app.logger.info(f"Segment {SegmentsName.DISPLAY_NAME_TKG_WORKLOAD} already created")

    listOfGroups = NsxtClient(current_app.config).list_groups(gateway_id='cgw')
    listOfSegment = NsxtClient(current_app.config).list_segments(gateway_id='cgw')
    if len(listOfSegment) == 0:
        d = {
            "responseType": "ERROR",
            "msg": "No segments are created",
            "ERROR_CODE": 404
        }
        current_app.logger.error("No segments are created")
        return jsonify(d), 404
    ##############################
    if not NsxtClient.find_object(listOfGroups, GroupNameCgw.DISPLAY_NAME_TKG_Workload_Networks_Group_CGW):
        if not NsxtClient.get_segment_path(listOfSegment, SegmentsName.DISPLAY_NAME_TKG_WORKLOAD):
            d = {
                "responseType": "ERROR",
                "msg": SegmentsName.DISPLAY_NAME_TKG_WORKLOAD + " is not created",
                "ERROR_CODE": 404
            }
            current_app.logger.error(SegmentsName.DISPLAY_NAME_TKG_WORKLOAD + " is not created")
            return jsonify(d), 404
        isAllGroupsCreated = False
        avi_management_network_group_CGW_path = \
            NsxtClient.get_segment_path(listOfSegment, SegmentsName.DISPLAY_NAME_TKG_WORKLOAD)
        avi_management_group_cgw_body = {"display_name": GroupNameCgw.DISPLAY_NAME_TKG_Workload_Networks_Group_CGW,
                                         "expression": [{"resource_type": "PathExpression",
                                                         "paths": [avi_management_network_group_CGW_path]
                                                         }
                                                        ]
                                         }
        avi_management_group_cgw_body_modified = json.dumps(avi_management_group_cgw_body, indent=4)
        avi_management_network_group_CGW_url = current_app.config['NSX_REVERSE_PROXY_URL'] \
                                               + "orgs/" + current_app.config[
                                                   'ORG_ID'] + "/sddcs/" + current_app.config[
                                                   'SDDC_ID'] + "/policy/api/v1/infra/domains/cgw/groups/" \
                                               + GroupNameCgw.DISPLAY_NAME_TKG_Workload_Networks_Group_CGW
        avi_management_network_group_CGW_create = requests.request("PUT", avi_management_network_group_CGW_url,
                                                                   headers=headers,
                                                                   data=avi_management_group_cgw_body_modified,
                                                                   verify=False)
        if avi_management_network_group_CGW_create.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": avi_management_network_group_CGW_create.text,
                "ERROR_CODE": avi_management_network_group_CGW_create.status_code
            }
            current_app.logger.error(avi_management_network_group_CGW_create.text)
            return jsonify(
                d), avi_management_network_group_CGW_create.status_code

        current_app.logger.info("Created group " + GroupNameCgw.DISPLAY_NAME_TKG_Workload_Networks_Group_CGW)

    ####################################################
    tkg_management = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtNetworkName']
    if not NsxtClient.find_object(listOfGroups, GroupNameMgw.DISPLAY_NAME_TKG_Workload_Networks_Group_Mgw):
        if not NsxtClient.get_segment_path(listOfSegment, tkg_management):
            d = {
                "responseType": "ERROR",
                "msg": tkg_management + " is not created",
                "ERROR_CODE": 404
            }
            current_app.logger.error(tkg_management + " is not created")
            return jsonify(d), 404
        isAllGroupsMGWCreated = False
        avi_management_network_group_CGW_path = \
            NsxtClient.get_segment_path(listOfSegment, SegmentsName.DISPLAY_NAME_TKG_WORKLOAD)
        tkg_management_network_group_mgw_body = {
            "display_name": GroupNameMgw.DISPLAY_NAME_TKG_Workload_Networks_Group_Mgw,
            "expression": [
                {
                    "resource_type": "PathExpression",
                    "paths": [
                        avi_management_network_group_CGW_path
                    ]
                }
            ]
        }
        tkg_management_network_mgw_body_modified = json.dumps(tkg_management_network_group_mgw_body, indent=4)
        tkg_management_network_mgw_url = current_app.config['NSX_REVERSE_PROXY_URL'] \
                                         + "orgs/" + current_app.config[
                                             'ORG_ID'] + "/sddcs/" + current_app.config[
                                             'SDDC_ID'] + "/policy/api/v1/infra/domains/mgw/groups/" \
                                         + GroupNameMgw.DISPLAY_NAME_TKG_Workload_Networks_Group_Mgw
        tkg_management_network_mgw_create = requests.request("PUT", tkg_management_network_mgw_url,
                                                             headers=headers,
                                                             data=tkg_management_network_mgw_body_modified,
                                                             verify=False)
        if tkg_management_network_mgw_create.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": tkg_management_network_mgw_create.text,
                "ERROR_CODE": tkg_management_network_mgw_create.status_code
            }
            current_app.logger.error(tkg_management_network_mgw_create.text)
            return jsonify(d), tkg_management_network_mgw_create.status_code

        current_app.logger.info("Created group " + GroupNameMgw.DISPLAY_NAME_TKG_Workload_Networks_Group_Mgw)
    ####################################################################
    listOfSegment = NsxtClient(current_app.config).list_segments(gateway_id='cgw')
    if len(listOfSegment) == 0:
        d = {
            "responseType": "ERROR",
            "msg": "No segments are created",
            "ERROR_CODE": 404
        }
        current_app.logger.error("No segments are created")
        return jsonify(d), 404
    listOfGroups = NsxtClient(current_app.config).list_groups(gateway_id='cgw')
    if len(listOfGroups) == 0:
        d = {
            "responseType": "ERROR",
            "msg": "No groups are created",
            "ERROR_CODE": 404
        }
        current_app.logger.error("No groups are created")
        return jsonify(d), 404
    listOfFirewall = NsxtClient(current_app.config).list_gateway_firewall_rules(gw_id='cgw')
    isAllFirewallAlreadyCreated = True
    if not NsxtClient.find_object(listOfFirewall, FirewallRuleCgw.DISPLAY_NAME_WORKLOAD_TKG_and_AVI_DNS):
        isAllFirewallAlreadyCreated = False
        groupsName = ""
        allGroupCrated = True
        allSegmentCrated = True
        segmentsName = ""
        if not NsxtClient.get_segment_path(listOfSegment, SegmentsName.DISPLAY_NAME_TKG_WORKLOAD):
            segmentsName += SegmentsName.DISPLAY_NAME_AVI_MANAGEMENT + ","
            allSegmentCrated = False
        if not NsxtClient.get_segment_path(listOfSegment, tkg_management):
            segmentsName += tkg_management + ","
            allSegmentCrated = False
        if not allSegmentCrated:
            d = {
                "responseType": "ERROR",
                "msg": segmentsName + " segment/s is/are not created",
                "ERROR_CODE": 404
            }
            current_app.logger.error(segmentsName + " segment/s  is/are not created")
            return jsonify(d), 404
        if not \
                NsxtClient.find_object(listOfGroups,
                                       GroupNameCgw.DISPLAY_NAME_TKG_Workload_Networks_Group_CGW):
            groupsName += GroupNameCgw.DISPLAY_NAME_TKG_Workload_Networks_Group_CGW + ","
            allGroupCrated = False
        if not \
                NsxtClient.find_object(listOfGroups,
                                       GroupNameCgw.DISPLAY_NAME_TKG_Management_Network_Group_CGW):
            groupsName += GroupNameCgw.DISPLAY_NAME_TKG_Management_Network_Group_CGW + ","
            allGroupCrated = False
        if not NsxtClient.find_object(listOfGroups, GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW):
            groupsName += GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW + ","
            allGroupCrated = False
        if not NsxtClient.find_object(listOfGroups, GroupNameCgw.DISPLAY_NAME_DNS_IPs_Group):
            groupsName += GroupNameCgw.DISPLAY_NAME_DNS_IPs_Group + ","
            allGroupCrated = False
        if not NsxtClient.find_object(listOfGroups, GroupNameCgw.DISPLAY_NAME_NTP_IPs_Group):
            groupsName += GroupNameCgw.DISPLAY_NAME_NTP_IPs_Group + ","
            allGroupCrated = False
        if Tkg_version.TKG_VERSION == "1.3":
            if not \
                    NsxtClient.find_object(listOfGroups,
                                           GroupNameCgw.DISPLAY_NAME_TKG_Management_ControlPlane_IPs):
                groupsName += GroupNameCgw.DISPLAY_NAME_TKG_Management_ControlPlane_IPs + ","
                allGroupCrated = False
        if not \
                NsxtClient.find_object(listOfGroups,
                                       GroupNameCgw.DISPLAY_NAME_TKG_Workload_Networks_Group_CGW):
            groupsName += GroupNameCgw.DISPLAY_NAME_TKG_Workload_Networks_Group_CGW + ","
            allGroupCrated = False
        if not allGroupCrated:
            d = {
                "responseType": "ERROR",
                "msg": groupsName + " group/s is/are not created",
                "ERROR_CODE": 404
            }
            current_app.logger.error(groupsName + " group/s is/are not created")
            return jsonify(d), 404
        if Tkg_version.TKG_VERSION == "1.3":
            tkg_and_avi_to_dns_firewall_rule_cgw_body = {"action": "ALLOW",
                                                         "display_name": FirewallRuleCgw.DISPLAY_NAME_WORKLOAD_TKG_and_AVI_DNS,
                                                         "logged": False,
                                                         "source_groups": [
                                                             NsxtClient.get_object_path(
                                                                 NsxtClient.find_object(listOfGroups,
                                                                                        GroupNameCgw.DISPLAY_NAME_TKG_Workload_Networks_Group_CGW)),
                                                             NsxtClient.get_object_path(
                                                                 NsxtClient.find_object(listOfGroups,
                                                                                        GroupNameCgw.DISPLAY_NAME_TKG_Management_Network_Group_CGW))
                                                         ],
                                                         "destination_groups": [
                                                             NsxtClient.get_object_path(
                                                                 NsxtClient.find_object(listOfGroups,
                                                                                        GroupNameCgw.DISPLAY_NAME_DNS_IPs_Group)),
                                                             NsxtClient.get_object_path(
                                                                 NsxtClient.find_object(listOfGroups,
                                                                                        GroupNameCgw.DISPLAY_NAME_NTP_IPs_Group)),
                                                             NsxtClient.get_object_path(
                                                                 NsxtClient.find_object(listOfGroups,
                                                                                        GroupNameCgw.DISPLAY_NAME_TKG_Management_ControlPlane_IPs)),
                                                             NsxtClient.get_object_path(
                                                                 NsxtClient.find_object(listOfGroups,
                                                                                        GroupNameCgw.DISPLAY_NAME_TKG_Workload_Networks_Group_CGW))
                                                         ],
                                                         "services": ["/infra/services/DNS",
                                                                      "/infra/services/DNS-UDP",
                                                                      "/infra/services/NTP",
                                                                      "/infra/services/" + ServiceName.KUBE_VIP_SERVICE],
                                                         "scope": ["/infra/labels/cgw-all"]
                                                         }
        elif Tkg_version.TKG_VERSION == "1.5":
            tkg_and_avi_to_dns_firewall_rule_cgw_body = {"action": "ALLOW",
                                                         "display_name": FirewallRuleCgw.DISPLAY_NAME_WORKLOAD_TKG_and_AVI_DNS,
                                                         "logged": False,
                                                         "source_groups": [
                                                             NsxtClient.get_object_path(
                                                                 NsxtClient.find_object(listOfGroups,
                                                                                        GroupNameCgw.DISPLAY_NAME_TKG_Workload_Networks_Group_CGW)),
                                                             NsxtClient.get_object_path(
                                                                 NsxtClient.find_object(listOfGroups,
                                                                                        GroupNameCgw.DISPLAY_NAME_TKG_Management_Network_Group_CGW))
                                                         ],
                                                         "destination_groups": [
                                                             NsxtClient.get_object_path(
                                                                 NsxtClient.find_object(listOfGroups,
                                                                                        GroupNameCgw.DISPLAY_NAME_DNS_IPs_Group)),
                                                             NsxtClient.get_object_path(
                                                                 NsxtClient.find_object(listOfGroups,
                                                                                        GroupNameCgw.DISPLAY_NAME_NTP_IPs_Group)),
                                                             NsxtClient.get_object_path(
                                                                 NsxtClient.find_object(listOfGroups,
                                                                                        GroupNameCgw.DISPLAY_NAME_TKG_Workload_Networks_Group_CGW)),
                                                             NsxtClient.get_object_path(
                                                                 NsxtClient.find_object(listOfGroups,
                                                                                        GroupNameCgw.DISPLAY_NAME_CLUSTER_VIP_NETWORK_Group_CGW))
                                                         ],
                                                         "services": ["/infra/services/DNS",
                                                                      "/infra/services/DNS-UDP",
                                                                      "/infra/services/NTP",
                                                                      "/infra/services/" + ServiceName.KUBE_VIP_SERVICE],
                                                         "scope": ["/infra/labels/cgw-all"]
                                                         }
            tkg_and_avi_to_dns_firewall_rule_cgw_modified = json.dumps(tkg_and_avi_to_dns_firewall_rule_cgw_body,
                                                                       indent=4)
            tkg_and_avi_to_dns_firewall_rule_cgw_modified_url = current_app.config['NSX_REVERSE_PROXY_URL'] \
                                                                + "orgs/" + current_app.config[
                                                                    'ORG_ID'] + "/sddcs/" + current_app.config[
                                                                    'SDDC_ID'] + "/policy/api/v1/infra/domains/cgw/gateway-policies/default/rules/" \
                                                                + FirewallRuleCgw.DISPLAY_NAME_WORKLOAD_TKG_and_AVI_DNS
            tkg_and_avi_to_dns_create = requests.request("PUT", tkg_and_avi_to_dns_firewall_rule_cgw_modified_url,
                                                         headers=headers,
                                                         data=tkg_and_avi_to_dns_firewall_rule_cgw_modified,
                                                         verify=False)
            if tkg_and_avi_to_dns_create.status_code != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": tkg_and_avi_to_dns_create.text,
                    "ERROR_CODE": tkg_and_avi_to_dns_create.status_code
                }
                current_app.logger.error(tkg_and_avi_to_dns_create.text)
                return jsonify(d), tkg_and_avi_to_dns_create.status_code

        current_app.logger.info("Created firewall rule " + FirewallRuleCgw.DISPLAY_NAME_WORKLOAD_TKG_and_AVI_DNS)
    if Tkg_version.TKG_VERSION == "1.5":
        if not NsxtClient.find_object(listOfFirewall, FirewallRuleCgw.DISPLAY_NAME_TKG_WORKLOAD_to_vCenter):
            isAllFirewallAlreadyCreated = False
            groupsName = ""
            allGroupCrated = True
            allSegmentCrated = True
            segmentsName = ""
            if not NsxtClient.get_segment_path(listOfSegment, SegmentsName.DISPLAY_NAME_AVI_MANAGEMENT):
                segmentsName += SegmentsName.DISPLAY_NAME_AVI_MANAGEMENT + ","
                allSegmentCrated = False
            if not NsxtClient.get_segment_path(listOfSegment, tkg_management):
                segmentsName += tkg_management + ","
                allSegmentCrated = False
            if not \
                    NsxtClient.get_segment_path(listOfSegment,
                                                SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment):
                segmentsName += tkg_management + ","
                allSegmentCrated = False
            if not allSegmentCrated:
                d = {
                    "responseType": "ERROR",
                    "msg": segmentsName + " segment/s is/are not created",
                    "ERROR_CODE": 404
                }
                current_app.logger.error(segmentsName + " segment/s  is/are not created")
                return jsonify(d), 404
            if not \
                    NsxtClient.find_object(listOfGroups,
                                           GroupNameCgw.DISPLAY_NAME_TKG_Workload_Networks_Group_CGW):
                groupsName += GroupNameCgw.DISPLAY_NAME_TKG_Workload_Networks_Group_CGW + ","
                allGroupCrated = False
            if not NsxtClient.find_object(listOfGroups, GroupNameCgw.DISPLAY_NAME_vCenter_IP_Group):
                groupsName += GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW + ","
                allGroupCrated = False
            if not allGroupCrated:
                d = {
                    "responseType": "ERROR",
                    "msg": groupsName + " group/s is/are not created",
                    "ERROR_CODE": 404
                }
                current_app.logger.error(groupsName + " group/s is/are not created")
                return jsonify(d), 404
            tkg_and_avi_to_dns_firewall_rule_cgw_body = {"action": "ALLOW",
                                                         "display_name": FirewallRuleCgw.DISPLAY_NAME_TKG_WORKLOAD_to_vCenter,
                                                         "logged": False,
                                                         "source_groups": [
                                                             NsxtClient.get_object_path(
                                                                 NsxtClient.find_object(listOfGroups,
                                                                                        GroupNameCgw.DISPLAY_NAME_TKG_Workload_Networks_Group_CGW))],
                                                         "destination_groups": [
                                                             NsxtClient.get_object_path(
                                                                 NsxtClient.find_object(listOfGroups,
                                                                                        GroupNameCgw.DISPLAY_NAME_vCenter_IP_Group))],
                                                         "services": ["/infra/services/HTTPS"],
                                                         "scope": ["/infra/labels/cgw-all"]
                                                         }
            tkg_and_avi_to_dns_firewall_rule_cgw_modified = json.dumps(tkg_and_avi_to_dns_firewall_rule_cgw_body,
                                                                       indent=4)
            tkg_and_avi_to_dns_firewall_rule_cgw_modified_url = current_app.config['NSX_REVERSE_PROXY_URL'] \
                                                                + "orgs/" + current_app.config[
                                                                    'ORG_ID'] + "/sddcs/" + current_app.config[
                                                                    'SDDC_ID'] + "/policy/api/v1/infra/domains/cgw/gateway-policies/default/rules/" \
                                                                + FirewallRuleCgw.DISPLAY_NAME_TKG_WORKLOAD_to_vCenter
            tkg_and_avi_to_dns_create = requests.request("PUT", tkg_and_avi_to_dns_firewall_rule_cgw_modified_url,
                                                         headers=headers,
                                                         data=tkg_and_avi_to_dns_firewall_rule_cgw_modified,
                                                         verify=False)
            if tkg_and_avi_to_dns_create.status_code != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": tkg_and_avi_to_dns_create.text,
                    "ERROR_CODE": tkg_and_avi_to_dns_create.status_code
                }
                current_app.logger.error(tkg_and_avi_to_dns_create.text)
                return jsonify(d), tkg_and_avi_to_dns_create.status_code

            current_app.logger.info("Created firewall rule " + FirewallRuleCgw.DISPLAY_NAME_TKG_WORKLOAD_to_vCenter)
    ####################################################################
    if not NsxtClient.find_object(listOfFirewall,
                                  FirewallRuleCgw.DISPLAY_NAME_WORKLOAD_TKG_and_AVI_to_Internet):
        isAllFirewallAlreadyCreated = False
        groupsName = ""
        allGroupCrated = True
        allSegmentCrated = True
        segmentsName = ""
        if not NsxtClient.get_segment_path(listOfSegment, SegmentsName.DISPLAY_NAME_TKG_WORKLOAD):
            segmentsName += SegmentsName.DISPLAY_NAME_TKG_WORKLOAD + ","
            allSegmentCrated = False
        if not allSegmentCrated:
            d = {
                "responseType": "ERROR",
                "msg": segmentsName + " segment/s is/are not created",
                "ERROR_CODE": 404
            }
            current_app.logger.error(segmentsName + " segment/s  is/are not created")
            return jsonify(d), 404
        if not \
                NsxtClient.find_object(listOfGroups,
                                       GroupNameCgw.DISPLAY_NAME_TKG_Workload_Networks_Group_CGW):
            groupsName += GroupNameCgw.DISPLAY_NAME_TKG_Workload_Networks_Group_CGW + ","
            allGroupCrated = False
        if not allGroupCrated:
            d = {
                "responseType": "ERROR",
                "msg": groupsName + " group/s is/are not created",
                "ERROR_CODE": 404
            }
            current_app.logger.error(groupsName + " group/s is/are not created")
            return jsonify(d), 404
        tkg_and_avi_to_dns_firewall_rule_cgw_body = {"action": "ALLOW",
                                                     "display_name": FirewallRuleCgw.DISPLAY_NAME_WORKLOAD_TKG_and_AVI_to_Internet,
                                                     "logged": False,
                                                     "source_groups": [
                                                         NsxtClient.get_object_path(NsxtClient.find_object(listOfGroups,
                                                                                                           GroupNameCgw.DISPLAY_NAME_TKG_Workload_Networks_Group_CGW))
                                                     ],
                                                     "destination_groups": ["ANY"],
                                                     "services": ["ANY"],
                                                     "scope": ["/infra/labels/cgw-all"]
                                                     }
        tkg_and_avi_to_dns_firewall_rule_cgw_modified = json.dumps(tkg_and_avi_to_dns_firewall_rule_cgw_body, indent=4)
        tkg_and_avi_to_dns_firewall_rule_cgw_modified_url = current_app.config['NSX_REVERSE_PROXY_URL'] \
                                                            + "orgs/" + current_app.config[
                                                                'ORG_ID'] + "/sddcs/" + current_app.config[
                                                                'SDDC_ID'] + "/policy/api/v1/infra/domains/cgw/gateway-policies/default/rules/" \
                                                            + FirewallRuleCgw.DISPLAY_NAME_WORKLOAD_TKG_and_AVI_to_Internet
        tkg_and_avi_to_dns_create = requests.request("PUT", tkg_and_avi_to_dns_firewall_rule_cgw_modified_url,
                                                     headers=headers,
                                                     data=tkg_and_avi_to_dns_firewall_rule_cgw_modified,
                                                     verify=False)
        if tkg_and_avi_to_dns_create.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": tkg_and_avi_to_dns_create.text,
                "ERROR_CODE": tkg_and_avi_to_dns_create.status_code
            }
            current_app.logger.error(tkg_and_avi_to_dns_create.text)
            return jsonify(d), tkg_and_avi_to_dns_create.status_code

        current_app.logger.info(
            "Created firewall rule " + FirewallRuleCgw.DISPLAY_NAME_WORKLOAD_TKG_and_AVI_to_Internet)
    ###################################################################################
    listOfGroups = NsxtClient(current_app.config).list_groups(gateway_id='mgw')
    if len(listOfGroups) == 0:
        d = {
            "responseType": "ERROR",
            "msg": "No groups are created on mgw",
            "ERROR_CODE": 404
        }
        current_app.logger.error("No groups are created")
        return jsonify(d), 404
    listOfFirewall = NsxtClient(current_app.config).list_gateway_firewall_rules(gw_id='mgw')
    isAllFirewallAlreadyCreated = True
    if not NsxtClient.find_object(listOfFirewall, FirewallRuleMgw.DISPLAY_NAME_WORKLOAD_TKG_and_AVItovCenter):
        isAllFirewallAlreadyCreated = False
        groupsName = ""
        allGroupCrated = True
        allSegmentCrated = True
        segmentsName = ""
        if not NsxtClient.get_segment_path(listOfSegment, tkg_management):
            segmentsName += tkg_management + ","
            allSegmentCrated = False
        if not allSegmentCrated:
            d = {
                "responseType": "ERROR",
                "msg": segmentsName + " segment/s is/are not created",
                "ERROR_CODE": 404
            }
            current_app.logger.error(segmentsName + " segment/s  is/are not created")
            return jsonify(d), 404
        if not \
                NsxtClient.find_object(listOfGroups,
                                       GroupNameMgw.DISPLAY_NAME_TKG_Workload_Networks_Group_Mgw):
            groupsName += GroupNameMgw.DISPLAY_NAME_AVI_Management_Network_Group_Mgw + ","
            allGroupCrated = False
        if not allGroupCrated:
            d = {
                "responseType": "ERROR",
                "msg": groupsName + " group/s is/are not created",
                "ERROR_CODE": 404
            }
            current_app.logger.error(groupsName + " group/s is/are not created")
            return jsonify(d), 404
        tkg_and_avi_to_dns_firewall_rule_cgw_body = {"action": "ALLOW",
                                                     "display_name": FirewallRuleMgw.DISPLAY_NAME_WORKLOAD_TKG_and_AVItovCenter,
                                                     "logged": False,
                                                     "source_groups": [
                                                         NsxtClient.get_object_path(NsxtClient.find_object(listOfGroups,
                                                                                                           GroupNameMgw.DISPLAY_NAME_TKG_Workload_Networks_Group_Mgw))],
                                                     "destination_groups": ["/infra/domains/mgw/groups/VCENTER"],
                                                     "services": ["/infra/services/HTTPS"],
                                                     "scope": ["/infra/labels/mgw"]
                                                     }
        tkg_and_avi_to_dns_firewall_rule_cgw_modified = json.dumps(tkg_and_avi_to_dns_firewall_rule_cgw_body, indent=4)
        tkg_and_avi_to_dns_firewall_rule_cgw_modified_url = current_app.config['NSX_REVERSE_PROXY_URL'] \
                                                            + "orgs/" + current_app.config[
                                                                'ORG_ID'] + "/sddcs/" + current_app.config[
                                                                'SDDC_ID'] + "/policy/api/v1/infra/domains/mgw/gateway-policies/default/rules/" \
                                                            + FirewallRuleMgw.DISPLAY_NAME_WORKLOAD_TKG_and_AVItovCenter
        tkg_and_avi_to_dns_create = requests.request("PUT", tkg_and_avi_to_dns_firewall_rule_cgw_modified_url,
                                                     headers=headers,
                                                     data=tkg_and_avi_to_dns_firewall_rule_cgw_modified,
                                                     verify=False)
        if tkg_and_avi_to_dns_create.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": tkg_and_avi_to_dns_create.text,
                "ERROR_CODE": tkg_and_avi_to_dns_create.status_code
            }
            current_app.logger.error(tkg_and_avi_to_dns_create.text)
            return jsonify(d), tkg_and_avi_to_dns_create.status_code

        current_app.logger.info("Created firewall rule " + FirewallRuleMgw.DISPLAY_NAME_WORKLOAD_TKG_and_AVItovCenter)
    govc_client = GovcClient(current_app.config, LocalCmdHelper())
    ip = govc_client.get_vm_ip(ControllerLocation.CONTROLLER_NAME, datacenter_name=data_center)
    if ip is None:
        current_app.logger.error("Failed to get ip of avi controller")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get ip of avi controller",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    ip = ip[0]
    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        current_app.logger.error("Failed to get csrf from new set password")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get csrf from new set password",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    count = 0
    found = False
    seIp3 = None
    while count < 120:
        try:
            current_app.logger.info("Waited " + str(10 * count) + "s to get controller 3 ip, retrying")
            seIp3 = govc_client.get_vm_ip(ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME, datacenter_name=data_center)
            if seIp3 is not None:
                found = True
                seIp3 = seIp3[0]
                break
        except:
            pass
        time.sleep(10)
        count = count + 1

    if not found:
        current_app.logger.error("Controller 3 is not up failed to get ip ")
        d = {
            "responseType": "ERROR",
            "msg": "Controller 3 is not up ",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    count = 0
    found = False
    seIp4 = None
    while count < 120:
        try:
            current_app.logger.info("Waited " + str(10 * count) + "s to get controller 4 ip, retrying")
            seIp4 = govc_client.get_vm_ip(ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME2, datacenter_name=data_center)
            if seIp4 is not None:
                found = True
                seIp4 = seIp4[0]
                break
        except:
            pass
        time.sleep(10)
        count = count + 1

    if not found:
        current_app.logger.error("Controller 4 is not up failed to get ip ")
        d = {
            "responseType": "ERROR",
            "msg": "Controller 4 is not up ",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    urlFromServiceEngine1 = listAllServiceEngine(ip, csrf2, 3, seIp3, aviVersion)
    if urlFromServiceEngine1[0] is None:
        current_app.logger.error("Failed to  get service engine3 details" + str(urlFromServiceEngine1[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to  get service engine details " + str(urlFromServiceEngine1[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    urlFromServiceEngine2 = listAllServiceEngine(ip, csrf2, 3, seIp4, aviVersion)
    if urlFromServiceEngine2[0] is None:
        current_app.logger.error("Failed to  get service engine 4 details" + str(urlFromServiceEngine2[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to  get service engine details " + str(urlFromServiceEngine2[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    details1 = getDetailsOfServiceEngine(ip, csrf2, urlFromServiceEngine1[0], "detailsOfServiceEngine3.json",
                                         aviVersion)
    if details1[0] is None:
        current_app.logger.error("Failed to  get details of engine 3" + str(details1[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to  get details of engine 3" + str(details1[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    details2 = getDetailsOfServiceEngine(ip, csrf2, urlFromServiceEngine2[0], "detailsOfServiceEngine4.json",
                                         aviVersion)
    if details2[0] is None:
        current_app.logger.error("Failed to  get details of engine 4 " + str(details2[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to  get details of engine 4 " + str(details2[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    get_se_cloud = getSECloudStatus(ip, csrf2, aviVersion, Cloud.SE_WORKLOAD_GROUP_NAME)
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
        current_app.logger.error("Failed to get se cloud " + str(get_se_cloud[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create  get se cloud " + str(get_se_cloud[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    else:
        se_cloud_url = get_se_cloud[0]
    if not validateNetworkAvailable(SegmentsName.DISPLAY_NAME_TKG_WORKLOAD, vcenter_ip, vcenter_username, password):
        current_app.logger.error("Failed to find the network " + SegmentsName.DISPLAY_NAME_TKG_WORKLOAD)
        d = {
            "responseType": "ERROR",
            "msg": "Failed to find the network " + SegmentsName.DISPLAY_NAME_TKG_WORKLOAD,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    change = changeNetworks(vcenter_ip, vcenter_username, password, ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME)
    if change[1] != 200:
        current_app.logger.error("Failed changeNetwork " + str(change[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed changeNetwork " + str(change[0]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    se_engines = changeSeGroupAndSetInterfaces(ip, csrf2, urlFromServiceEngine1[0], se_cloud_url,
                                               "detailsOfServiceEngine3.json",
                                               vcenter_ip, vcenter_username,
                                               password, ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME,
                                               Type.WORKLOAD, 2, aviVersion)
    if se_engines[0] is None:
        current_app.logger.error("Failed to  change set interfaces engine 3" + str(se_engines[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to  change set interfaces engine 3" + str(se_engines[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    change = changeNetworks(vcenter_ip, vcenter_username, password, ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME2)
    if change[1] != 200:
        current_app.logger.error("Failed changeNetwork se controller 4 " + str(change[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed changeNetwork se controller 4 " + str(change[0]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    se_engines = changeSeGroupAndSetInterfaces(ip, csrf2, urlFromServiceEngine2[0], se_cloud_url,
                                               "detailsOfServiceEngine4.json",
                                               vcenter_ip, vcenter_username,
                                               password, ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME2,
                                               Type.WORKLOAD, 2, aviVersion)
    if se_engines[0] is None:
        current_app.logger.error("Failed to  change set interfaces engine 4" + str(se_engines[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to  change set interfaces engine 4" + str(se_engines[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    parent_resourcepool = current_app.config['RESOURCE_POOL']
    create = createResourceFolderAndWait(vcenter_ip, vcenter_username, password,
                                         cluster_name, data_center, ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL,
                                         ResourcePoolAndFolderName.WORKLOAD_FOLDER, parent_resourcepool)
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
    deployWorkload = False
    workload_cluster_name = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
        'tkgWorkloadClusterName']
    management_cluster = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtClusterName']
    kubernetes_ova_version = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadKubeVersion']
    size = str(request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadSize'])
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
        cpu = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadCpuSize']
        memory = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadMemorySize']
        disk = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadStorageSize']
        memory = str(int(memory) * 1024)
    else:
        current_app.logger.error("Provided cluster size: " + size + "is not supported, please provide one of: small/medium/large/extra-large/custom")
        d = {
            "responseType": "ERROR",
            "msg": "Provided cluster size: " + size + "is not supported, please provide one of: small/medium/large/extra-large/custom",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    pod_cidr = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadClusterCidr']
    service_cidr = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadServiceCidr']
    machineCount = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
        'tkgWorkloadWorkerMachineCount']
    cluster_plan = str(
        request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadDeploymentType'])
    datacenter_path = "/" + data_center
    datastore_path = datacenter_path + "/datastore/" + data_store
    workload_folder_path = datacenter_path + "/vm/" + ResourcePoolAndFolderName.WORKLOAD_FOLDER
    if parent_resourcepool:
        workload_resource_path = datacenter_path + "/host/" + cluster_name + "/Resources/" + parent_resourcepool + "/" + ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL
    else:
        workload_resource_path = datacenter_path + "/host/" + cluster_name + "/Resources/" + ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL
    workload_network_path = datacenter_path + "/network/" + SegmentsName.DISPLAY_NAME_TKG_WORKLOAD

    if not createClusterFolder(workload_cluster_name):
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create directory: " + Paths.CLUSTER_PATH + workload_cluster_name,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    current_app.logger.info(
        "The config files for shared services cluster will be located at: " + Paths.CLUSTER_PATH + workload_cluster_name)
    if Tkg_version.TKG_VERSION == "1.3":
        control_plane_end_point = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
            'TKG_Workload_ControlPlane_IP']
        createWorkloadCluster = ["tmc", "cluster", "create", "-t", "tkg-vsphere", "-n", workload_cluster_name, "-m",
                                 management_cluster, "-p", "default", "--cluster-group", "default",
                                 "--control-plane-endpoint", control_plane_end_point, "--ssh-key",
                                 re, "--version", Versions.tkg, "--datacenter",
                                 datacenter_path, "--datastore", datastore_path, "--folder", workload_folder_path,
                                 "--resource-pool", workload_resource_path, "--workspace-network",
                                 workload_network_path,
                                 "--control-plane-cpu", cpu, "--control-plane-disk-gib", disk,
                                 "--control-plane-memory-mib",
                                 memory, "--worker-node-count", machineCount, "--worker-cpu", cpu, "--worker-disk-gib",
                                 disk,
                                 "--worker-memory-mib", memory]
    if Tkg_version.TKG_VERSION == "1.5":
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

        if checkTmcEnabled(env):
            clusterGroup = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadClusterGroupName']
        else:
            clusterGroup = "default"

        if not clusterGroup:
            clusterGroup = "default"

        # workload_network_folder_path = getNetworkPathTMC(SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment,
        #                                                vcenter_ip, vcenter_username, password)
        if cluster_plan.lower() == PLAN.PROD_PLAN:
            createWorkloadCluster = ["tmc", "cluster", "create", "-t", "tkg-vsphere", "-n", workload_cluster_name, "-m",
                                     management_cluster, "-p", "default", "--cluster-group", clusterGroup,
                                     "--ssh-key", re, "--version", version, "--datacenter", datacenter_path,
                                     "--datastore",
                                     datastore_path, "--folder", workload_folder_path, "--resource-pool",
                                     workload_resource_path,
                                     "--workspace-network", workload_network_path, "--control-plane-cpu", cpu,
                                     "--control-plane-disk-gib", disk, "--control-plane-memory-mib", memory,
                                     "--worker-node-count", machineCount, "--worker-cpu", cpu, "--worker-disk-gib",
                                     disk, "--worker-memory-mib", memory, "--pods-cidr-blocks", pod_cidr,
                                     "--service-cidr-blocks", service_cidr, "--high-availability"]
        else:
            createWorkloadCluster = ["tmc", "cluster", "create", "-t", "tkg-vsphere", "-n", workload_cluster_name, "-m",
                                     management_cluster, "-p", "default", "--cluster-group", clusterGroup,
                                     "--ssh-key", re, "--version", version, "--datacenter", datacenter_path,
                                     "--datastore",
                                     datastore_path, "--folder", workload_folder_path, "--resource-pool",
                                     workload_resource_path,
                                     "--workspace-network", workload_network_path, "--control-plane-cpu", cpu,
                                     "--control-plane-disk-gib", disk, "--control-plane-memory-mib", memory,
                                     "--worker-node-count", machineCount, "--worker-cpu", cpu, "--worker-disk-gib",
                                     disk, "--worker-memory-mib", memory, "--pods-cidr-blocks", pod_cidr,
                                     "--service-cidr-blocks", service_cidr]

    isCheck = False
    found = False
    if command_status[0] is None:
        if Tkg_version.TKG_VERSION == "1.5" and checkTmcEnabled(env):
            current_app.logger.info("Deploying shared cluster")
            for i in tqdm(range(150), desc="Waiting for folder to be available in tmc…", ascii=False, ncols=75):
                time.sleep(1)
            current_app.logger.info("Deploying workload cluster")
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
            wip = getVipNetworkIpNetMask(ip, csrf2, aviVersion)
            if wip[0] is None or wip[0] == "NOT_FOUND":
                current_app.logger.error("Failed to get wip netmask ")
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get wip netmask ",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            createAkoFile(ip, wip[0], workload_cluster_name)
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
            lisOfCommand = ["kubectl", "apply", "-f", Paths.CLUSTER_PATH + workload_cluster_name + '/ako_workloadset1.yaml', "--validate=false"]
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
            isCheck = True
            if not checkTmcEnabled(env):
                current_app.logger.info("Deploying workload cluster using tanzu 1.5")
                deploy_status = deployCluster(workload_cluster_name, cluster_plan,
                                              data_center, data_store, workload_folder_path, workload_network_path,
                                              vsphere_password,
                                              workload_resource_path, vcenter_ip, re, vcenter_username, machineCount,
                                              size, env, Type.WORKLOAD, vmcSpec)
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
                    current_app.logger.info("Deploying workload cluster, after verification, using tmc")
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
                # else:
                #     deploy_status = deployCluster(workload_cluster_name, cluster_plan,
                #                                   data_center, data_store, workload_folder_path, workload_network_path,
                #                                   vsphere_password,
                #                                   workload_resource_path, vcenter_ip, re, vcenter_username,
                #                                   machineCount,
                #                                   size, env, Type.WORKLOAD, vmcSpec)
                #     if deploy_status[0] is None:
                #         current_app.logger.error("Failed to deploy cluster " + deploy_status[1])
                #         d = {
                #             "responseType": "ERROR",
                #             "msg": "Failed to deploy cluster " + deploy_status[1],
                #             "ERROR_CODE": 500
                #         }
                #         return jsonify(d), 500
        else:
            current_app.logger.info("Workload cluster is already deployed and running ")
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
        if verifyPodsAreRunning(AppName.AKO, command_status[0], RegexPattern.RUNNING):
            found = True
        if verifyPodsAreRunning(workload_cluster_name, command_status[0], RegexPattern.running):
            found = True
        while not verifyPodsAreRunning(workload_cluster_name, command_status[0], RegexPattern.running) and count < 60:
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
    # if command_status_ako[1] != 0:
    #     current_app.logger.error("Failed to check pods are running " + command_status_ako[0])
    #     d = {
    #         "responseType": "ERROR",
    #         "msg": "Failed to check pods are running " + command_status_ako[0],
    #         "ERROR_CODE": 500
    #     }
    #     return jsonify(d), 500
    while not verifyPodsAreRunning(AppName.AKO, command_status_ako[0], RegexPattern.RUNNING) and count_ako < 60:
        command_status = grabPipeOutput(podRunninng_ako_main, podRunninng_ako_grep)
        if command_status[1] != 0:
            current_app.logger.error("Failed to check pods are running " + str(command_status_ako[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to check pods are running " + str(command_status_ako[0]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        if verifyPodsAreRunning(AppName.AKO, command_status[0], RegexPattern.RUNNING):
            break
        count_ako = count_ako + 1
        time.sleep(30)
        current_app.logger.info("Waited for  " + str(count_ako * 30) + "s, retrying.")
    if not verifyPodsAreRunning(AppName.AKO, command_status_ako[0], RegexPattern.RUNNING):
        current_app.logger.error("Ako pods are not running on waiting " + str(count_ako * 30))
        d = {
            "responseType": "ERROR",
            "msg": "Ako pods are not running on waiting " + str(count_ako * 30),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if not deployWorkload:
        current_app.logger.info("Waiting for cluster in healthy state")
        for i in tqdm(range(120), desc="Waiting for cluster in healthy state…", ascii=False, ncols=75):
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
    current_app.logger.info("Switched to the workload context")
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
        cluster_admin_users = \
            request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadRbacUserRoleSpec'][
                'clusterAdminUsers']
        admin_users = \
            request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadRbacUserRoleSpec'][
                'adminUsers']
        edit_users = \
            request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadRbacUserRoleSpec'][
                'editUsers']
        view_users = \
            request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadRbacUserRoleSpec'][
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
        state = registerWithTmcOnSharedAndWorkload(env, workload_cluster_name,
                                                   "false", "workload")
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


def getVipNetworkIpNetMask(ip, csrf2, aviVersion):
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
                if re['name'] == Cloud.WIP_WORKLOAD_NETWORK_NAME:
                    for sub in re["configured_subnets"]:
                        return str(sub["prefix"]["ip_addr"]["addr"]) + "/" + str(sub["prefix"]["mask"]), "SUCCESS"
            else:
                next_url = None if not response_csrf.json()["next"] else response_csrf.json()["next"]
                while len(next_url) > 0:
                    response_csrf = requests.request("GET", next_url, headers=headers, data=body, verify=False)
                    for re in response_csrf.json()["results"]:
                        if re['name'] == Cloud.WIP_WORKLOAD_NETWORK_NAME:
                            for sub in re["configured_subnets"]:
                                return str(sub["prefix"]["ip_addr"]["addr"]) + "/" + str(
                                    sub["prefix"]["mask"]), "SUCCESS"
                    next_url = None if not response_csrf.json()["next"] else response_csrf.json()["next"]

        return "NOT_FOUND", "FAILED"
    except KeyError:
        return "NOT_FOUND", "FAILED"


def createAkoFile(ip, wipCidr, clusterName):
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
            cloudName=Cloud.CLOUD_NAME,
            clusterSelector=dict(
                matchLabels=dict(
                    type=AkoType.type_ako_set
                )
            ),
            controller=ip,
            dataNetwork=dict(cidr=wipCidr, name=Cloud.WIP_WORKLOAD_NETWORK_NAME),
            extraConfigs=dict(ingress=dict(defaultIngressController=False, disableIngressClass=True)),
            serviceEngineGroup=Cloud.SE_WORKLOAD_GROUP_NAME
        )
    )
    with open(Paths.CLUSTER_PATH + clusterName + '/ako_workloadset1.yaml', 'w') as outfile:
        yaml = ruamel.yaml.YAML()
        yaml.indent(mapping=2, sequence=4, offset=3)
        yaml.dump(data, outfile)


def connectToWorkLoadCluster(env):
    if env == Env.VMC:
        workload_cluster_name = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
            'tkgWorkloadClusterName']
    else:
        workload_cluster_name = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadClusterName']
    current_app.logger.info("Connect to workload cluster")
    commands_shared = ["tanzu", "cluster", "kubeconfig", "get", workload_cluster_name, "--admin"]
    kubeContextCommand_shared = grabKubectlCommand(commands_shared, RegexPattern.SWITCH_CONTEXT_KUBECTL)
    if kubeContextCommand_shared is None:
        current_app.logger.error("Failed to get switch to workload cluster context command")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get switch to workload cluster context command",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    lisOfSwitchContextCommand_shared = str(kubeContextCommand_shared).split(" ")
    status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand_shared)
    if status[1] != 0:
        current_app.logger.error("Failed to switch to workload cluster context " + str(status[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to switch to workload cluster context " + str(status[0]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    d = {
        "responseType": "SUCCESS",
        "msg": "Switch to workload cluster context ",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


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
