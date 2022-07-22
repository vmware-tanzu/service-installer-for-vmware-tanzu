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
    Sizing, ClusterType, Repo
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
    installCertManagerAndContour, runSsh, checkenv
from util.avi_api_helper import isAviHaEnabled, obtain_second_csrf
from workflows.ra_mgmt_cluster_workflow import RaMgmtClusterWorkflow
from util.ShellHelper import grabKubectlCommand, runShellCommandAndReturnOutputAsList, \
    grabPipeOutput
import ruamel
import requests
from model.vsphereSpec import VsphereMasterSpec


logger = LoggerHelper.get_logger(Path(__file__).stem)


class RaWorkloadClusterWorkflow:
    def __init__(self, run_config: RunConfig):
        self.run_config = run_config
        self.extensions_root = TKG_EXTENSIONS_ROOT[self.run_config.desired_state.version.tkg]
        self.extensions_dir = Paths.TKG_EXTENSIONS_DIR.format(extensions_root=self.extensions_root)
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
        jsonpath = os.path.join(self.run_config.root_dir, Paths.MASTER_SPEC_PATH)
        with open(jsonpath) as f:
            self.jsonspec = json.load(f)
        self.rcmd = RunCmd()
        self.clusterops = RaMgmtClusterWorkflow(self.run_config)

        check_env_output = checkenv(self.jsonspec)
        if check_env_output is None:
            msg = "Failed to connect to VC. Possible connection to VC is not available or " \
                  "incorrect spec provided."
            raise Exception(msg)

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

    def networkConfig(self):

        aviVersion = ControllerLocation.VSPHERE_AVI_VERSION
        vcpass_base64 = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']
        password = CmdHelper.decode_base64(vcpass_base64)
        vcenter_username = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser']
        vcenter_ip = self.jsonspec['envSpec']['vcenterDetails']['vcenterAddress']
        cluster_name = self.jsonspec['envSpec']['vcenterDetails']['vcenterCluster']
        data_center = self.jsonspec['envSpec']['vcenterDetails']['vcenterDatacenter']
        data_store = self.jsonspec['envSpec']['vcenterDetails']['vcenterDatastore']
        refToken = self.jsonspec['envSpec']['marketplaceSpec']['refreshToken']
        kubernetes_ova_os = self.jsonspec["tkgWorkloadComponents"]["tkgWorkloadBaseOs"]
        kubernetes_ova_version = self.jsonspec["tkgWorkloadComponents"]["tkgWorkloadKubeVersion"]
        if refToken:
            logger.info("Kubernetes OVA configs for workload cluster")
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
        aviVersion = ControllerLocation.VSPHERE_AVI_VERSION
        vcpass_base64 = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']
        password = CmdHelper.decode_base64(vcpass_base64)
        vcenter_username = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser']
        vcenter_ip = self.jsonspec['envSpec']['vcenterDetails']['vcenterAddress']
        cluster_name = self.jsonspec['envSpec']['vcenterDetails']['vcenterCluster']
        data_center = self.jsonspec['envSpec']['vcenterDetails']['vcenterDatacenter']
        data_store = self.jsonspec['envSpec']['vcenterDetails']['vcenterDatastore']
        parent_resourcepool = self.jsonspec['envSpec']['vcenterDetails']['resourcePoolName']
        refToken = self.jsonspec['envSpec']['marketplaceSpec']['refreshToken']
        kubernetes_ova_os = self.jsonspec["tkgWorkloadComponents"]["tkgWorkloadBaseOs"]
        kubernetes_ova_version = self.jsonspec["tkgWorkloadComponents"]["tkgWorkloadKubeVersion"]

        avi_fqdn = self.jsonspec['tkgComponentSpec']['aviComponents']['aviController01Fqdn']
        ha_field = self.jsonspec['tkgComponentSpec']['aviComponents']['enableAviHa']
        ssh_key = runSsh(vcenter_username)
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
            raise Exception
        avienc_pass = self.jsonspec['tkgComponentSpec']['aviComponents']['aviPasswordBase64']
        csrf2 = obtain_second_csrf(ip, avienc_pass)
        if csrf2 is None:
            logger.error("Failed to get csrf from new set password")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get csrf from new set password",
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
            with open('/root/.ssh/id_rsa.pub', 'r') as f:
                re = f.readline()
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
        to_enable = self.jsonspec["envSpec"]["saasEndpoints"]["tanzuObservabilityDetails"][
            "tanzuObservabilityAvailability"]
        size = str(self.jsonspec['tkgWorkloadComponents']['tkgWorkloadSize'])
        to = registerTanzuObservability(workload_cluster_name, to_enable, size, self.jsonspec)
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

    @log("Updating Grafana Admin password")
    def _update_grafana_admin_password(self, grafana_pas):
        remote_file = Paths.REMOTE_GRAFANA_DATA_VALUES
        local_file = Paths.LOCAL_GRAFANA_DATA_VALUES.format(root_dir=self.run_config.root_dir)
        logger.info(f"Fetching and saving data values yml to {local_file}")
        self.runcmd.local_file_copy(remote_file, local_file)
        encoded_password = CmdHelper.encode_base64(grafana_pas)
        logger.info(f"Updating admin password in local copy of grafana-data-values.yaml")
        # Replacing string with pattern matching instead of loading yaml because comments
        # in yaml file will be lost during boxing/unboxing of yaml data
        FileHelper.replace_pattern(
            src=local_file,
            target=local_file,
            pattern_replacement_list=[(Constants.GRAFANA_ADMIN_PASSWORD_TOKEN,
                                       Constants.GRAFANA_ADMIN_PASSWORD_VALUE.format(password=encoded_password))],
        )

        self.runcmd.local_file_copy (local_file, remote_file)

    @log("Updating namespace in grafana-data-values.yaml")
    def _update_grafana_namespace(self, remote_file):
        local_file = Paths.LOCAL_GRAFANA_DATA_VALUES.format(root_dir=self.run_config.root_dir)

        logger.info(f"Fetching and saving data values yml to {local_file}")
        self.runcmd.local_file_copy(remote_file, local_file)

        new_namespace = "tanzu-system-dashboards"
        FileHelper.replace_pattern(
            src=local_file,
            target=local_file,
            pattern_replacement_list=[(Constants.GRAFANA_DATA_VALUES_NAMESPACE,
                                       Constants.GRAFANA_DATA_VALUES_NEW_NAMESPACE.format(
                                           namespace=new_namespace))],
        )
        self.runcmd.local_file_copy(local_file, remote_file)

    def _install_grafana(self, clustername):
        version = self.common_workflow.get_available_package_version(
            cluster_name=clustername,
            package=Constants.GRAFANA_PACKAGE,
            name=Constants.GRAFANA_APP)

        logger.info("Generating Grafana configuration template")
        self.common_workflow.generate_spec_template(name=Constants.GRAFANA_APP,
                                                    package=Constants.GRAFANA_PACKAGE,
                                                    version=version,
                                                    template_path=Paths.REMOTE_GRAFANA_DATA_VALUES,
                                                    on_docker=False)

        logger.info("Updating Grafana admin password")
        grafana_pass = self.jsonspec['tanzuExtensions']['monitoring']['grafanaPasswordBase64']
        self._update_grafana_admin_password(grafana_pas=grafana_pass)
        logger.info("Creating namespace for grafana")
        self.kubectl_client.set_cluster_context(cluster_name=clustername)

        logger.info("Updating namespace in grafana config file")
        self._update_grafana_namespace(remote_file=Paths.REMOTE_GRAFANA_DATA_VALUES)

        logger.info("Removing comments from grafana-data-values.yaml")
        self.runcmd.run_cmd_only(
            f"yq -i eval '... comments=\"\"' {Paths.REMOTE_GRAFANA_DATA_VALUES}")
        # self.ssh.run_cmd(f"yq -i eval '... comments=\"\"' {Paths.REMOTE_GRAFANA_DATA_VALUES}")
        namespace = clustername + 'grafana_extensions'
        self.common_workflow.install_package(cluster_name=self.cluster_to_deploy,
                                             package=Constants.GRAFANA_PACKAGE,
                                             namespace=namespace,
                                             name=Constants.GRAFANA_APP, version=version,
                                             values=Paths.REMOTE_GRAFANA_DATA_VALUES)

        logger.debug(self.kubectl_client.get_all_pods())
        logger.info('Grafana installation complete')

    @log("Installing prometheus package")
    def _install_prometheus(self, clustername):
        version = self.common_workflow.get_available_package_version(cluster_name=clustername,
                                                                package=Constants.PROMETHEUS_PACKAGE,
                                                                name=Constants.PROMETHEUS_APP)

        logger.info("Generating prometheus configuration template")
        self.common_workflow.generate_spec_template(name=Constants.PROMETHEUS_APP,
                                                    package=Constants.PROMETHEUS_PACKAGE,
                                                    version=version,
                                                    template_path=Paths.REMOTE_PROMETHEUS_DATA_VALUES,
                                                    on_docker=False)

        logger.info("Removing comments from prometheus-data-values.yml")
        self.runcmd.run_cmd_only(f"yq -i eval '... comments=\"\"' {Paths.REMOTE_PROMETHEUS_DATA_VALUES}")
        namespace = 'prometheus_{}'.format(clustername)
        self.common_workflow.install_package(cluster_name=self.cluster_to_deploy,
                                             package=Constants.PROMETHEUS_PACKAGE,
                                             namespace=namespace,
                                             name=Constants.PROMETHEUS_APP,
                                             version=version,
                                             values=Paths.REMOTE_PROMETHEUS_DATA_VALUES)
        logger.debug(self.kubectl_client.get_all_pods())
        logger.info('Prometheus installation complete')

    def deploy_workload_cluster(self):
        logger.info("Setting up SE groups for workload cluster...")
        network_config = self.networkConfig()
        if network_config[1] != 200:
            logger.error(network_config[0].json['msg'])
            d = {
                "responseType": "ERROR",
                "msg": "Failed to Config workload cluster " + str(network_config[0].json['msg']),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        deploy_workload = self.deploy()
        if deploy_workload[1] != 200:
            logger.error(str(deploy_workload[0].json['msg']))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to deploy extention " + str(deploy_workload[0].json['msg']),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        logger.info("Checking for SaaS Integration..")
        saas_integration_output = self.deploy_saas_workload()
        if saas_integration_output[1] != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to enable SaaS Integartions " +
                       str(saas_integration_output[0].json['msg']),
                "ERROR_CODE": 500
                }
            return json.dumps(d), 500
        extension_check = str(self.jsonspec['tanzuExtensions']['enableEntensions']).lower
        if extension_check == "true":
            repo_address = Repo.PUBLIC_REPO
            if not repo_address.endswith("/"):
                repo_address = repo_address + "/"
            repo_address = repo_address.replace("https://", "").replace("http://", "")
            logger.info('Setting up Cert and Contour...')
            workload_cluster_name = self.jsonspec['tkgWorkloadComponents']['tkgWorkloadClusterName']
            cert_ext_status = installCertManagerAndContour(self.jsonspec, workload_cluster_name,
                                                           repo_address)
            if cert_ext_status[1] != 200:
                logger.error(cert_ext_status[0].json['msg'])
                d = {
                    "responseType": "ERROR",
                    "msg": cert_ext_status[0].json['msg'],
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500

            logger.info("Check for monitoring extensions deployment...")
            monitor_extension_check = str(self.jsonspec['tanzuExtensions']['monitoring']).lower
            if monitor_extension_check == "true":
                try:
                    logger.info("Starting grafana deployment...")
                    self._install_grafana(workload_cluster_name)
                except:
                    d = {
                        "responseType": "ERROR",
                        "msg": "Unable to setup grafana extension",
                        "ERROR_CODE": 500
                    }
                    logger.error("Error Encountered: {}".format(traceback.format_exc()))
                    return json.dumps(d), 500
                try:
                    logger.info("Starting prometheus deployment...")
                    self._install_prometheus(workload_cluster_name)
                except:
                    d = {
                        "responseType": "ERROR",
                        "msg": "Unable to setup prometheus extension",
                        "ERROR_CODE": 500
                    }
                    logger.error("Error Encountered: {}".format(traceback.format_exc()))
                    return json.dumps(d), 500

        logger.info("Not Enabling Extensions, since user has not opted for.")
        d = {
            "responseType": "SUCCESS",
            "msg": "Workload cluster configured Successfully",
            "ERROR_CODE": 200
        }

        logger.info("Workload cluster configured Successfully")
        return json.dumps(d), 200



