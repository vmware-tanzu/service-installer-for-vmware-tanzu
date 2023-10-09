import json
import os
import time

import requests
from flask import current_app, jsonify, request
from tqdm import tqdm

from common.common_utilities import VrfType, addStaticRoute, envCheck, getVrfAndNextRoutId, obtain_second_csrf
from common.lib.avi.avi_infra_operations import AVIInfraOps
from common.lib.govc.govc_client import GOVClient
from common.operation.constants import Cloud, ControllerLocation, Env, ResourcePoolAndFolderName, SegmentsName, Type
from common.operation.ShellHelper import runShellCommandWithPolling
from common.operation.vcenter_operations import checkforIpAddress, checkVmPresent, getMacAddresses, getSi
from common.replace_value import replaceMac, replaceSe, replaceSeGroup, replaceValueSysConfig
from common.util.local_cmd_helper import LocalCmdHelper

__author__ = "Pooja Deshmukh"


# TODO: this class has vsphere/vcf related function implementation, can be reuse for vmc env
class ServiceEngineUtils:
    def __init__(self, spec):
        self.spec = spec

    def controller_deployment(
        self,
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
            token = self.generate_token(ip, csrf2, aviVersion, Cloud.CLOUD_NAME_VSPHERE)
            if token[0] is None:
                current_app.logger.error("Failed to get token " + str(token[1]))
                d = {"responseType": "ERROR", "msg": "Failed to  token " + str(token[1]), "STATUS_CODE": 500}
                return jsonify(d), 500
            current_app.logger.info("Get cluster uuid")
            uuid = self.get_cluster_uuid(ip, csrf2, aviVersion)
            if uuid[0] is None:
                current_app.logger.error("Failed to get cluster uuid " + str(uuid[1]))
                d = {"responseType": "ERROR", "msg": "Failed to get cluster uuid " + str(uuid[1]), "STATUS_CODE": 500}
                return jsonify(d), 500
            if type == Type.WORKLOAD:
                self.replace_network_values_workload(ip, token[0], uuid[0], seJson, env=env)
            else:
                self.replace_network_values_vsphere(ip, token[0], uuid[0], seJson)
            deploy_se = self.deploy_se_engines(
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
                env,
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
            token = self.generate_token(ip, csrf2, aviVersion, Cloud.CLOUD_NAME_VSPHERE)
            if token[0] is None:
                current_app.logger.error("Failed to get token " + str(token[0]))
                d = {"responseType": "ERROR", "msg": "Failed to  token " + str(token[0]), "STATUS_CODE": 500}
                return jsonify(d), 500
            current_app.logger.info("Get cluster uuid")
            uuid = self.get_cluster_uuid(ip, csrf2, aviVersion)
            if uuid[0] is None:
                current_app.logger.error("Failed to get cluster uuid " + str(uuid[0]))
                d = {"responseType": "ERROR", "msg": "Failed to get cluster uuid " + str(uuid[0]), "STATUS_CODE": 500}
                return jsonify(d), 500
            self.replace_network_values_vsphere(ip, token[0], uuid[0], seJson)
            deploy_se2 = self.deploy_se_engines(
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
                env,
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
        urlFromServiceEngine1 = self.list_all_service_engine(
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
        urlFromServiceEngine2 = self.list_all_service_engine(
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
        details1 = self.get_details_of_service_engine(ip, csrf2, urlFromServiceEngine1[0], detailsJson1, aviVersion)
        if details1[0] is None:
            current_app.logger.error("Failed to get details of engine 1" + str(details1[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get details of engine 1" + str(details1[1]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        details2 = self.get_details_of_service_engine(ip, csrf2, urlFromServiceEngine2[0], detailsJson2, aviVersion)
        if details2[0] is None:
            current_app.logger.error("Failed to get details of engine 2 " + str(details2[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get details of engine 2 " + str(details2[1]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500

        se_engines = self.change_se_group_and_set_interfaces(
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
        se_engines2 = self.change_se_group_and_set_interfaces(
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
            s = self.get_connected_status(ip, csrf2, i, aviVersion)
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
                if re["name"] == Cloud.CLOUD_NAME_VSPHERE:
                    uuid = re["uuid"]
        if uuid is None:
            return None, "NOT_FOUND"
        if type == Type.WORKLOAD:
            ipNetMask = self.seperate_netmask_and_ip(
                request.get_json(force=True)["tkgWorkloadDataNetwork"]["tkgWorkloadDataNetworkGatewayCidr"]
            )
        else:
            ipNetMask = self.seperate_netmask_and_ip(
                request.get_json(force=True)["tkgMgmtDataNetwork"]["tkgMgmtDataNetworkGatewayCidr"]
            )
            ipNetMask_ = self.seperate_netmask_and_ip(
                request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"][
                    "tkgClusterVipNetworkGatewayCidr"
                ]
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

    def get_details_of_service_engine(self, ip, csrf2, urlFromServiceEngine, file_name, aviVersion):
        url = urlFromServiceEngine
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
        while count < 30:
            response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False, timeout=600)
            if response_csrf.status_code == 200:
                try:
                    if len(response_csrf.json()["data_vnics"]) > 1:
                        break
                    count = count + 1
                    time.sleep(10)
                    current_app.logger.info("Waited to get all the NICs " + str(count * 10) + "s")
                except Exception:
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

    def seperate_netmask_and_ip(self, cidr):
        return str(cidr).split("/")

    def deploy_se_engines(
        self,
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
        env,
    ):
        os.putenv("GOVC_URL", "https://" + vcenter_ip + "/sdk")
        os.putenv("GOVC_USERNAME", vcenter_username)
        os.putenv("GOVC_PASSWORD", password)
        os.putenv("GOVC_INSECURE", "true")
        replaceValueSysConfig(file_name, "Name", "name", engine_name)
        if type == Type.WORKLOAD:
            self.replace_network_values_workload(ip, aviAuthToken, clusterUUid, file_name, env)
        else:
            self.replace_network_values_vsphere(ip, aviAuthToken, clusterUUid, file_name)
        parent_resourcepool = current_app.config["RESOURCE_POOL"]
        if parent_resourcepool is not None:
            rp_pool = (
                data_center
                + "/host/"
                + cluster_name
                + "/Resources/"
                + parent_resourcepool
                + "/"
                + ResourcePoolAndFolderName.AVI_RP_VSPHERE
            )
        else:
            rp_pool = data_center + "/host/" + cluster_name + "/Resources/" + ResourcePoolAndFolderName.AVI_RP_VSPHERE
        ova_deploy_command = [
            "govc",
            "import.ova",
            "-options",
            file_name,
            "-dc=" + data_center,
            "-ds=" + data_store,
            "-folder=" + ResourcePoolAndFolderName.AVI_Components_FOLDER_VSPHERE,
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

    def generate_token(self, ip, csrf2, aviVersion, cloud_name):
        with open("./newCloudInfo.json", "r") as file2:
            new_cloud_json = json.load(file2)
        uuid = None
        try:
            uuid = new_cloud_json["uuid"]
        except Exception:
            for re in new_cloud_json["results"]:
                if re["name"] == cloud_name:
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
            "x-csrftoken": csrf2[0],
        }
        payload = {}
        response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False, timeout=600)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        else:
            return response_csrf.json()["auth_token"], 200

    def replace_network_values(self, ip, aviAuthToken, clusterUUid, file_name):
        tkg_management = request.get_json(force=True)["componentSpec"]["tkgMgmtSpec"]["tkgMgmtNetworkName"]
        property_mapping = {"AVICNTRL": ip, "AVICNTRL_AUTHTOKEN": aviAuthToken, "AVICNTRL_CLUSTERUUID": clusterUUid}
        for key, value in property_mapping.items():
            replaceSe(file_name, "PropertyMapping", key, "Key", "Value", value)
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
            "Data Network 9": SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment,
        }
        for key, value in dictionary_network.items():
            replaceSe(file_name, "NetworkMapping", key, "Name", "Network", value)

    def replace_network_values_vsphere(self, ip, avi_auth_token, cluster_uuid, file_name):
        tkg_management = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtNetworkName
        avi_management = self.spec.tkgComponentSpec.aviMgmtNetwork.aviMgmtNetworkName
        avi_data_pg = self.spec.tkgMgmtDataNetwork.tkgMgmtDataNetworkName
        tkg_cluster_vip_name = self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkName
        property_mapping = {"AVICNTRL": ip, "AVICNTRL_AUTHTOKEN": avi_auth_token, "AVICNTRL_CLUSTERUUID": cluster_uuid}
        for key, value in property_mapping.items():
            replaceSe(file_name, "PropertyMapping", key, "Key", "Value", value)
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
        for key, value in dictionary_network.items():
            replaceSe(file_name, "NetworkMapping", key, "Name", "Network", value)

    def replace_network_values_workload(self, ip, aviAuthToken, clusterUUid, file_name, env):
        tkg_management = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtNetworkName
        avi_management = self.spec.tkgComponentSpec.aviMgmtNetwork.aviMgmtNetworkName
        avi_data_pg = self.spec.tkgMgmtDataNetwork.tkgMgmtDataNetworkName
        tkg_cluster_vip_name = self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkName
        workload_vip = self.spec.tkgWorkloadDataNetwork.tkgWorkloadDataNetworkName
        property_mapping = {"AVICNTRL": ip, "AVICNTRL_AUTHTOKEN": aviAuthToken, "AVICNTRL_CLUSTERUUID": clusterUUid}
        for key, value in property_mapping.items():
            replaceSe(file_name, "PropertyMapping", key, "Key", "Value", value)
        if env == Env.VMC:
            dictionary_network = {
                "Management": SegmentsName.DISPLAY_NAME_AVI_MANAGEMENT,
                "Data Network 1": SegmentsName.DISPLAY_NAME_CLUSTER_VIP,
                "Data Network 2": SegmentsName.DISPLAY_NAME_TKG_WORKLOAD,
                "Data Network 3": SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT,
                "Data Network 4": SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT,
                "Data Network 5": SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT,
                "Data Network 6": SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT,
                "Data Network 7": SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT,
                "Data Network 8": SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT,
                "Data Network 9": SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT,
            }
        else:
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

    def get_cluster_uuid(self, ip, csrf2, aviVersion):
        url = "https://" + ip + "/api/cluster"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0],
        }
        payload = {}
        response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False, timeout=600)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        else:
            return response_csrf.json()["uuid"], 200

    def get_connected_status(self, ip, csrf2, se_engine_url, aviVersion):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0],
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

    def change_se_group_and_set_interfaces(
        self,
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
            self.change_mac_address_and_seGroup_in_file_workload(
                vcenter_ip, vcenter_username, password, vm_name, se_cloud_url, file_name, name
            )
        else:
            self.change_mac_address_and_seGroup_in_file(
                vcenter_ip, vcenter_username, password, vm_name, se_cloud_url, file_name
            )
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

    def change_mac_address_and_seGroup_in_file(
        self, vcenter_ip, vcenter_username, password, vm_name, segroupUrl, file_name
    ):
        d = getMacAddresses(getSi(vcenter_ip, vcenter_username, password), vm_name)
        mac1 = d[1]
        mac2 = d[2]
        mac3 = d[3]
        replaceSeGroup(file_name, "se_group_ref", "false", segroupUrl)
        replaceMac(file_name, mac1)
        replaceMac(file_name, mac2)
        replaceMac(file_name, mac3)
        mac4 = d[4]
        replaceMac(file_name, mac4)

    def change_mac_address_and_seGroup_in_file_workload(
        self, vcenter_ip, vcenter_username, password, vm_name, segroupUrl, file_name, number
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
            replaceMac(file_name, mac3)
        replaceSeGroup(file_name, "se_group_ref", "false", segroupUrl)

    def change_networks(self, vcenter_ip, vcenter_username, password, engine_name):
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

    def list_all_service_engine(
        self, ip, csrf2, countSe, name, controllerName, vcenter_ip, vcenter_username, password, aviVersion
    ):
        with open("./newCloudInfo.json", "r") as file2:
            new_cloud_json = json.load(file2)
        uuid = None
        try:
            uuid = new_cloud_json["uuid"]
        except Exception:
            for re in new_cloud_json["results"]:
                if re["name"] == Cloud.CLOUD_NAME_VSPHERE:
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

    def _create_workload_service_engines(
        self,
        ip,
        avi_password,
        csrf2,
        vcenter_ip,
        vcenter_username,
        password,
        vc_cluster_name,
        data_center,
        data_store,
        aviVersion,
    ):
        avi_infra_obj = AVIInfraOps(ip, avi_password, vcenter_ip, vcenter_username, password)
        govc_client = GOVClient(
            vcenter_ip, vcenter_username, password, vc_cluster_name, data_center, data_store, LocalCmdHelper()
        )
        count = 0
        found = False
        seIp3 = None
        while count < 120:
            try:
                current_app.logger.info("Waited " + str(10 * count) + "s to get controller 3 ip, retrying")
                seIp3 = govc_client.get_vm_ip(ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME_VSPHERE)
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
                seIp4 = govc_client.get_vm_ip(ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME2_VSPHERE)
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
        urlFromServiceEngine1 = self.list_all_service_engine(
            ip,
            csrf2,
            3,
            seIp3,
            ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME_VSPHERE,
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
        urlFromServiceEngine2 = self.list_all_service_engine(
            ip,
            csrf2,
            3,
            seIp4,
            ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME2_VSPHERE,
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
        details1 = self.get_details_of_service_engine(
            ip, csrf2, urlFromServiceEngine1[0], "detailsOfServiceEngine3.json", aviVersion
        )
        if details1[0] is None:
            current_app.logger.error("Failed to get details of engine 3" + str(details1[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get details of engine 3" + str(details1[1]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        details2 = self.get_details_of_service_engine(
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
        get_se_cloud = avi_infra_obj.get_SE_cloud_status(Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE)
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
        change = self.change_networks(
            vcenter_ip,
            vcenter_username,
            password,
            ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME_VSPHERE,
        )
        if change[1] != 200:
            current_app.logger.error("Failed to change Network " + str(change[0]))
            d = {"responseType": "ERROR", "msg": "Failed to change Network " + str(change[0]), "STATUS_CODE": 500}
            return jsonify(d), 500

        # TODO : change_se_group_and_set_interfaces has diff functionalit in avi_infra_obj
        se_engines = self.change_se_group_and_set_interfaces(
            ip,
            csrf2,
            urlFromServiceEngine1[0],
            se_cloud_url,
            "detailsOfServiceEngine3.json",
            vcenter_ip,
            vcenter_username,
            password,
            ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME_VSPHERE,
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
        change = self.change_networks(
            vcenter_ip,
            vcenter_username,
            password,
            ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME2_VSPHERE,
        )
        if change[1] != 200:
            current_app.logger.error("Failed to change Network for service engine controller 4 " + str(change[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to change Network for service engine controller 4 " + str(change[0]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        se_engines = self.change_se_group_and_set_interfaces(
            ip,
            csrf2,
            urlFromServiceEngine2[0],
            se_cloud_url,
            "detailsOfServiceEngine4.json",
            vcenter_ip,
            vcenter_username,
            password,
            ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME2_VSPHERE,
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
