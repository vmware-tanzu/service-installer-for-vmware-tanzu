#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
from pathlib import Path
import traceback
import json
import base64
import time
from constants.constants import TKG_EXTENSIONS_ROOT, Constants, Paths, Task, ControllerLocation, \
    Cloud, VrfType, RegexPattern, AkoType, AppName, Versions, ResourcePoolAndFolderName, PLAN, \
    Sizing, ClusterType, Repo, Avi_Version, Avi_Tkgs_Version
from lib.kubectl_client import KubectlClient
from lib.tkg_cli_client import TkgCliClient
from model.run_config import RunConfig
from util.cmd_helper import CmdHelper
from util.file_helper import FileHelper
from util.git_helper import Git
from util.logger_helper import LoggerHelper, log, log_debug
from util.cmd_runner import RunCmd
from workflows.cluster_common_workflow import ClusterCommonWorkflow
from util.common_utils import downloadAndPushKubernetesOvaMarketPlace, getCloudStatus, \
    getVrfAndNextRoutId, addStaticRoute, getVipNetworkIpNetMask, getSECloudStatus, \
    createResourceFolderAndWait, getNetworkFolder, deployCluster, verifyPodsAreRunning,\
    registerWithTmcOnSharedAndWorkload, registerTanzuObservability, registerTSM,\
    installCertManagerAndContour, runSsh, checkenv, checkNameSpaceRunningStatus, getClusterID, getPolicyID, \
    getLibraryId, getBodyResourceSpec, cidr_to_netmask, getCountOfIpAdress, seperateNetmaskAndIp, configureKubectl, \
    createClusterFolder, supervisorTMC, checkTmcEnabled, get_alias_name, convertStringToCommaSeperated, \
    checkClusterVersionCompatibility, checkToEnabled, checkTSMEnabled, checkDataProtectionEnabled, \
    enable_data_protection
from util.ShellHelper import runShellCommandAndReturnOutput
from util.avi_api_helper import isAviHaEnabled, obtain_second_csrf
from workflows.ra_mgmt_cluster_workflow import RaMgmtClusterWorkflow
from util.ShellHelper import grabKubectlCommand, runShellCommandAndReturnOutputAsList, \
    grabPipeOutput
from util.vcenter_operations import getDvPortGroupId
import ruamel
from ruamel import yaml as ryaml
import yaml
import requests
from model.vsphereSpec import VsphereMasterSpec
from util.tkg_util import TkgUtil


logger = LoggerHelper.get_logger(Path(__file__).stem)


