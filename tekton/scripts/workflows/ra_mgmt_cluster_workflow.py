#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
from pathlib import Path
from re import sub
import json
import time
from jinja2 import Template
import requests
from tqdm import tqdm
import base64
from constants.constants import Constants, Paths, TKGCommands, ComponentPrefix, AkoType, \
    ControllerLocation, KubernetesOva, Cloud, VrfType, ResourcePoolAndFolderName
from lib.tkg_cli_client import TkgCliClient
from model.run_config import RunConfig
from model.spec import Bootstrap
from model.vsphereSpec import VsphereMasterSpec
from model.status import HealthEnum, Info
from util.cmd_helper import CmdHelper
from util.file_helper import FileHelper
from util.git_helper import Git
from util.govc_helper import get_alb_ip_address
from util.logger_helper import LoggerHelper, log
from util.avi_api_helper import isAviHaEnabled, obtain_second_csrf
from util.ssh_helper import SshHelper
from util.ssl_helper import get_base64_cert
from util.tanzu_utils import TanzuUtils
from workflows.cluster_common_workflow import ClusterCommonWorkflow
import subprocess
import shutil
import traceback
from util.common_utils import createSubscribedLibrary, downloadAndPushKubernetesOvaMarketPlace, \
    getCloudStatus, seperateNetmaskAndIp, getSECloudStatus, getSeNewBody, getVrfAndNextRoutId, \
    addStaticRoute, getVipNetworkIpNetMask, getClusterStatusOnTanzu, runSsh, checkenv
from util.replace_value import generateVsphereConfiguredSubnets, replaceValueSysConfig
from util.vcenter_operations import createResourcePool, create_folder
from util.ShellHelper import runProcess, runShellCommandAndReturnOutputAsList

# logger = LoggerHelper.get_logger(Path(__file__).stem)
logger = LoggerHelper.get_logger(name='ra_mgmt_cluster_workflow')

class RaMgmtClusterWorkflow:
    def __init__(self, run_config: RunConfig):
        self.run_config = run_config
        logger.info ("Current deployment state: %s", self.run_config.state)
        jsonpath = os.path.join(self.run_config.root_dir, Paths.MASTER_SPEC_PATH)
        with open(jsonpath) as f:
            self.jsonspec = json.load(f)

        check_env_output = checkenv(self.jsonspec)
        if check_env_output is None:
            msg = "Failed to connect to VC. Possible connection to VC is not available or " \
                  "incorrect spec provided."
            raise Exception(msg)
    @log("Preparing to deploy Management cluster")
    def create_mgmt_cluster(self):
        config_cloud = self.configCloud()
        if config_cloud[1] != 200:

            d = {
                "responseType": "ERROR",
                "msg": "Failed to Config management cluster ",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        config_mgmt = self.configTkgMgmt()
        if config_mgmt[1] != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to Config management cluster ",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        d = {
            "responseType": "SUCCESS",
            "msg": "Management cluster configured Successfully",
            "ERROR_CODE": 200
        }
        logger.info("Management cluster configured Successfully")
        return json.dumps(d), 200

    @log("Template yaml deployment of management cluster in progress...")
    def templateMgmtDeployYaml(self, ip, datacenter, data_store, cluster_name, wpName, wipIpNetmask,
                               vcenter_ip,
                               vcenter_username,
                               password, vsSpec):
        deploy_yaml = FileHelper.read_resource(Paths.TKG_MGMT_SPEC_J2)
        t = Template(deploy_yaml)
        datastore_path = "/" + datacenter + "/datastore/" + data_store
        vsphere_folder_path = "/" + datacenter + "/vm/" + \
                              ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder_VSPHERE
        str_enc = str(password)
        _base64_bytes = str_enc.encode('ascii')
        _enc_bytes = base64.b64encode(_base64_bytes)
        vcenter_passwd = _enc_bytes.decode('ascii')
        management_cluster = vsSpec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtClusterName
        parent_resourcePool = vsSpec.envSpec.vcenterDetails.resourcePoolName
        if parent_resourcePool:
            vsphere_rp = "/" + datacenter + "/host/" + cluster_name + "/Resources/" + \
                         parent_resourcePool + "/" + ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE
        else:
            vsphere_rp = "/" + datacenter + "/host/" + cluster_name + "/Resources/" + \
                         ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE
        datacenter = "/" + datacenter
        ssh_key = runSsh(vcenter_username)
        size = vsSpec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtSize
        control_plane_vcpu = ""
        control_plane_disk_gb = ""
        control_plane_mem_gb = ""
        control_plane_mem_mb = ""
        if size.lower() == "medium":
            pass
        elif size.lower() == "large":
            pass
        elif size.lower() == "extra-large":
            pass
        elif size.lower() == "custom":
            control_plane_vcpu = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtCpuSize']
            control_plane_disk_gb = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtStorageSize']
            control_plane_mem_gb = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtMemorySize']
            control_plane_mem_mb = str(int(control_plane_mem_gb) * 1024)
        else:
            logger.error(
                "Un supported cluster size please specify medium/large/extra-large/custom " + size)
            d = {
                "responseType": "ERROR",
                "msg": "Un supported cluster size please specify medium/large/extra-large/custom " + size,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        try:
            osName = str(self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtBaseOs'])
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
        FileHelper.write_to_file(
            t.render(config=vsSpec, avi_cert=get_base64_cert(ip), ip=ip, wpName=wpName,
                     wipIpNetmask=wipIpNetmask,
                     avi_label_key=AkoType.KEY, avi_label_value=AkoType.VALUE,
                     cluster_name=management_cluster,
                     data_center=datacenter, datastore_path=datastore_path,
                     vsphere_folder_path=vsphere_folder_path, vcenter_passwd=vcenter_passwd,
                     vsphere_rp=vsphere_rp,
                     vcenter_ip=vcenter_ip, ssh_key=ssh_key, vcenter_username=vcenter_username,
                     size_controlplane=size.lower(), size_worker=size.lower(),
                     avi_cluster_vip_network_gateway_cidr=avi_cluster_vip_network_gateway_cidr,
                     air_gapped_repo=air_gapped_repo, repo_certificate=repo_certificate,
                     osName=osName, osVersion=osVersion,
                     size=size, control_plane_vcpu=control_plane_vcpu,
                     control_plane_disk_gb=control_plane_disk_gb,
                     control_plane_mem_mb=control_plane_mem_mb),
            "management_cluster_vsphere.yaml")

    @log("Executing management cluster deployment...")
    def deployManagementCluster(self, management_cluster, ip, data_center, data_store, cluster_name,
                                wpName, wipIpNetmask, vcenter_ip, vcenter_username, password,
                                vsSpec):
        try:
            logger.info('Getting cluster state if any previous clusters are  deployed..')
            if not getClusterStatusOnTanzu(management_cluster, "management"):
                os.system("rm -rf kubeconfig.yaml")
                self.templateMgmtDeployYaml(ip, data_center, data_store, cluster_name, wpName,
                                            wipIpNetmask, vcenter_ip, vcenter_username, password,
                                            vsSpec)

                logger.info("Deploying management cluster")
                os.putenv("DEPLOY_TKG_ON_VSPHERE7", "true")
                listOfCmd = ["tanzu", "management-cluster", "create", "-y", "--file",
                             "management_cluster_vsphere.yaml",
                             "-v",
                             "6"]
                runProcess(listOfCmd)
                listOfCmdKube = ["tanzu", "management-cluster", "kubeconfig", "get",
                                 management_cluster, "--admin",
                                 "--export-file",
                                 "kubeconfig.yaml"]
                runProcess(listOfCmdKube)
                return "SUCCESS", 200
            else:
                return "SUCCESS", 200
        except Exception as e:
            logger.info(traceback.format_exc())
            return None, str(e)

    @log("Creating TKGM management cluster")
    def configTkgMgmt(self):

        json_dict = self.jsonspec
        vsSpec = VsphereMasterSpec.parse_obj(json_dict)
        aviVersion = ControllerLocation.VSPHERE_AVI_VERSION
        vcpass_base64 = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']
        password = CmdHelper.decode_base64(vcpass_base64)
        vcenter_username = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser']
        vcenter_ip = self.jsonspec['envSpec']['vcenterDetails']['vcenterAddress']
        cluster_name = self.jsonspec['envSpec']['vcenterDetails']['vcenterCluster']
        data_center = self.jsonspec['envSpec']['vcenterDetails']['vcenterDatacenter']
        data_store = self.jsonspec['envSpec']['vcenterDetails']['vcenterDatastore']
        parent_resourcepool = self.jsonspec['envSpec']['vcenterDetails']['resourcePoolName']
        try:
            isCreated5 = createResourcePool(vcenter_ip, vcenter_username, password,
                                            cluster_name,
                                            ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE,
                                            parent_resourcepool)
            if isCreated5 is not None:
                logger.info("Created resource pool " +
                            ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE)
        except Exception as e:
            logger.error("Failed to create resource pool " + str(e))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create resource pool " + str(e),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        try:
            isCreated3 = create_folder(vcenter_ip, vcenter_username, password, data_center,
                                       ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder_VSPHERE)
            if isCreated3 is not None:
                logger.info("Created folder " +
                            ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder_VSPHERE)

        except Exception as e:
            logger.error("Failed to create folder " + str(e))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create folder " + str(e),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        avi_fqdn = self.jsonspec['tkgComponentSpec']['aviComponents']['aviController01Fqdn']
        ha_field = self.jsonspec['tkgComponentSpec']['aviComponents']['enableAviHa']
        if isAviHaEnabled(ha_field):
            ip = self.jsonspec['tkgComponentSpec']['aviComponents']['aviClusterFqdn']
        else:
            ip = avi_fqdn
        if ip is None:
            logger.error("Failed to get ip of avi controller")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get ip of avi controller",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        avienc_pass = self.jsonspec['tkgComponentSpec']['aviComponents']['aviPasswordBase64']
        csrf2 = obtain_second_csrf(ip, avienc_pass)
        if csrf2 is None:
            logger.error("Failed to get csrf from new set password")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get csrf from new set password",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        data_network = self.jsonspec["tkgMgmtDataNetwork"]["tkgMgmtDataNetworkName"]
        get_wip = getVipNetworkIpNetMask(ip, csrf2, data_network, aviVersion)
        if get_wip[0] is None or get_wip[0] == "NOT_FOUND":
            logger.error("Failed to get se vip network ip and netmask " + str(get_wip[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get vip network " + str(get_wip[1]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        management_cluster = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
            'tkgMgmtClusterName']
        avi_ip = self.jsonspec['tkgComponentSpec']['aviComponents'][
            'aviController01Ip']
        avi_fqdn = self.jsonspec['tkgComponentSpec']['aviComponents'][
            'aviController01Fqdn']
        if not avi_ip:
            controller_fqdn = ip
        elif not avi_fqdn:
            controller_fqdn = avi_fqdn
        else:
            controller_fqdn = ip
        logger.info("Deploying Management Cluster " + management_cluster)
        deploy_status = self.deployManagementCluster(management_cluster, controller_fqdn,
                                                     data_center, data_store, cluster_name,
                                                     data_network, get_wip[0], vcenter_ip,
                                                     vcenter_username, password, vsSpec)
        if deploy_status[0] is None:
            logger.error("Failed to deploy management cluster " + deploy_status[1])
            d = {
                "responseType": "ERROR",
                "msg": "Failed to deploy management cluster " + deploy_status[1],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        command = ["tanzu", "plugin", "sync"]
        runShellCommandAndReturnOutputAsList(command)
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully configured management cluster ",
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200

    @log("Wait for AVI Default Cloud to be in Ready State")
    def waitForCloudPlacementReady(self, ip, csrf2, name, aviVersion):
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
            response_csrf = requests.request("GET", status_url, headers=headers, data=body,
                                             verify=False)
            if response_csrf.status_code != 200:
                return None, "Failed", "Error"
            try:
                logger.info(name + " cloud state " + response_csrf.json()["state"])
                if response_csrf.json()["state"] == "CLOUD_STATE_PLACEMENT_READY":
                    break
            except:
                pass
            count = count + 1
            time.sleep(10)
            logger.info("Waited for " + str(count * 10) + "s retrying")
        if response_csrf is None:
            logger.info("Waited for " + str(count * 10) + "s default cloud status")
            return None, "Failed", "ERROR"

        return "SUCCESS", "READY", response_csrf.json()["state"]

    @log("Creating mgmt cloud")
    def createNewCloud(self, ip, csrf2, aviVersion):
        vcpass_base64 = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']
        password = CmdHelper.decode_base64(vcpass_base64)
        vcenter_username = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser']
        vcenter_ip = self.jsonspec['envSpec']['vcenterDetails']['vcenterAddress']
        data_center = self.jsonspec['envSpec']['vcenterDetails']['vcenterDatacenter']

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        body = {
            "name": Cloud.CLOUD_NAME_VSPHERE,
            "vtype": "CLOUD_VCENTER",
            "vcenter_configuration": {
                "privilege": "WRITE_ACCESS",
                "deactivate_vm_discovery": False,
                "vcenter_url": vcenter_ip,
                "username": vcenter_username,
                "password": password,
                "datacenter": data_center
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
        response_csrf = requests.request("POST", url, headers=headers, data=json_object,
                                         verify=False)
        if response_csrf.status_code != 201:
            return None, response_csrf.text
        else:
            os.system("rm -rf newCloudInfo.json")
            with open("./newCloudInfo.json", "w") as outfile:
                json.dump(response_csrf.json(), outfile)
            return response_csrf.json()["url"], "SUCCESS"

    @log("Fetching Network url")
    def getNetworkUrl(self, ip, csrf2, name, aviVersion):
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
                response_csrf = requests.request("GET", url, headers=headers, data=payload,
                                                 verify=False)
                if response_csrf.status_code == 200:
                    if response_csrf.json()["count"] > 1:
                        break
                count = count + 1
                time.sleep(10)
                logger.info("Waited for " + str(count * 10) + "s retrying")
            if response_csrf is None:
                logger.info(
                    "Waited for " + str(count * 10) + "s but service engine is not up")
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
                    next_url = None if not response_csrf.json()["next"] else response_csrf.json()[
                        "next"]
                    while len(next_url) > 0:
                        response_csrf = requests.request("GET", next_url, headers=headers,
                                                         data=payload, verify=False)
                        for se in response_csrf.json()["results"]:
                            if se["config"]["name"] == name:
                                return se["config"]["url"], se["config"]["uuid"], "FOUND", "SUCCESS"
                        next_url = None if not response_csrf.json()["next"] else \
                            response_csrf.json()["next"]
            return None, "NOT_FOUND", "Failed"
        except KeyError:
            return None, "NOT_FOUND", "Failed"

    @log("Fetching Network details")
    def getNetworkDetails(self, ip, csrf2, managementNetworkUrl, startIp, endIp, prefixIp, netmask,
                          aviVersion):
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
            logger.info("Ip pools are not configured.")

        os.system("rm -rf managementNetworkDetails.json")
        with open("./managementNetworkDetails.json", "w") as outfile:
            json.dump(response_csrf.json(), outfile)
        generateVsphereConfiguredSubnets("managementNetworkDetails.json", startIp, endIp, prefixIp,
                                         int(netmask))
        return "SUCCESS", 200, details

    @log("Updating Network with IP Pools")
    def updateNetworkWithIpPools(self, ip, csrf2, managementNetworkUrl, fileName, aviVersion):
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
        response_csrf = requests.request("PUT", url, headers=headers, data=json_object_m,
                                         verify=False)
        if response_csrf.status_code != 200:
            count = 0
            if response_csrf.text.__contains__(
                    "Cannot edit network properties till network sync from Service Engines is complete"):
                while count < 10:
                    time.sleep(60)
                    response_csrf = requests.request("PUT", url, headers=headers,
                                                     data=json_object_m, verify=False)
                    if response_csrf.status_code == 200:
                        break
                    logger.info("waited for " + str(count * 60) + "s sync to complete")
                    count = count + 1
            else:
                return 500, response_csrf.text, details
        details["subnet_ip"] = response_csrf.json()["configured_subnets"][0]["prefix"]["ip_addr"][
            "addr"]
        details["subnet_mask"] = response_csrf.json()["configured_subnets"][0]["prefix"]["mask"]
        details["vimref"] = response_csrf.json()["vimgrnw_ref"]
        return 200, "SUCCESS", details

    @log("Getting Details of New Cloud")
    def getDetailsOfNewCloud(self, ip, csrf2, newCloudUrl, vim_ref, captured_ip, captured_mask,
                             aviVersion):
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
            replaceValueSysConfig("detailsOfNewCloud.json", "vcenter_configuration",
                                  "management_network", vim_ref)
            ip_val = dict(ip_addr=dict(addr=captured_ip, type="V4"), mask=captured_mask)
            replaceValueSysConfig("detailsOfNewCloud.json", "vcenter_configuration",
                                  "management_ip_subnet", ip_val)
            return response_csrf.json(), "SUCCESS"

    @log("Updating new cloud details...")
    def updateNewCloud(self, ip, csrf2, newCloudUrl, aviVersion):
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
        response_csrf = requests.request("PUT", newCloudUrl, headers=headers, data=json_object,
                                         verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        else:
            return response_csrf.json(), "SUCCESS"

    @log("Getting Network details of VIP...")
    def getNetworkDetailsVip(self, ip, csrf2, vipNetworkUrl, startIp, endIp, prefixIp, netmask,
                             aviVersion):
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
            logger.info("Ip pools are not configured.")

        os.system("rm -rf vipNetworkDetails.json")
        with open("./vipNetworkDetails.json", "w") as outfile:
            json.dump(response_csrf.json(), outfile)
        generateVsphereConfiguredSubnets("vipNetworkDetails.json", startIp, endIp, prefixIp,
                                         int(netmask))
        return "SUCCESS", 200, details

    @log("Updating VIP with the IP Pools....")
    def updateVipNetworkIpPools(self, ip, csrf2, get_vip, aviVersion):
        try:
            startIp = self.jsonspec["tkgComponentSpec"]['tkgClusterVipNetwork'][
                "tkgClusterVipIpStartRange"]
            endIp = self.jsonspec["tkgComponentSpec"]['tkgClusterVipNetwork'][
                "tkgClusterVipIpEndRange"]
            prefixIpNetmask = seperateNetmaskAndIp(
                self.jsonspec["tkgComponentSpec"]['tkgClusterVipNetwork'][
                    "tkgClusterVipNetworkGatewayCidr"])
            getVIPNetworkDetails = self.getNetworkDetailsVip(ip, csrf2, get_vip[0], startIp, endIp,
                                                             prefixIpNetmask[0], prefixIpNetmask[1],
                                                             aviVersion)
            if getVIPNetworkDetails[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get vip network details " + str(getVIPNetworkDetails[2]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            if getVIPNetworkDetails[0] == "AlreadyConfigured":
                logger.info("Vip Ip pools are already configured.")
                ip_pre = getVIPNetworkDetails[2]["subnet_ip"] + "/" + str(
                    getVIPNetworkDetails[2]["subnet_mask"])
            else:
                update_resp = self.updateNetworkWithIpPools(ip, csrf2, get_vip[0],
                                                            "vipNetworkDetails.json",
                                                            aviVersion)
                if update_resp[0] != 200:
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to update vip network ip pools " + str(update_resp[1]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                ip_pre = update_resp[2]["subnet_ip"] + "/" + str(update_resp[2]["subnet_mask"])
            with open("vip_ip.txt", "w") as e:
                e.write(ip_pre)
            d = {
                "responseType": "SUCCESS",
                "msg": "Updated ip vip pools successfully",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200
        except Exception as e:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to update vip ip pools " + str(e),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

    @log("Fetching IPAM details")
    def getIpam(self, ip, csrf2, name, aviVersion):
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

    @log("Creating IPAM...")
    def createIpam(self, ip, csrf2, managementNetworkUrl, managementDataNetwork, vip_network, name,
                   aviVersion):
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
        response_csrf = requests.request("POST", url, headers=headers, data=json_object,
                                         verify=False)
        if response_csrf.status_code != 201:
            return None, response_csrf.text
        else:
            return response_csrf.json()["url"], "SUCCESS"

    @log("Getting IPAM details of Newly added cloud")
    def getDetailsOfNewCloudAddIpam(self, ip, csrf2, newCloudUrl, ipamUrl, aviVersion):
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

    @log("Updating IPAM...")
    def updateIpam(self, ip, csrf2, newCloudUrl, aviVersion):
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
        response_csrf = requests.request("PUT", newCloudUrl, headers=headers, data=json_object,
                                         verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        else:
            return response_csrf.json(), "SUCCESS"

    @log("Getting Cluster URL")
    def getClusterUrl(self, ip, csrf2, cluster_name, aviVersion):
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
            for cluster in response_csrf.json()["results"]:
                if cluster["name"] == cluster_name:
                    return cluster["url"], "SUCCESS"

            return "NOT_FOUND", "FAILED"

    @log("Creating Service Engine for cloud")
    def createSECloud(self, ip, csrf2, newCloudUrl, seGroupName, clusterUrl, dataStore, aviVersion):
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
        response_csrf = requests.request("POST", url, headers=headers, data=json_object,
                                         verify=False)
        if response_csrf.status_code != 201:
            return None, response_csrf.text
        else:
            return response_csrf.json()["url"], "SUCCESS"

    @log("Getting networking details for DHCP")
    def getNetworkDetailsDhcp(self, ip, csrf2, managementNetworkUrl, aviVersion):
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

    @log("Enabling DHCP for management network")
    def enableDhcpForManagementNetwork(self, ip, csrf2, name, aviVersion):
        getNetwork = self.getNetworkUrl(ip, csrf2, name, aviVersion)
        if getNetwork[0] is None:
            logger.error("Failed to network url " + name)
            d = {
                "responseType": "ERROR",
                "msg": "Failed to network url " + name,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        details = self.getNetworkDetailsDhcp(ip, csrf2, getNetwork[0], aviVersion)
        if details[0] is None:
            logger.error("Failed to network details " + details[1])
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get network details " + details[1],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
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
        response_csrf = requests.request("PUT", getNetwork[0], headers=headers, data=json_object_m,
                                         verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        return "SUCCESS", 200

    @log("Configuring cloud")
    def configCloud(self):

        aviVersion = ControllerLocation.VSPHERE_AVI_VERSION
        vcpass_base64 = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']
        password = CmdHelper.decode_base64(vcpass_base64)
        vcenter_username = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser']
        vcenter_ip = self.jsonspec['envSpec']['vcenterDetails']['vcenterAddress']
        cluster_name = self.jsonspec['envSpec']['vcenterDetails']['vcenterCluster']
        data_center = self.jsonspec['envSpec']['vcenterDetails']['vcenterDatacenter']
        data_store = self.jsonspec['envSpec']['vcenterDetails']['vcenterDatastore']
        refToken = self.jsonspec['envSpec']['marketplaceSpec']['refreshToken']
        req = True
        if refToken:
            kubernetes_ova_os = \
                self.jsonspec["tkgComponentSpec"]["tkgMgmtComponents"][
                    "tkgMgmtBaseOs"]
            kubernetes_ova_version = KubernetesOva.KUBERNETES_OVA_LATEST_VERSION
            logger.info("Kubernetes OVA configs for management cluster")
            down_status = downloadAndPushKubernetesOvaMarketPlace(self.jsonspec,
                                                                  kubernetes_ova_version,
                                                                  kubernetes_ova_os)
            if down_status[0] is None:
                logger.error(down_status[1])
                d = {
                    "responseType": "ERROR",
                    "msg": down_status[1],
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
        else:
            logger.info("MarketPlace refresh token is not provided, "
                        "skipping the download of kubernetes ova")
        avi_fqdn = self.jsonspec['tkgComponentSpec']['aviComponents']['aviController01Fqdn']
        aviClusterFqdn = self.jsonspec['tkgComponentSpec']['aviComponents'][
                'aviClusterFqdn']
        if not avi_fqdn:
            controller_name = ControllerLocation.CONTROLLER_NAME_VSPHERE
        else:
            controller_name = avi_fqdn
        ha_field = self.jsonspec['tkgComponentSpec']['aviComponents']['enableAviHa']
        if isAviHaEnabled(ha_field):
            ip = aviClusterFqdn
        else:
            ip = avi_fqdn
        if ip is None:
            logger.error("Failed to get ip of avi controller")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get ip of avi controller",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        avienc_pass = self.jsonspec['tkgComponentSpec']['aviComponents']['aviPasswordBase64']
        csrf2 = obtain_second_csrf(ip, avienc_pass)
        if csrf2 is None:
            logger.error("Failed to get csrf from new set password")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get csrf from new set password",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        default = self.waitForCloudPlacementReady(ip, csrf2, "Default-Cloud", aviVersion)
        if default[0] is None:
            logger.error("Failed to get default cloud status")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get default cloud status",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        get_cloud = getCloudStatus(ip, csrf2, aviVersion, Cloud.CLOUD_NAME_VSPHERE)
        if get_cloud[0] is None:
            logger.error("Failed to get cloud status " + str(get_cloud[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get cloud status " + str(get_cloud[1]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        isGen = False
        if get_cloud[0] == "NOT_FOUND":
            if req:
                for i in tqdm(range(60), desc="Waiting…", ascii=False, ncols=75):
                    time.sleep(1)
            isGen = True
            logger.info("Creating New cloud " + Cloud.CLOUD_NAME_VSPHERE)
            cloud = self.createNewCloud(ip, csrf2, aviVersion)
            if cloud[0] is None:
                logger.error("Failed to create cloud " + str(cloud[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create cloud " + str(cloud[1]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            cloud_url = cloud[0]
        else:
            cloud_url = get_cloud[0]
        if isGen:
            for i in tqdm(range(60), desc="Waiting…", ascii=False, ncols=75):
                time.sleep(1)
            mgmt_pg = self.jsonspec['tkgComponentSpec']['aviMgmtNetwork']['aviMgmtNetworkName']
            get_management = self.getNetworkUrl(ip, csrf2, mgmt_pg, aviVersion)
            if get_management[0] is None:
                logger.error("Failed to get management network " + str(get_management[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get management network " + str(get_management[1]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            startIp = self.jsonspec["tkgComponentSpec"]["aviMgmtNetwork"][
                "aviMgmtServiceIpStartRange"]
            endIp = self.jsonspec["tkgComponentSpec"]["aviMgmtNetwork"][
                "aviMgmtServiceIpEndRange"]
            prefixIpNetmask = seperateNetmaskAndIp(self.jsonspec["tkgComponentSpec"]
                                                   ["aviMgmtNetwork"]["aviMgmtNetworkGatewayCidr"])
            getManagementDetails = self.getNetworkDetails(ip, csrf2, get_management[0], startIp,
                                                          endIp, prefixIpNetmask[0],
                                                          prefixIpNetmask[1], aviVersion)
            if getManagementDetails[0] is None:
                logger.error(
                    "Failed to get management network details " + str(getManagementDetails[2]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get management network details " + str(
                        getManagementDetails[2]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            if getManagementDetails[0] == "AlreadyConfigured":
                logger.info("Ip pools are already configured.")
                vim_ref = getManagementDetails[2]["vim_ref"]
                ip_pre = getManagementDetails[2]["subnet_ip"]
                mask = getManagementDetails[2]["subnet_mask"]
            else:
                update_resp = self.updateNetworkWithIpPools(ip, csrf2, get_management[0],
                                                            "managementNetworkDetails.json",
                                                            aviVersion)
                if update_resp[0] != 200:
                    logger.error(
                        "Failed to update management network ip pools " + str(update_resp[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to update management network ip pools " + str(
                            update_resp[1]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                vim_ref = update_resp[2]["vimref"]
                mask = update_resp[2]["subnet_mask"]
                ip_pre = update_resp[2]["subnet_ip"]
            new_cloud_status = self.getDetailsOfNewCloud(ip, csrf2, cloud_url, vim_ref, ip_pre,
                                                         mask, aviVersion)
            if new_cloud_status[0] is None:
                logger.error(
                    "Failed to get new cloud details" + str(new_cloud_status[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get new cloud details " + str(new_cloud_status[1]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            updateNewCloudStatus = self.updateNewCloud(ip, csrf2, cloud_url, aviVersion)
            if updateNewCloudStatus[0] is None:
                logger.error("Failed to update cloud " + str(updateNewCloudStatus[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to update cloud " + str(updateNewCloudStatus[1]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            mgmt_data_pg = self.jsonspec['tkgMgmtDataNetwork']['tkgMgmtDataNetworkName']
            get_management_data_pg = self.getNetworkUrl(ip, csrf2, mgmt_data_pg, aviVersion)
            if get_management_data_pg[0] is None:
                logger.error("Failed to get management data network details " +
                             str(get_management_data_pg[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get management data network details " + str(
                        get_management_data_pg[1]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            startIp = self.jsonspec["tkgMgmtDataNetwork"]["tkgMgmtAviServiceIpStartRange"]
            endIp = self.jsonspec["tkgMgmtDataNetwork"]["tkgMgmtAviServiceIpEndRange"]
            prefixIpNetmask = seperateNetmaskAndIp(self.jsonspec["tkgMgmtDataNetwork"]
                                                   ["tkgMgmtDataNetworkGatewayCidr"])
            getManagementDetails_data_pg = self.getNetworkDetails(ip, csrf2,
                                                                  get_management_data_pg[0],
                                                                  startIp, endIp,
                                                                  prefixIpNetmask[0],
                                                                  prefixIpNetmask[1],
                                                                  aviVersion)
            if getManagementDetails_data_pg[0] is None:
                logger.error(
                    "Failed to get management data network details " +
                    str(getManagementDetails_data_pg[2]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get management data network details " + str(
                        getManagementDetails_data_pg[2]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            if getManagementDetails_data_pg[0] == "AlreadyConfigured":
                logger.info("Ip pools are already configured.")
            else:
                update_resp = self.updateNetworkWithIpPools(ip, csrf2, get_management_data_pg[0],
                                                            "managementNetworkDetails.json",
                                                            aviVersion)
                if update_resp[0] != 200:
                    logger.error(
                        "Failed to update management network details " + str(update_resp[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to update management network details " + str(update_resp[1]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
            mgmt_pg = self.jsonspec['tkgComponentSpec']['tkgClusterVipNetwork'][
                'tkgClusterVipNetworkName']
            get_vip = self.getNetworkUrl(ip, csrf2, mgmt_pg, aviVersion)
            if get_vip[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get vip network " + str(get_vip[1]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            vip_pool = self.updateVipNetworkIpPools(ip, csrf2, get_vip, aviVersion)
            if vip_pool[1] != 200:
                logger.error(str(vip_pool[0].json['msg']))
                d = {
                    "responseType": "ERROR",
                    "msg": str(vip_pool[0].json['msg']),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500

            get_ipam = self.getIpam(ip, csrf2, Cloud.IPAM_NAME_VSPHERE, aviVersion)
            if get_ipam[0] is None:
                logger.error("Failed to get se Ipam " + str(get_ipam[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get ipam " + str(get_ipam[1]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500

            isGen = False
            if get_ipam[0] == "NOT_FOUND":
                isGen = True
                logger.info("Creating IPAM " + Cloud.IPAM_NAME_VSPHERE)
                ipam = self.createIpam(ip, csrf2, get_management[0], get_management_data_pg[0],
                                       get_vip[0], Cloud.IPAM_NAME_VSPHERE, aviVersion)
                if ipam[0] is None:
                    logger.error("Failed to create ipam " + str(ipam[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to create  ipam " + str(ipam[1]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                ipam_url = ipam[0]
            else:
                ipam_url = get_ipam[0]

            new_cloud_status = self.getDetailsOfNewCloudAddIpam(ip, csrf2, cloud_url, ipam_url,
                                                                aviVersion)
            if new_cloud_status[0] is None:
                logger.error(
                    "Failed to get new cloud details" + str(new_cloud_status[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get new cloud details " + str(new_cloud_status[1]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            updateIpam_re = self.updateIpam(ip, csrf2, cloud_url, aviVersion)
            if updateIpam_re[0] is None:
                logger.error("Failed to update ipam to cloud " + str(updateIpam_re[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to update ipam to cloud " + str(updateIpam_re[1]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            cluster_name = self.jsonspec["envSpec"]["vcenterDetails"]["vcenterCluster"]
            cluster_status = self.getClusterUrl(ip, csrf2, cluster_name, aviVersion)
            if cluster_status[0] is None:
                logger.error("Failed to get cluster details" + str(cluster_status[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get cluster details " + str(cluster_status[1]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            if cluster_status[0] == "NOT_FOUND":
                logger.error("Failed to get cluster details" + str(cluster_status[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get cluster details " + str(cluster_status[1]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            get_se_cloud = getSECloudStatus(ip, csrf2, aviVersion, Cloud.SE_GROUP_NAME_VSPHERE)
            if get_se_cloud[0] is None:
                logger.error("Failed to get se cloud status " + str(get_se_cloud[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get se cloud status " + str(get_se_cloud[1]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500

            isGen = False
            if get_se_cloud[0] == "NOT_FOUND":
                isGen = True
                logger.info("Creating New se cloud " + Cloud.SE_GROUP_NAME_VSPHERE)
                cloud_se = self.createSECloud(ip, csrf2, cloud_url, Cloud.SE_GROUP_NAME_VSPHERE,
                                              cluster_status[0], data_store,
                                              aviVersion)
                if cloud_se[0] is None:
                    logger.error("Failed to create se cloud " + str(cloud_se[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to create  se cloud " + str(cloud_se[1]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                se_cloud_url = cloud_se[0]
            else:
                se_cloud_url = get_se_cloud[0]
            mgmt_name = self.jsonspec["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtNetworkName"]
            dhcp = self.enableDhcpForManagementNetwork(ip, csrf2, mgmt_name, aviVersion)
            if dhcp[0] is None:
                logger.error("Failed to enable dhcp " + str(dhcp[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to enable dhcp " + str(dhcp[1]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500

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
                self.jsonspec["tkgComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkGatewayCidr"])
            vrf = getVrfAndNextRoutId(ip, csrf2, uuid, VrfType.MANAGEMENT, ipNetMask[0], aviVersion)
            if vrf[0] is None or vrf[1] == "NOT_FOUND":
                logger.error("Vrf not found " + str(vrf[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Vrf not found " + str(vrf[1]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            if vrf[1] != "Already_Configured":
                ad = addStaticRoute(ip, csrf2, vrf[0], ipNetMask[0], vrf[1], aviVersion)
                if ad[0] is None:
                    logger.error("Failed to add static route " + str(ad[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Vrf not found " + str(ad[1]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
            prefixIpNetmask_vip = seperateNetmaskAndIp(
                self.jsonspec['tkgComponentSpec']["tkgClusterVipNetwork"][
                    "tkgClusterVipNetworkGatewayCidr"])
            list_ = [prefixIpNetmask[0], prefixIpNetmask_vip[0]]
            for l in list_:
                vrf = getVrfAndNextRoutId(ip, csrf2, uuid, VrfType.GLOBAL, l, aviVersion)
                if vrf[0] is None or vrf[1] == "NOT_FOUND":
                    logger.error("Vrf not found " + str(vrf[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Vrf not found " + str(vrf[1]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                if vrf[1] != "Already_Configured":
                    ad = addStaticRoute(ip, csrf2, vrf[0], l, vrf[1], aviVersion)
                    if ad[0] is None:
                        logger.error("Failed to add static route " + str(ad[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Vrf not found " + str(ad[1]),
                            "ERROR_CODE": 500
                        }
                        return json.dumps(d), 500
        logger.info("Configured management cluster cloud successfully")
        d = {
            "responseType": "SUCCESS",
            "msg": "Configured management cluster cloud successfully",
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200