class RaWorkloadClusterWorkflow:
    def __init__(self, run_config: RunConfig):
        self.run_config = run_config
        self.tkg_util_obj = TkgUtil(run_config=self.run_config)
        self.tkg_version_dict = self.tkg_util_obj.get_desired_state_tkg_version()
        self.desired_state_tkg_version = None
        if "tkgs" in self.tkg_version_dict:
            self.jsonpath = os.path.join(self.run_config.root_dir, Paths.TKGS_NS_MASTER_SPEC_PATH)
            self.desired_state_tkg_version = self.tkg_version_dict["tkgs"]
        elif "tkgm" in self.tkg_version_dict:
            self.jsonpath = os.path.join(self.run_config.root_dir, Paths.MASTER_SPEC_PATH)
            self.desired_state_tkg_version = self.tkg_version_dict["tkgm"]
        else:
            raise Exception(f"Could not find supported TKG version: {self.tkg_version_dict}")
        #self.extensions_root = TKG_EXTENSIONS_ROOT[self.desired_state_tkg_version]
        #self.extensions_dir = Paths.TKG_EXTENSIONS_DIR.format(extensions_root=self.extensions_root)
        self.cluster_to_deploy = None
        self.tkg_cli_client = TkgCliClient()
        self.kubectl_client = KubectlClient()
        self.runcmd = RunCmd()
        self.kube_config = os.path.join(self.run_config.root_dir, Paths.REPO_KUBE_TKG_CONFIG)
        self.common_workflow = ClusterCommonWorkflow()
        # Following values must be set in upgrade scenarios
        # prev_version Specifies current running version as per state.yml
        self.prev_version = None
        self.prev_extensions_root = None
        self.prev_extensions_dir = None
        with open(self.jsonpath) as f:
            self.jsonspec = json.load(f)
        self.rcmd = RunCmd()
        self.clusterops = RaMgmtClusterWorkflow(self.run_config)

        check_env_output = checkenv(self.jsonspec)
        if check_env_output is None:
            msg = "Failed to connect to VC. Possible connection to VC is not available or " \
                  "incorrect spec provided."
            raise Exception(msg)
        self.isEnvTkgs_wcp = TkgUtil.isEnvTkgs_wcp(self.jsonspec)
        self.isEnvTkgs_ns = TkgUtil.isEnvTkgs_ns(self.jsonspec)
        self.get_vcenter_details()

    def get_vcenter_details(self):
        """
        Method to get vCenter Details from JSON file
        :return:
        """
        self.vcenter_dict = {}
        try:
            self.vcenter_dict.update({'vcenter_ip': self.jsonspec['envSpec']['vcenterDetails']['vcenterAddress'],
                                      'vcenter_password': CmdHelper.decode_base64(
                                          self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']),
                                      'vcenter_username': self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser'],
                                      'vcenter_cluster_name': self.jsonspec['envSpec']['vcenterDetails'][
                                          'vcenterCluster'],
                                      'vcenter_datacenter': self.jsonspec['envSpec']['vcenterDetails'][
                                          'vcenterDatacenter']
                                      })
        except KeyError as e:
            logger.warning(f"Field  {e} not configured in vcenterDetails")
            pass


    def createAkoFile(self, ip, wipCidr, tkgMgmtDataPg):

        repository = 'projects.registry.vmware.com/tkg/ako'

        data = dict(
            apiVersion='networking.tkg.tanzu.vmware.com/v1alpha1',
            kind='AKODeploymentConfig',
            metadata=dict(
                finalizers=['ako-operator.networking.tkg.tanzu.vmware.com'],
                generation=2,
                name='tkgvsphere-ako-workload-set01'
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
                extraConfigs=dict(image=dict(pullPolicy='IfNotPresent', repository=repository,
                                             version=Versions.ako),
                                  ingress=dict(defaultIngressController=False,
                                               disableIngressClass=True
                                               )),
                serviceEngineGroup=Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE
            )
        )
        with open('./ako_vsphere_workloadset1.yaml', 'w') as outfile:
            yaml = ruamel.yaml.YAML()
            yaml.indent(mapping=2, sequence=4, offset=3)
            yaml.dump(data, outfile)

    def updateIpam_profile(self, ip, csrf2, network_name, aviVersion):
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
        get_network_pg = self.clusterops.getNetworkUrl(ip, csrf2, network_name, aviVersion)
        if get_network_pg[0] is None:
            logger.error("Failed to get  network details " + str(get_network_pg[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get network details " + str(get_network_pg[1]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

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
        response_csrf = requests.request("PUT", ipam_url, headers=headers, data=json_object,
                                         verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        else:
            return response_csrf.json()["url"], "SUCCESS"

    def networkConfig(self, aviVersion, cluster_name, data_store):

        refToken = self.jsonspec['envSpec']['marketplaceSpec']['refreshToken']
        avi_fqdn = self.jsonspec['tkgComponentSpec']['aviComponents']['aviController01Fqdn']
        ha_field = self.jsonspec['tkgComponentSpec']['aviComponents']['enableAviHa']
        if refToken:
            if not (self.isEnvTkgs_wcp or self.isEnvTkgs_ns):
                logger.info("Kubernetes OVA configs for workload cluster")
                kubernetes_ova_os = self.jsonspec["tkgWorkloadComponents"]["tkgWorkloadBaseOs"]
                kubernetes_ova_version = self.jsonspec["tkgWorkloadComponents"]["tkgWorkloadKubeVersion"]
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
            logger.info( "MarketPlace refresh token is not provided, skipping the download "
                         "of kubernetes ova")
        workload_network_name = self.jsonspec['tkgWorkloadDataNetwork']['tkgWorkloadDataNetworkName']
        avi_fqdn = self.jsonspec['tkgComponentSpec']['aviComponents'][
            'aviController01Fqdn']
        ##########################################################
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
            logger.error("Requested cloud is not created")
            d = {
                "responseType": "ERROR",
                "msg": "Requested cloud is not created",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        else:
            cloud_url = get_cloud[0]
        cluster_name = self.jsonspec["envSpec"]["vcenterDetails"]["vcenterCluster"]
        cluster_status = self.clusterops.getClusterUrl(ip, csrf2, cluster_name, aviVersion)
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

        get_ipam = self.clusterops.getIpam(ip, csrf2, Cloud.IPAM_NAME_VSPHERE, aviVersion)
        if get_ipam[0] is None:
            logger.error("Failed to get se Ipam " + str(get_ipam[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get ipam " + str(get_ipam[1]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        update = self.updateIpam_profile(ip, csrf2, workload_network_name, aviVersion)
        if update[0] is None:
            logger.error("Failed to update se Ipam " + str(update[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to update ipam " + str(update[1]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        get_se_cloud = getSECloudStatus(ip, csrf2, aviVersion, Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE)
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
            logger.info("Creating New se cloud " + Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE)
            cloud_se = self.clusterops.createSECloud(ip, csrf2, cloud_url,
                                                     Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE,
                                                     cluster_status[0],
                                                     data_store, aviVersion)
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
        management_cluster = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtClusterName']
        data_network_workload = self.jsonspec["tkgWorkloadDataNetwork"]["tkgWorkloadDataNetworkName"]
        get_management_data_pg = self.clusterops.getNetworkUrl(ip, csrf2, data_network_workload, aviVersion)
        if get_management_data_pg[0] is None:
            logger.error("Failed to get workload data network details " +
                         str(get_management_data_pg[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get workloadt data network details " + str(
                    get_management_data_pg[1]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        startIp = self.jsonspec["tkgWorkloadDataNetwork"]["tkgWorkloadAviServiceIpStartRange"]
        endIp = self.jsonspec["tkgWorkloadDataNetwork"]["tkgWorkloadAviServiceIpEndRange"]
        cidr = self.jsonspec["tkgWorkloadDataNetwork"]["tkgWorkloadDataNetworkGatewayCidr"]
        prefixIpNetmask = str(cidr).split("/")
        getManagementDetails_data_pg = self.clusterops.getNetworkDetails(ip, csrf2,
                                                                         get_management_data_pg[0],
                                                                         startIp, endIp,
                                                                         prefixIpNetmask[0],
                                                                         prefixIpNetmask[1],
                                                                         aviVersion)
        if getManagementDetails_data_pg[0] is None:
            logger.error("Failed to get workload data network details " +
                         str(getManagementDetails_data_pg[2]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get workload data network details " +
                       str(getManagementDetails_data_pg[2]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        if getManagementDetails_data_pg[0] == "AlreadyConfigured":
            logger.info("Ip pools are already configured.")
        else:
            update_resp = self.clusterops.updateNetworkWithIpPools(ip, csrf2,
                                                                   get_management_data_pg[0],
                                                                   "managementNetworkDetails.json",
                                                                   aviVersion)
            if update_resp[0] != 200:
                logger.error("Failed to update ip " + str(update_resp[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get management network details " + str(update_resp[1]),
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
            logger.error("uuid not found ")
            d = {
                "responseType": "ERROR",
                "msg": "uuid not found ",
                "ERROR_CODE": 500
            }
            return json.dumps(d), "NOT_FOUND"
        vrf = getVrfAndNextRoutId(ip, csrf2, uuid, VrfType.GLOBAL, prefixIpNetmask[0], aviVersion)
        if vrf[0] is None or vrf[1] == "NOT_FOUND":
            logger.error("Vrf not found " + str(vrf[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Vrf not found " + str(vrf[1]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        if vrf[1] != "Already_Configured":
            logger.info("Routing is not cofigured , configuring.")
            ad = addStaticRoute(ip, csrf2, vrf[0], prefixIpNetmask[0], vrf[1], aviVersion)
            if ad[0] is None:
                logger.error("Failed to add static route " + str(ad[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Vrf not found " + str(ad[1]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            logger.info("Routing is cofigured")
        commands = ["tanzu", "management-cluster", "kubeconfig", "get", management_cluster,
                    "--admin"]
        kubeContextCommand = grabKubectlCommand(commands, RegexPattern.SWITCH_CONTEXT_KUBECTL)
        if kubeContextCommand is None:
            logger.error("Failed to get switch to management cluster context command")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get switch to management cluster context command",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        lisOfSwitchContextCommand = str(kubeContextCommand).split(" ")
        status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand)
        if status[1] != 0:
            logger.error(
                "Failed to get switch to management cluster context " + str(status[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get switch to management cluster context " + str(status[0]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        podRunninng_ako_main = ["kubectl", "get", "pods", "-A"]
        podRunninng_ako_grep = ["grep", AppName.AKO]
        time.sleep(30)
        timer = 30
        ako_pod_running = False
        command_status_ako = []
        while timer < 600:
            logger.info("Check AKO pods are running. Waited for " + str(timer) + "s retrying")
            command_status_ako = grabPipeOutput(podRunninng_ako_main, podRunninng_ako_grep)
            if command_status_ako[1] != 0:
                time.sleep(30)
                timer = timer + 30
            else:
                ako_pod_running = True
                break
        if not ako_pod_running:
            logger.error("AKO pods are not running on waiting for 10m " + command_status_ako[0])
            d = {
                "responseType": "ERROR",
                "msg": "AKO pods are not running on waiting for 10m " + str(command_status_ako[0]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        wip = getVipNetworkIpNetMask(ip, csrf2, data_network_workload, aviVersion)
        if wip[0] is None or wip[0] == "NOT_FOUND":
            logger.error("Failed to get wip netmask ")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get wip netmask ",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        self.createAkoFile(ip, wip[0], data_network_workload)
        lisOfCommand = ["kubectl", "apply", "-f", "ako_vsphere_workloadset1.yaml",
                        "--validate=false"]
        status = runShellCommandAndReturnOutputAsList(lisOfCommand)
        if status[1] != 0:
            if not str(status[0]).__contains__("already has a value"):
                logger.error("Failed to apply ako" + str(status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to apply ako label " + str(status[0]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
        logger.info("Applied ako successfully")
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully configured workload preconfig",
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200

    def connectToWorkLoadCluster(self):
        workload_cluster_name = self.jsonspec['tkgWorkloadComponents']['tkgWorkloadClusterName']
        logger.info("Connect to workload cluster")
        commands_shared = ["tanzu", "cluster", "kubeconfig", "get", workload_cluster_name,
                           "--admin"]
        kubeContextCommand_shared = grabKubectlCommand(commands_shared,
                                                       RegexPattern.SWITCH_CONTEXT_KUBECTL)
        if kubeContextCommand_shared is None:
            logger.error("Failed to get switch to workload cluster context command")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get switch to workload cluster context command",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        lisOfSwitchContextCommand_shared = str(kubeContextCommand_shared).split(" ")
        status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand_shared)
        if status[1] != 0:
            logger.error(
                "Failed to switch to workload cluster context " + str(status[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to switch to workload cluster context " + str(status[0]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        d = {
            "responseType": "SUCCESS",
            "msg": "Switch to workload cluster context ",
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200

    @log("Deploying Workload Cluster...")
    def deploy(self):
        json_dict = self.jsonspec
        vsSpec = VsphereMasterSpec.parse_obj(json_dict)
        aviVersion = Avi_Tkgs_Version.VSPHERE_AVI_VERSION if TkgUtil.isEnvTkgs_ns(self.jsonspec) else Avi_Version.VSPHERE_AVI_VERSION
        vcpass_base64 = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']
        password = CmdHelper.decode_base64(vcpass_base64)
        vcenter_username = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser']
        vcenter_ip = self.jsonspec['envSpec']['vcenterDetails']['vcenterAddress']
        cluster_name = self.jsonspec['envSpec']['vcenterDetails']['vcenterCluster']
        data_center = self.jsonspec['envSpec']['vcenterDetails']['vcenterDatacenter']
        data_store = self.jsonspec['envSpec']['vcenterDetails']['vcenterDatastore']
        parent_resourcepool = self.jsonspec['envSpec']['vcenterDetails']['resourcePoolName']

        logger.info("Setting up SE groups for workload cluster...")
        network_config = self.networkConfig(aviVersion, cluster_name,data_store)
        if network_config[1] != 200:
            logger.error(network_config[0].json['msg'])
            d = {
                "responseType": "ERROR",  
                "msg": "Failed to Config workload cluster " + str(network_config[0].json['msg']),
                "ERROR_CODE": 500
            }
            raise Exception
        create = createResourceFolderAndWait(vcenter_ip, vcenter_username, password,
                                             cluster_name, data_center,
                                             ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL_VSPHERE,
                                             ResourcePoolAndFolderName.WORKLOAD_FOLDER_VSPHERE,
                                             parent_resourcepool)
        if create[1] != 200:
            logger.error(
                "Failed to create resource pool and folder " + create[0].json['msg'])
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create resource pool " + str(create[0].json['msg']),
                "ERROR_CODE": 500
            }
            raise Exception
        try:
            #with open('/root/.ssh/id_rsa.pub', 'r') as f:
            #   re = f.readline()
            re = runSsh(vcenter_username)
        except Exception as e:
            logger.error("Failed to ssh key from config file " + str(e))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to ssh key from config file " + str(e),
                "ERROR_CODE": 500
            }
            raise Exception

        # Init tanzu cli plugins
        tanzu_init_cmd = "tanzu plugin sync"
        command_status = self.rcmd.run_cmd_output(tanzu_init_cmd)
        logger.debug("Tanzu plugin output: {}".format(command_status))

        podRunninng = ["tanzu", "cluster", "list"]
        command_status = runShellCommandAndReturnOutputAsList(podRunninng)
        if command_status[1] != 0:
            logger.error("Failed to run command to check status of pods")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to run command to check status of pods",
                "ERROR_CODE": 500
            }
            raise Exception
        tmc_required = str(self.jsonspec['envSpec']['saasEndpoints']['tmcDetails']['tmcAvailability'])
        tmc_flag = False
        if tmc_required.lower() == "true":
            tmc_flag = True
        elif tmc_required.lower() == "false":
            tmc_flag = False
            logger.info("Tmc registration is disabled")
        else:
            logger.error("Wrong tmc selection attribute provided " + tmc_required)
            d = {
                "responseType": "ERROR",
                "msg": "Wrong tmc selection attribute provided " + tmc_required,
                "ERROR_CODE": 500
            }
            raise Exception
        cluster_plan = self.jsonspec['tkgWorkloadComponents']['tkgWorkloadDeploymentType']
        if cluster_plan == PLAN.DEV_PLAN:
            additional_command = ""
            machineCount =  self.jsonspec['tkgWorkloadComponents']['tkgWorkloadWorkerMachineCount']
        elif cluster_plan == PLAN.PROD_PLAN:
            additional_command = "--high-availability"
            machineCount = self.jsonspec['tkgWorkloadComponents']['tkgWorkloadWorkerMachineCount']
        else:
            logger.error("Un supported control plan provided please specify prod or dev " +
                         cluster_plan)
            d = {
                "responseType": "ERROR",
                "msg": "Un supported control plan provided please specify prod or dev " +
                       cluster_plan,
                "ERROR_CODE": 500
            }
            raise Exception
        size = str(self.jsonspec['tkgWorkloadComponents']['tkgWorkloadSize'])
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
            cpu = self.jsonspec['tkgWorkloadComponents']['tkgWorkloadCpuSize']
            disk = self.jsonspec['tkgWorkloadComponents']['tkgWorkloadStorageSize']
            control_plane_mem_gb = self.jsonspec['tkgWorkloadComponents']['tkgWorkloadMemorySize']
            memory = str(int(control_plane_mem_gb) * 1024)
        else:
            logger.error("Un supported cluster size please specify "
                         "medium/large/extra-large/custom " + size)
            d = {
                "responseType": "ERROR",
                "msg": "Un supported cluster size please specify"
                       " medium/large/extra-large/custom " + size,
                "ERROR_CODE": 500
            }
            raise Exception
        deployWorkload = False
        workload_cluster_name = self.jsonspec['tkgWorkloadComponents']['tkgWorkloadClusterName']
        management_cluster = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtClusterName']
        workload_network = self.jsonspec['tkgWorkloadComponents']['tkgWorkloadNetworkName']
        vsphere_password = password
        _base64_bytes = vsphere_password.encode('ascii')
        _enc_bytes = base64.b64encode(_base64_bytes)
        vsphere_password = _enc_bytes.decode('ascii')

        datacenter_path = "/" + data_center
        datastore_path = datacenter_path + "/datastore/" + data_store
        workload_folder_path = datacenter_path + "/vm/" +\
                               ResourcePoolAndFolderName.WORKLOAD_FOLDER_VSPHERE
        if parent_resourcepool:
            workload_resource_path = datacenter_path + "/host/" + cluster_name + "/Resources/" + \
                                     parent_resourcepool + "/" + \
                                     ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL_VSPHERE
        else:
            workload_resource_path = datacenter_path + "/host/" + cluster_name + "/Resources/" +\
                                     ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL_VSPHERE
        workload_network_path = getNetworkFolder(workload_network, vcenter_ip, vcenter_username,
                                                 password)
        if not workload_network_path:
            logger.error("Network folder not found for " + workload_network)
            d = {
                "responseType": "ERROR",
                "msg": "Network folder not found for " + workload_network,
                "ERROR_CODE": 500
            }
            raise Exception

        logger.info("Deploying workload cluster using tanzu cli")
        deploy_status = deployCluster(workload_cluster_name, cluster_plan,
                                                  data_center, data_store, workload_folder_path,
                                                  workload_network_path,
                                                  vsphere_password,
                                                  workload_resource_path, vcenter_ip, re,
                                                  vcenter_username, machineCount,
                                                  size, ClusterType.WORKLOAD, vsSpec, self.jsonspec)
        if deploy_status[0] is None:
            logger.error("Failed to deploy workload cluster " + deploy_status[1])
            d = {
                "responseType": "ERROR",
                "msg": "Failed to deploy workload cluster " + deploy_status[1],
                "ERROR_CODE": 500
            }
            raise Exception
        isCheck = True
        count = 0
        if isCheck:
            command_status = runShellCommandAndReturnOutputAsList(podRunninng)
            if command_status[1] != 0:
                logger.error(
                    "Failed to check pods are running " + str(command_status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to check pods are running " + str(command_status[0]),
                    "ERROR_CODE": 500
                }
                raise Exception
            if verifyPodsAreRunning(workload_cluster_name, command_status[0], RegexPattern.running):
                found = True
            while not verifyPodsAreRunning(workload_cluster_name, command_status[0],
                                           RegexPattern.running) and count < 60:
                command_status_next = runShellCommandAndReturnOutputAsList(podRunninng)
                if verifyPodsAreRunning(workload_cluster_name, command_status_next[0],
                                        RegexPattern.running):
                    found = True
                    break
                count = count + 1
                time.sleep(30)
                logger.info("Waited for  " + str(count * 30) + "s, retrying.")
        if not found:
            logger.error(
                workload_cluster_name + " is not running on waiting " + str(count * 30) + "s")
            d = {
                "responseType": "ERROR",
                "msg": workload_cluster_name + " is not running on waiting " + str(count * 30) + "s",
                "ERROR_CODE": 500
            }
            raise Exception
        commands = ["tanzu", "management-cluster", "kubeconfig", "get", management_cluster,
                    "--admin"]
        kubeContextCommand = grabKubectlCommand(commands, RegexPattern.SWITCH_CONTEXT_KUBECTL)
        if kubeContextCommand is None:
            logger.error("Failed to get switch to management cluster context command")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get switch to management cluster context command",
                "ERROR_CODE": 500
            }
            raise Exception
        lisOfSwitchContextCommand = str(kubeContextCommand).split(" ")
        status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand)
        if status[1] != 0:
            logger.error(
                "Failed to get switch to management cluster context " + str(status[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get switch to management cluster context " + str(status[0]),
                "ERROR_CODE": 500
            }
            raise Exception
        lisOfCommand = ["kubectl", "label", "cluster",
                        workload_cluster_name, AkoType.KEY + "=" + AkoType.type_ako_set]
        status = runShellCommandAndReturnOutputAsList(lisOfCommand)
        if status[1] != 0:
            if not str(status[0]).__contains__("already has a value"):
                logger.error("Failed to apply ako label " + str(status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to apply ako label " + str(status[0]),
                    "ERROR_CODE": 500
                }
                raise Exception
        else:
            logger.info("Status: {}".format(status[0]))

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
            logger.info("Waited for  " + str(count_ako * 30) + "s, retrying.")
        if not found:
            logger.error("Ako pods are not running on waiting " + str(count_ako * 30))
            d = {
                "responseType": "ERROR",
                "msg": "Ako pods are not running on waiting " + str(count_ako * 30),
                "ERROR_CODE": 500
            }
            raise Exception

        logger.info("Ako pods are running on waiting " + str(count_ako * 30))
        connectToWorkload = self.connectToWorkLoadCluster()
        if connectToWorkload[1] != 200:
            logger.error("Switching context to workload failed " +
                         connectToWorkload[0].json['msg'])
            d = {
                "responseType": "ERROR",
                "msg": "Switching context to workload failed " + connectToWorkload[0].json['msg'],
                "ERROR_CODE": 500
            }
            raise Exception
        logger.info(
            "Succesfully configured workload cluster and ako pods are running on waiting " + str(
                count_ako * 30))
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully deployed  cluster " + workload_cluster_name,
            "SUCCESS_CODE": 200
        }
        return json.dumps(d), 200

    def deploy_saas_workload(self):

        """
        Check and deploy SaaS Integrations for TMC, TSM
        :return: 200 on Success
                500 on Failure
        """
        workload_cluster_name = self.jsonspec['tkgWorkloadComponents']['tkgWorkloadClusterName']
        logger.info('Attaching to TMC if enabled...')
        tmc_required = str(
            self.jsonspec['envSpec']["saasEndpoints"]['tmcDetails']['tmcAvailability'])
        tmc_flag = False
        if tmc_required.lower() == "true":
            tmc_flag = True
        elif tmc_required.lower() == "false":
            tmc_flag = False
            logger.info("Tmc registration is disabled")
        else:
            logger.error("Wrong tmc selection attribute provided " + tmc_required)
            d = {
                "responseType": "ERROR",
                "msg": "Wrong tmc selection attribute provided " + tmc_required,
                "ERROR_CODE": 500
            }
            # return json.dumps(d), 500
        if tmc_flag:
            state = registerWithTmcOnSharedAndWorkload(self.jsonspec, workload_cluster_name,
                                                       "workload")
            if state[1] != 200:
                logger.error(state[0].json['msg'])
                d = {
                    "responseType": "ERROR",
                    "msg": state[0].json['msg'],
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500

        logger.info('Starting Tanzu Observability Integration if enabled')
        # to_enable = self.jsonspec["envSpec"]["saasEndpoints"]["tanzuObservabilityDetails"][
        #     "tanzuObservabilityAvailability"]
        size = str(self.jsonspec['tkgWorkloadComponents']['tkgWorkloadSize'])
        to = registerTanzuObservability(workload_cluster_name, size, self.jsonspec)
        if to[1] != 200:
            logger.error(to[0].json['msg'])
            d = {
                "responseType": "ERROR",
                "msg": to[0].json['msg'],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        logger.info('Starting TSM Integration if enabled')

        tsm_required = str(self.jsonspec['tkgWorkloadComponents']['tkgWorkloadTsmIntegration'])
        tsm_flag = False
        if tsm_required.lower() == "true":
            tmc_flag = True
        elif tsm_required.lower() == "false":
            tmc_flag = False
            logger.info("Tmc registration is disabled")
            d = {
                "responseType": "SUCCESS",
                "msg": "Completed SaaS Integration..",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200
        else:
            logger.error("Wrong tmc selection attribute provided " + tmc_required)

        if tsm_flag:
            tsm_state = registerTSM(workload_cluster_name, self.jsonspec, size)
            if tsm_state[1] != 200:
                logger.error(tsm_state[0].json['msg'])
                d = {
                    "responseType": "SUCCESS",
                    "msg": "TSM registration failed for workload cluster",
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
        logger.info("Completed SaaS Integration for cluster: {}".format(workload_cluster_name))
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully Completed SaaS Integration",
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200

    # TKGs Code
    def create_workload(self):
        #pre = preChecks()
        # if pre[1] != 200:
        #     current_app.logger.error(pre[0].json['msg'])
        #     d = {
        #         "responseType": "ERROR",
        #         "msg": pre[0].json['msg'],
        #         "ERROR_CODE": 500
        #     }
        #     return jsonify(d), 500
        # env = envCheck()
        # if env[1] != 200:
        #     current_app.logger.error("Wrong env provided " + env[0])
        #     d = {
        #         "responseType": "ERROR",
        #         "msg": "Wrong env provided " + env[0],
        #         "ERROR_CODE": 500
        #     }
        #     return jsonify(d), 500
        # env = env[0]
        vcenter_ip = self.vcenter_dict["vcenter_ip"]
        vcenter_username = self.vcenter_dict["vcenter_username"]
        password = self.vcenter_dict["vcenter_password"]
        name_space = self.createTkgWorkloadCluster(vcenter_ip, vcenter_username, password)
        if name_space[0] is None:
            logger.error("Failed to create workload cluster " + str(name_space[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create workload cluster " + str(name_space[1]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        logger.info("Successfully created workload cluster")
        if checkTmcEnabled(self.jsonspec):
            logger.info("Initiating TKGs SAAS integration")
            size = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']['workerNodeCount']
            workload_cluster_name = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereWorkloadClusterName']
            if checkToEnabled(self.jsonspec):
                to = registerTanzuObservability(workload_cluster_name, size, self.jsonspec)
                if to[1] != 200:
                    logger.error(to[0])
                    d = {
                        "responseType": "SUCCESS",
                        "msg": "TO registration failed for workload cluster",
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
            else:
                logger.info("Tanzu Observability not enabled")
            if checkTSMEnabled(self.jsonspec, self.isEnvTkgs_ns):
                cluster_version = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereWorkloadClusterVersion']
                if not cluster_version.startswith('v'):
                    cluster_version = 'v' + cluster_version
                if not cluster_version.startswith("v1.18.19+vmware.1"):
                    logger.warn(
                        "On vSphere with Tanzu platform, TSM supports the Kubernetes version 1.18.19+vmware.1")
                    logger.warn("For latest updates please check - "
                                            "https://docs.vmware.com/en/VMware-Tanzu-Service-Mesh/services/tanzu-service-mesh-environment-requirements-and-supported-platforms/GUID-D0B939BE-474E-4075-9A65-3D72B5B9F237.html")
                tsm = registerTSM(workload_cluster_name, self.jsonspec, size)
                if tsm[1] != 200:
                    logger.error("TSM registration failed for workload cluster")
                    d = {
                        "responseType": "SUCCESS",
                        "msg": "TSM registration failed for workload cluster",
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
            else:
                logger.info("TSM not enabled")

            if checkDataProtectionEnabled(self.jsonspec, "workload", self.isEnvTkgs_ns):
                supervisor_cluster = self.jsonspec['envSpec']["saasEndpoints"]['tmcDetails'][
                    'tmcSupervisorClusterName']
                is_enabled = enable_data_protection(self.jsonspec, workload_cluster_name, supervisor_cluster,
                                                    self.isEnvTkgs_ns)
                if not is_enabled[0]:
                    logger.error(is_enabled[1])
                    d = {
                        "responseType": "ERROR",
                        "msg": is_enabled[1],
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                logger.info(is_enabled[1])
            else:
                logger.info("Data Protection is not enabled for cluster " + workload_cluster_name)
        else:
            logger.info("TMC not enabled.")

        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully created workload cluster",
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200

    def create_name_space(self):
        vcenter_ip = self.vcenter_dict["vcenter_ip"]
        vcenter_username = self.vcenter_dict["vcenter_username"]
        password = self.vcenter_dict["vcenter_password"]

        name_space = self.createNameSpace(vcenter_ip, vcenter_username, password)
        if name_space[0] is None:
            logger.error("Failed to create name space " + str(name_space[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create name space " + str(name_space[1]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        logger.info("Successfully created name space")
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully created name space",
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200

    def createTkgWorkloadCluster(self, vc_ip, vc_user, vc_password):
        try:
            url_ = "https://" + vc_ip + "/"
            sess = requests.post(url_ + "rest/com/vmware/cis/session", auth=(vc_user, vc_password), verify=False)
            if sess.status_code != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to fetch session ID for vCenter - " + vc_ip,
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            else:
                session_id = sess.json()['value']

            header = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "vmware-api-session-id": session_id
            }
            cluster_name = self.jsonspec["envSpec"]["vcenterDetails"]["vcenterCluster"]
            id = getClusterID(vc_ip, vc_user, vc_password, cluster_name, self.jsonspec)
            if id[1] != 200:
                return None, id[0]
            clusterip_resp = requests.get(url_ + "api/vcenter/namespace-management/clusters/" + str(id[0]),
                                          verify=False,
                                          headers=header)
            if clusterip_resp.status_code != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to fetch API server cluster endpoint - " + vc_ip,
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500

            cluster_endpoint = clusterip_resp.json()["api_server_cluster_endpoint"]

            configure_kubectl = configureKubectl(cluster_endpoint)
            if configure_kubectl[1] != 200:
                return configure_kubectl[0], 500
            supervisorTMC(vc_user, vc_password, cluster_endpoint)
            logger.info("Switch context to name space")
            name_space = \
                self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereNamespaceName']

            workload_name = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereWorkloadClusterName']
            if not createClusterFolder(workload_name):
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create directory: " + Paths.CLUSTER_PATH + workload_name,
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            logger.info(
                "The config files for shared services cluster will be located at: " + Paths.CLUSTER_PATH + workload_name)
            logger.info(
                "Before deploying cluster, checking if namespace is in running status..." + name_space)
            wcp_status = self.checkClusterStatus(vc_ip, header, name_space, id[0])
            if wcp_status[0] is None:
                return None, wcp_status[1]

            switch = ["kubectl", "config", "use-context", name_space]
            switch_context = runShellCommandAndReturnOutputAsList(switch)
            if switch_context[1] != 0:
                return None, "Failed to switch  to context " + str(switch_context[0]), 500
            command = ["kubectl", "get", "tanzukubernetescluster"]
            cluster_list = runShellCommandAndReturnOutputAsList(command)
            if cluster_list[1] != 0:
                return None, "Failed to get list of cluster " + str(cluster_list[0]), 500
            if str(cluster_list[0]).__contains__(workload_name):
                logger.info("Cluster with same name already exist - " + workload_name)
                return "Cluster with same name already exist ", 200
            if checkTmcEnabled(self.jsonspec):
                supervisor_cluster = self.jsonspec['envSpec']["saasEndpoints"]['tmcDetails'][
                    'tmcSupervisorClusterName']
                logger.info("Creating workload cluster...")
                name_space = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereWorkloadClusterSpec'][
                    'tkgsVsphereNamespaceName']
                version = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereWorkloadClusterVersion']

                # if user using json and v not appended to version
                if not version.startswith('v'):
                    version = 'v' + version
                is_compatible = checkClusterVersionCompatibility(vc_ip, vc_user, vc_password, cluster_name, version,
                                                                 self.jsonspec)
                if is_compatible[0]:
                    logger.info("Provided cluster version is valid !")
                else:
                    return None, is_compatible[1]
                pod_cidr = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereWorkloadClusterSpec'][
                    'podCidrBlocks']
                service_cidr = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereWorkloadClusterSpec']['serviceCidrBlocks']
                node_storage_class_input = \
                    self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                        'tkgsVsphereWorkloadClusterSpec']['nodeStorageClass']
                policy_id = getPolicyID(node_storage_class_input, vc_ip, vc_user, vc_password)
                if policy_id[0] is None:
                    return None, "Failed to get policy id"
                allowed_ = get_alias_name(policy_id[0])
                if allowed_[0] is None:
                    logger.error(allowed_[1])
                    return None, "Failed to get Alias name"
                node_storage_class = allowed_[0]
                allowed_storage = \
                    self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                        'tkgsVsphereWorkloadClusterSpec']['allowedStorageClasses']
                allowed = ""
                classes = allowed_storage
                for c in classes:
                    policy_id = getPolicyID(c, vc_ip, vc_user, vc_password)
                    if policy_id[0] is None:
                        return None, "Failed to get policy id"
                    allowed_ = get_alias_name(policy_id[0])
                    if allowed_[0] is None:
                        logger.error(allowed_[1])
                        return None, "Failed to alias name"
                    allowed += str(allowed_[0]) + ","
                if not allowed:
                    logger.error("Failed to get allowed classes")
                    return None, "Failed to get allowed classes"
                allowed = allowed.strip(",")
                default_storage_class = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereWorkloadClusterSpec']['defaultStorageClass']
                policy_id = getPolicyID(default_storage_class, vc_ip, vc_user, vc_password)
                if policy_id[0] is None:
                    return None, "Failed to get policy id"
                default = get_alias_name(policy_id[0])
                if default[0] is None:
                    logger.error(default[1])
                    return None, "Failed to get Alias name"
                default_class = default[0]
                worker_node_count = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereWorkloadClusterSpec']['workerNodeCount']
                enable_ha = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereWorkloadClusterSpec']['enableControlPlaneHa']
                clusterGroup = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereWorkloadClusterSpec']["tkgsWorkloadClusterGroupName"]
                worker_vm_class = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereWorkloadClusterSpec']['workerVmClass']
                if not clusterGroup:
                    clusterGroup = "default"

                if str(enable_ha).lower() == "true":
                    workload_cluster_create_command = ["tmc", "cluster", "create", "--template", "tkgs", "-m",
                                                       supervisor_cluster, "-p", name_space, "--cluster-group",
                                                       clusterGroup,
                                                       "--name", workload_name, "--version",
                                                       version, "--pods-cidr-blocks", pod_cidr, "--service-cidr-blocks",
                                                       service_cidr, "--storage-class", node_storage_class,
                                                       "--allowed-storage-classes", allowed,
                                                       "--default-storage-class", default_class,
                                                       "--worker-instance-type", worker_vm_class, "--instance-type",
                                                       worker_vm_class, "--worker-node-count", worker_node_count,
                                                       "--high-availability"]
                else:
                    workload_cluster_create_command = ["tmc", "cluster", "create", "--template", "tkgs", "-m",
                                                       supervisor_cluster, "-p", name_space, "--cluster-group",
                                                       clusterGroup,
                                                       "--name", workload_name, "--version",
                                                       version, "--pods-cidr-blocks", pod_cidr, "--service-cidr-blocks",
                                                       service_cidr, "--storage-class", node_storage_class,
                                                       "--allowed-storage-classes", allowed,
                                                       "--default-storage-class", default_class,
                                                       "--worker-instance-type", worker_vm_class, "--instance-type",
                                                       worker_vm_class, "--worker-node-count", worker_node_count]
                try:
                    control_plane_volumes = \
                    self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                        'tkgsVsphereWorkloadClusterSpec']['controlPlaneVolumes']
                    control_plane_volumes_list = []
                    for control_plane_volume in control_plane_volumes:
                        if control_plane_volume['storageClass']:
                            storageClass = control_plane_volume['storageClass']
                        else:
                            storageClass = default_class
                        control_plane_volumes_list.append(
                            dict(name=control_plane_volume['name'], mountPath=control_plane_volume['mountPath'],
                                 capacity=dict(storage=control_plane_volume['storage']), storageClass=storageClass))
                    control_plane_vol = True
                except Exception as e:
                    control_plane_vol = False
                try:
                    worker_volumes = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                        'tkgsVsphereWorkloadClusterSpec']['workerVolumes']
                    worker_vol = True
                    worker_volumes_list = []
                    for worker_volume in worker_volumes:
                        if worker_volume['storageClass']:
                            storageClass = worker_volume['storageClass']
                        else:
                            storageClass = default_class
                        worker_volumes_list.append(
                            dict(name=worker_volume['name'], mountPath=worker_volume['mountPath'],
                                 capacity=dict(storage=worker_volume['storage']),
                                 storageClass=storageClass))
                except Exception as e:
                    worker_vol = False
                if control_plane_vol and worker_vol:
                    workload_cluster_create_command.append("--control-plane-volumes")
                    control_plane_command = ""
                    for control_plane_volumes in control_plane_volumes_list:
                        control_plane_command += control_plane_volumes["name"] + ":[" + control_plane_volumes[
                            "mountPath"] + " " + str(control_plane_volumes['capacity']["storage"]).lower().strip(
                            "gi") + " " + control_plane_volumes['storageClass'] + "],"
                    workload_cluster_create_command.append("\"" + control_plane_command.strip(",") + "\"")
                    workload_cluster_create_command.append("--nodepool-volumes")
                    worker_command = ""
                    for worker_volumes in worker_volumes_list:
                        worker_command += worker_volumes["name"] + ":[" + worker_volumes["mountPath"] + " " + \
                                          str(worker_volumes['capacity']["storage"]).lower().strip("gi") + " " + \
                                          worker_volumes['storageClass'] + "]"
                    workload_cluster_create_command.append("\"" + worker_command.strip(",") + "\"")
                elif control_plane_vol:
                    workload_cluster_create_command.append("--control-plane-volumes")
                    control_plane_command = ""
                    for control_plane_volumes in control_plane_volumes_list:
                        control_plane_command += control_plane_volumes["name"] + ":[" + control_plane_volumes[
                            "mountPath"] + " " + str(control_plane_volumes['capacity']["storage"]).lower().strip(
                            "gi") + " " + control_plane_volumes['storageClass'] + "],"
                    workload_cluster_create_command.append("\"" + control_plane_command.strip(",") + "\"")
                elif worker_vol:
                    workload_cluster_create_command.append("--nodepool-volumes")
                    worker_command = ""
                    for worker_volumes in worker_volumes_list:
                        worker_command += worker_volumes["name"] + ":[" + worker_volumes["mountPath"] + " " + \
                                          str(worker_volumes['capacity']["storage"]).lower().strip("gi") + " " + \
                                          worker_volumes['storageClass'] + "]"
                    workload_cluster_create_command.append("\"" + worker_command.strip(",") + "\"")
                logger.info(workload_cluster_create_command)
                worload = runShellCommandAndReturnOutputAsList(workload_cluster_create_command)
                if worload[1] != 0:
                    return None, "Failed to create  workload cluster " + str(worload[0])
                logger.info("Waiting for 2 min for checking status == ready")
                time.sleep(120)
                command_monitor = ["tmc", "cluster", "get", workload_name, "-m", supervisor_cluster, "-p", name_space]
                count = 0
                found = False
                while count < 135:
                    o = runShellCommandAndReturnOutput(command_monitor)
                    if o[1] == 0:
                        l = yaml.safe_load(o[0])
                        try:
                            phase = str(l["status"]["phase"])
                            wcm = str(l["status"]["conditions"]["WCM-Ready"]["status"])
                            health = str(l["status"]["health"])
                            if phase == "READY" and wcm == "TRUE" and health == "HEALTHY":
                                found = True
                                logger.info(
                                    "Phase status " + phase + " wcm status " + wcm + " Health status " + health)
                                break
                            logger.info(
                                "Phase status " + phase + " wcm status " + wcm + " Health status " + health)
                        except:
                            pass
                    time.sleep(20)
                    logger.info("Waited for " + str(count * 20) + "s, retrying")
                    count = count + 1
                if not found:
                    return None, "Cluster not in ready state"
                return "SUCCESS", 200
            else:
                try:
                    gen = self.generateYamlFile(vc_ip, vc_user, vc_password, workload_name)
                    if gen is None:
                        return None, "Failed"
                except Exception as e:
                    return None, "Failed to generate yaml file " + str(e)

                command = ["kubectl", "apply", "-f", gen]
                worload = runShellCommandAndReturnOutputAsList(command)
                if worload[1] != 0:
                    return None, "Failed to create workload " + str(worload[0])
                logger.info(worload[0])
                name_space = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereNamespaceName']
                workload_name = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereWorkloadClusterName']
                logger.info("Waiting for cluster creation to be initiated...")
                time.sleep(60)
                command = ["kubectl", "get", "tkc", "-n", name_space]
                count = 0
                found = False
                while count < 90:
                    worload = runShellCommandAndReturnOutputAsList(command)
                    if worload[1] != 0:
                        return None, "Failed to monitor workload " + str(worload[0])

                    index = None
                    for item in range(len(worload[0])):
                        if worload[0][item].split()[0] == workload_name:
                            index = item
                            break

                    if index is None:
                        return None, "Unable to find cluster..."

                    output = worload[0][index].split()
                    if not ((output[5] == "True" or output[5] == "running") and output[6] == "True"):
                        logger.info("Waited for " + str(count * 30) + "s, retrying")
                        count = count + 1
                        time.sleep(30)
                    else:
                        found = True
                        break
                if not found:
                    logger.error("Cluster is not up and running on waiting " + str(count * 30) + "s")
                    return None, "Failed"
                return "SUCCESS", "DEPLOYED"
        except Exception as e:
            return None, "Failed to create tkg workload cluster  " + str(e)

    def createNameSpace(self, vcenter_ip, vcenter_username, password):
        try:
            sess = requests.post("https://" + str(vcenter_ip) + "/rest/com/vmware/cis/session",
                                 auth=(vcenter_username, password),
                                 verify=False)
            if sess.status_code != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to fetch session ID for vCenter - " + vcenter_ip,
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            else:
                vc_session = sess.json()['value']

            header = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "vmware-api-session-id": vc_session
            }
            name_space = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereNamespaceName']
            url = "https://" + str(vcenter_ip) + "/api/vcenter/namespaces/instances"
            cluster_name = self.jsonspec["envSpec"]["vcenterDetails"]["vcenterCluster"]
            id = getClusterID(vcenter_ip, vcenter_username, password, cluster_name, self.jsonspec)
            if id[1] != 200:
                return None, id[0]
            status = checkNameSpaceRunningStatus(url, header, name_space, id[0])
            if status[0] is None:
                if status[1] == "NOT_FOUND":
                    pass
                elif status[1] == "NOT_FOUND_INITIAL":
                    pass
                elif status[1] == "NOT_RUNNING":
                    return None, "Name is already created but not in running state"
            if status[0] == "SUCCESS":
                return "SUCCESS", name_space + " already created"
            try:
                cpu_limit = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereNamespaceResourceSpec']['cpuLimit']
            except Exception as e:
                cpu_limit = ""
                logger.info("CPU Limit is not provided, will continue without setting Custom CPU Limit")
            try:
                memory_limit = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereNamespaceResourceSpec']['memoryLimit']
            except Exception as e:
                memory_limit = ""
                logger.info(
                    "Memory Limit is not provided, will continue without setting Custom Memory Limit")
            try:
                storage_limit = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereNamespaceResourceSpec']['storageRequestLimit']
            except Exception as e:
                storage_limit = ""
                logger.info("Storage Request Limit is not provided, will continue without setting Custom "
                                        "Storage Request Limit")
            content_library = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereNamespaceContentLibrary']
            resource_spec = getBodyResourceSpec(cpu_limit, memory_limit, storage_limit)
            if not content_library:
                content_library = ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY
            lib = getLibraryId(vcenter_ip, vcenter_username, password, content_library)
            if lib is None:
                return None, "Failed to get content library id " + content_library
            name_space_vm_classes = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereNamespaceVmClasses']
            storage_specs = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereNamespaceStorageSpec']
            list_storage = []
            for storage_spec in storage_specs:
                policy = storage_spec["storagePolicy"]
                policy_id = getPolicyID(policy, vcenter_ip, vcenter_username, password)
                if policy_id[0] is None:
                    logger.error("Failed to get policy id")
                    return None, policy_id[1]
                if "storageLimit" in storage_spec:
                    if not storage_spec["storageLimit"]:
                        list_storage.append(dict(policy=policy_id[0]))
                    else:
                        list_storage.append(dict(limit=storage_spec["storageLimit"], policy=policy_id[0]))
                else:
                    list_storage.append(dict(policy=policy_id[0]))
            workload_network = self.jsonspec['tkgsComponentSpec']['tkgsWorkloadNetwork'][
                'tkgsWorkloadNetworkName']
            network_status = self.checkWorkloadNetwork(vcenter_ip, vcenter_username, password, id[0], workload_network)
            if network_status[1] and network_status[0] == "SUCCESS":
                logger.info("Workload network is already created - " + workload_network)
                logger.info("Using " + workload_network + " network for creating namespace " + name_space)
            elif network_status[0] == "NOT_CREATED":
                create_status = self.create_workload_network(vcenter_ip, vcenter_username, password, id[0], workload_network)
                if create_status[0] == "SUCCESS":
                    logger.info("Workload network created successfully - " + workload_network)
                else:
                    logger.error("Failed to created workload network - " + workload_network)
                    return None, create_status[1]
            else:
                return None, network_status[0]

            body = {
                "cluster": id[0],
                "description": "name space",
                "namespace": name_space,
                "networks": [workload_network],
                "resource_spec": resource_spec,
                "storage_specs": list_storage,
                "vm_service_spec": {
                    "content_libraries": [lib],
                    "vm_classes": name_space_vm_classes
                }
            }
            json_object = json.dumps(body, indent=4)
            url = "https://" + str(vcenter_ip) + "/api/vcenter/namespaces/instances"
            response_csrf = requests.request("POST", url, headers=header, data=json_object, verify=False)
            if response_csrf.status_code != 204:
                return None, "Failed to create name-space " + response_csrf.text
            count = 0
            while count < 30:
                status = checkNameSpaceRunningStatus(url, header, name_space, id[0])
                if status[0] == "SUCCESS":
                    break
                logger.info("Waited for " + str(count * 10) + "s, retrying")
                count = count + 1
                time.sleep(10)
            return "SUCCESS", "CREATED"
        except Exception as e:
            return None, str(e)

    def checkWorkloadNetwork(self, vcenter_ip, vc_user, password, cluster_id, workload_network):
        sess = requests.post("https://" + str(vcenter_ip) + "/rest/com/vmware/cis/session",
                             auth=(vc_user, password), verify=False)
        if sess.status_code != 200:
            logger.error("Connection to vCenter failed")
            return "Connection to vCenter failed", False
        else:
            vc_session = sess.json()['value']
        header = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "vmware-api-session-id": vc_session
        }

        url = "https://" + vcenter_ip + "/api/vcenter/namespace-management/clusters/" + cluster_id + "/networks"
        response_networks = requests.request("GET", url, headers=header, verify=False)
        if response_networks.status_code != 200:
            return "Failed to fetch workload networks for given cluster", False

        for network in response_networks.json():
            if network["network"] == workload_network:
                return "SUCCESS", True
        else:
            return "NOT_CREATED", False

    def create_workload_network(self, vCenter, vc_user, password, cluster_id, network_name):
        worker_cidr = self.jsonspec['tkgsComponentSpec']['tkgsWorkloadNetwork'][
            'tkgsWorkloadNetworkGatewayCidr']
        start = self.jsonspec['tkgsComponentSpec']['tkgsWorkloadNetwork'][
            'tkgsWorkloadNetworkStartRange']
        end = self.jsonspec['tkgsComponentSpec']['tkgsWorkloadNetwork']['tkgsWorkloadNetworkEndRange']
        port_group_name = self.jsonspec['tkgsComponentSpec']['tkgsWorkloadNetwork'][
            'tkgsWorkloadPortgroupName']
        datacenter = self.jsonspec['envSpec']['vcenterDetails']['vcenterDatacenter']

        if not (worker_cidr or start or end or port_group_name):
            return None, "Details to create workload network are not provided - " + network_name
        ip_cidr = seperateNetmaskAndIp(worker_cidr)
        count_of_ip = getCountOfIpAdress(worker_cidr, start, end)
        worker_network_id = getDvPortGroupId(vCenter, vc_user, password, port_group_name, datacenter)

        sess = requests.post("https://" + str(vCenter) + "/rest/com/vmware/cis/session",
                             auth=(vc_user, password), verify=False)
        if sess.status_code != 200:
            logger.error("Connection to vCenter failed")
            return None, "Connection to vCenter failed"
        else:
            vc_session = sess.json()['value']

        header = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "vmware-api-session-id": vc_session
        }

        body = {
            "network": network_name,
            "network_provider": "VSPHERE_NETWORK",
            "vsphere_network": {
                "address_ranges": [{
                    "address": start,
                    "count": count_of_ip
                }],
                "gateway": ip_cidr[0],
                "ip_assignment_mode": "STATICRANGE",
                "portgroup": worker_network_id,
                "subnet_mask": cidr_to_netmask(worker_cidr)
            }
        }

        json_object = json.dumps(body, indent=4)
        url1 = "https://" + vCenter + "/api/vcenter/namespace-management/clusters/" + cluster_id + "/networks"
        create_response = requests.request("POST", url1, headers=header, data=json_object, verify=False)
        if create_response.status_code == 204:
            return "SUCCESS", "Workload network created successfully"
        else:
            return None, create_response.txt

    def checkClusterStatus(self, vc_ip, header, name_space, cluster_id):
        try:
            url = "https://" + str(vc_ip) + "/api/vcenter/namespaces/instances"
            namespace_status = checkNameSpaceRunningStatus(url, header, name_space, cluster_id)
            running = False
            if namespace_status[0] != "SUCCESS":
                logger.info("Namespace is not in running status... retrying")
            else:
                running = True

            count = 0
            while count < 60 and not running:
                namespace_status = checkNameSpaceRunningStatus(url, header, name_space, cluster_id)
                if namespace_status[0] == "SUCCESS":
                    running = True
                    break
                count = count + 1
                time.sleep(5)
                logger.info("Waited for " + str(count * 1) + "s ...retrying")

            if not running:
                return None, "Namespace is not in running status - " + name_space + ". Waited for " + str(
                    count * 5) + "seconds"

            logger.info("Checking Cluster WCP status...")
            url1 = "https://" + vc_ip + "/api/vcenter/namespace-management/clusters/" + str(cluster_id)
            count = 0
            found = False
            while count < 60 and not found:
                response_csrf = requests.request("GET", url1, headers=header, verify=False)
                try:
                    if response_csrf.json()["config_status"] == "RUNNING":
                        found = True
                        break
                    else:
                        if response_csrf.json()["config_status"] == "ERROR":
                            return None, "WCP status in ERROR"
                    logger.info("Cluster config status " + response_csrf.json()["config_status"])
                except:
                    pass
                time.sleep(20)
                count = count + 1
                logger.info("Waited " + str(count * 20) + "s, retrying")
            if not found:
                logger.error("Cluster is not running on waiting " + str(count * 20))
                return None, "Failed"
            else:
                logger.info("WCP config status " + response_csrf.json()["config_status"])

            return "SUCCESS", "WCP and Namespace configuration check pass"
        except Exception as e:
            logger.error(str(e))
            return None, "Exception occurred while checking cluster config status"

    def generateYamlFile(self, vc_ip, vc_user, vc_password, workload_name):
        workload_name = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereWorkloadClusterName']
        file = Paths.CLUSTER_PATH + workload_name + "/tkgs_workload.yaml"
        command = ["rm", "-rf", file]
        runShellCommandAndReturnOutputAsList(command)
        name_space = \
            self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereNamespaceName']
        enable_ha = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['enableControlPlaneHa']
        if str(enable_ha).lower() == "true":
            count = "3"
        else:
            count = "1"
        control_plane_vm_class = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['controlPlaneVmClass']
        node_storage_class = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['nodeStorageClass']
        policy_id = getPolicyID(node_storage_class, vc_ip, vc_user, vc_password)
        if policy_id[0] is None:
            logger.error("Failed to get policy id")
            return None
        allowed_ = get_alias_name(policy_id[0])
        if allowed_[0] is None:
            logger.error(allowed_[1])
            return None
        node_storage_class = str(allowed_[0])
        worker_node_count = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['workerNodeCount']
        worker_vm_class = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['workerVmClass']
        cluster_name = self.jsonspec["envSpec"]["vcenterDetails"]["vcenterCluster"]
        kube_version = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereWorkloadClusterVersion']
        if not kube_version.startswith('v'):
            kube_version = 'v' + kube_version
        is_compatible = checkClusterVersionCompatibility(vc_ip, vc_user, vc_password, cluster_name, kube_version,
                                                         self.jsonspec)
        if is_compatible[0]:
            logger.info("Provided cluster version is valid !")
        else:
            return None
        service_cidr = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['serviceCidrBlocks']
        pod_cidr = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['podCidrBlocks']
        allowed_clases = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['allowedStorageClasses']
        allowed = ""
        classes = allowed_clases
        for c in classes:
            policy_id = getPolicyID(c, vc_ip, vc_user, vc_password)
            if policy_id[0] is None:
                logger.error("Failed to get policy id")
                return None
            allowed_ = get_alias_name(policy_id[0])
            if allowed_[0] is None:
                logger.error(allowed_[1])
                return None
            allowed += str(allowed_[0]) + ","
        if allowed is None:
            logger.error("Failed to get allowed classes")
            return None
        allowed = allowed.strip(",")
        li = convertStringToCommaSeperated(allowed)
        default_clases = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['defaultStorageClass']
        policy_id = getPolicyID(default_clases, vc_ip, vc_user, vc_password)
        if policy_id[0] is None:
            logger.error("Failed to get policy id")
            return None
        allowed_ = get_alias_name(policy_id[0])
        if allowed_[0] is None:
            logger.error(allowed_[1])
            return None
        default_clases = str(allowed_[0])
        try:
            control_plane_volumes = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']['controlPlaneVolumes']
            control_plane_volumes_list = []
            for control_plane_volume in control_plane_volumes:
                control_plane_volumes_list.append(
                    dict(name=control_plane_volume['name'], mountPath=control_plane_volume['mountPath'],
                         capacity=dict(storage=control_plane_volume['storage'])))
            control_plane_vol = True
        except Exception as e:
            control_plane_vol = False
        try:
            worker_volumes = self.jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']['workerVolumes']
            worker_vol = True
            worker_volumes_list = []
            for worker_volume in worker_volumes:
                worker_volumes_list.append(dict(name=worker_volume['name'], mountPath=worker_volume['mountPath'],
                                                capacity=dict(storage=worker_volume['storage'])))
        except Exception as e:
            worker_vol = False

        if worker_vol and control_plane_vol:
            topology_dict = {
                "controlPlane": {
                    "count": int(count),
                    "class": control_plane_vm_class,
                    "storageClass": node_storage_class,
                    "volumes": control_plane_volumes_list
                },
                "workers": {
                    "count": int(worker_node_count),
                    "class": worker_vm_class,
                    "storageClass": node_storage_class,
                    "volumes": worker_volumes_list
                }
            }
        elif control_plane_vol:
            topology_dict = {
                "controlPlane": {
                    "count": int(count),
                    "class": control_plane_vm_class,
                    "storageClass": node_storage_class,
                    "volumes": control_plane_volumes_list
                },
                "workers": {
                    "count": int(worker_node_count),
                    "class": worker_vm_class,
                    "storageClass": node_storage_class
                }
            }
        elif worker_vol:
            topology_dict = {
                "controlPlane": {
                    "count": int(count),
                    "class": control_plane_vm_class,
                    "storageClass": node_storage_class
                },
                "workers": {
                    "count": int(worker_node_count),
                    "class": worker_vm_class,
                    "storageClass": node_storage_class,
                    "volumes": worker_volumes_list
                }
            }
        else:
            topology_dict = {
                "controlPlane": {
                    "count": int(count),
                    "class": control_plane_vm_class,
                    "storageClass": node_storage_class
                },
                "workers": {
                    "count": int(worker_node_count),
                    "class": worker_vm_class,
                    "storageClass": node_storage_class
                }
            }
        meta_dict = {
            "name": workload_name,
            "namespace": name_space
        }
        spec_dict = {
            "topology": topology_dict,
            "distribution": {
                "version": kube_version
            },
            "settings": {
                "network": {
                    "services": {
                        "cidrBlocks": [service_cidr]
                    },
                    "pods": {
                        "cidrBlocks": [pod_cidr]
                    }
                },
                "storage": {
                    "classes": li,
                    "defaultClass": default_clases
                }
            }
        }
        ytr = dict(apiVersion='run.tanzu.vmware.com/v1alpha1', kind='TanzuKubernetesCluster', metadata=meta_dict,
                   spec=spec_dict)
        with open(file, 'w') as outfile:
            # formatted = ytr % (
            # workload_name, name_space, count, control_plane_vm_class, node_storage_class, worker_node_count,
            # worker_vm_class, node_storage_class, kube_version, service_cidr, pod_cidr, li, default_clases)
            # data1 = ryaml.load(formatted, Loader=ryaml.RoundTripLoader)
            ryaml.dump(ytr, outfile, Dumper=ryaml.RoundTripDumper, indent=2)
        return file
